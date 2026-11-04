"""
SIMGuard Risk Engine API (FastAPI)

  POST /api/v1/evaluate                 evaluate a SIM replacement request
  GET  /api/v1/decisions[/{id}]         off-chain decision records
  POST /api/v1/decisions/{id}/resolve   analyst outcome for a MANUAL_REVIEW
  GET  /api/v1/ledger                   on-chain entries + contract info
  GET  /api/v1/audit/verify             recompute hashes, compare with the chain
  POST /api/v1/demo/tamper | restore    insider-attack demonstration on the off-chain DB
  POST /api/v1/demo/edge-attack/{kind}  telemetry attacks (tamper, replay, stale, unknown device)
  GET  /api/v1/scenarios[/{key}]        real held-out requests for the console presets
  GET  /api/v1/metrics                  model comparison and calibration
"""

import copy
import json
import sys
import time
import uuid
from pathlib import Path
from typing import Dict, List, Literal, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import DASHBOARD_DIR, MODEL_META_PATH, RESULTS_DIR  # noqa: E402
from edge.gateway_sim import build_envelope  # noqa: E402
from risk_engine.engine import (DuplicateRequest, InvalidRequest, RiskEngine,  # noqa: E402
                                TelemetryRejected)
from risk_engine.samples import build_request, load_test_frame, pick_scenarios  # noqa: E402

app = FastAPI(title="SIMGuard Risk Engine", version="2.0.0",
              description="Explainable, blockchain-anchored SIM swap fraud decisions.")
app.add_middleware(CORSMiddleware, allow_origin_regex=r"http://(127\.0\.0\.1|localhost)(:\d+)?",
                   allow_methods=["*"], allow_headers=["*"])

_engine: Optional[RiskEngine] = None
_scenarios: Dict[str, Dict] = {}
_tamper_backup: Dict[str, Dict] = {}

SCENARIO_INFO = {
    "legitimate": ("Genuine upgrade", "Long-standing customer replaces the SIM in a store after buying a new handset."),
    "suspicious": ("Suspicious request", "Borderline case: unusual agent activity on an otherwise normal-looking request."),
    "attack": ("Remote social-engineering attack", "Remote request without biometric KYC, far from home, handset changing."),
    "blacklisted": ("Blacklisted handset", "Swap onto a handset that is on the stolen-device register."),
}


def engine() -> RiskEngine:
    global _engine, _scenarios
    if _engine is None:
        _engine = RiskEngine()
        _scenarios = pick_scenarios(load_test_frame(), _engine)
    return _engine


# ───────────────────────────── models ─────────────────────────────

class BSSData(BaseModel):
    account_age_days: float = Field(ge=0)
    sim_age_days: float = Field(ge=0)
    swaps_last_180d: float = Field(ge=0)
    hour_of_request: int = Field(ge=0, le=23)
    is_weekend: int = Field(ge=0, le=1)
    kyc_biometric_verified: int = Field(ge=0, le=1)
    auth_failures_7d: float = Field(ge=0)
    profile_change_7d: int = Field(ge=0, le=1)
    agent_swaps_24h: float = Field(ge=0)


class TelemetryEnvelope(BaseModel):
    device_id: str
    nonce: str
    ts: float
    payload: Dict
    signature: str


class SwapRequest(BaseModel):
    request_id: Optional[str] = None
    msisdn: str = Field(pattern=r"^\+\d{10,15}$")
    channel: Literal["STORE", "CALL_CENTRE", "ONLINE", "RETAILER"]
    agent_id: str
    bss: BSSData
    telemetry: TelemetryEnvelope


class ResolveBody(BaseModel):
    final_decision: Literal["AUTO_APPROVE", "AUTO_BLOCK"]
    analyst_id: str = Field(min_length=2)
    note: str = Field(min_length=5)


class TamperBody(BaseModel):
    request_id: str
    mode: Literal["decision", "explanation", "delete"]


def public(row: Dict) -> Dict:
    """Decision row as returned to clients (subscriber_ref is a pseudonym, MSISDN is masked)."""
    return row


# ───────────────────────────── endpoints ─────────────────────────────

@app.get("/api/v1/health")
def health():
    e = engine()
    return {"status": "healthy", "model_version": e.meta["model_version"],
            "decisions_stored": e.store.count_decisions(), "chain": e.chain.chain_info(),
            "blacklist_size": e.store.blacklist_size(),
            "thresholds": {"review": e.t_review, "block": e.t_block}}


@app.post("/api/v1/evaluate")
def evaluate(req: SwapRequest):
    e = engine()
    try:
        return public(e.evaluate(req.model_dump()))
    except TelemetryRejected as exc:
        return JSONResponse(status_code=401, content={"error": "telemetry_rejected", "reason": str(exc)})
    except DuplicateRequest as exc:
        return JSONResponse(status_code=409, content={"error": "duplicate_request", "reason": str(exc)})
    except InvalidRequest as exc:
        return JSONResponse(status_code=422, content={"error": "invalid_request", "reason": str(exc)})


@app.get("/api/v1/decisions")
def list_decisions(limit: int = 50, decision: Optional[str] = None):
    e = engine()
    rows = e.store.list_decisions(min(limit, 500), decision)
    return {"total": e.store.count_decisions(), "decisions": rows}


@app.get("/api/v1/decisions/{request_id}")
def get_decision(request_id: str):
    row = engine().store.get_decision(request_id)
    if row is None:
        raise HTTPException(404, "unknown request")
    return row


@app.post("/api/v1/decisions/{request_id}/resolve")
def resolve(request_id: str, body: ResolveBody):
    try:
        return engine().resolve(request_id, body.final_decision, body.analyst_id, body.note)
    except InvalidRequest as exc:
        raise HTTPException(422, str(exc))


@app.get("/api/v1/ledger")
def ledger(limit: int = 12):
    e = engine()
    n = e.chain.entry_count()
    entries = []
    for eid in range(n - 1, max(-1, n - 1 - limit), -1):
        entry = e.chain.get_entry(eid)
        row = e.store.get_by_entry(eid)
        entry["request_id"] = row["request_id"] if row else None
        entry["tx_hash"] = row["tx_hash"] if row else None
        entry["gas_used"] = row["gas_used"] if row else None
        entry["block_number"] = row["block_number"] if row else None
        entry["resolution"] = e.chain.get_resolution(eid)
        entries.append(entry)
    return {"info": e.chain.chain_info(), "stats": e.chain.stats(), "entries": entries}


@app.get("/api/v1/audit/verify")
def audit_verify():
    return engine().audit()


@app.post("/api/v1/demo/tamper")
def demo_tamper(body: TamperBody):
    """Simulate an insider with write access to the operator's database."""
    e = engine()
    row = e.store.get_decision(body.request_id)
    if row is None:
        raise HTTPException(404, "unknown request")
    _tamper_backup.setdefault(body.request_id, copy.deepcopy(row))
    if body.mode == "decision":
        new = "AUTO_APPROVE" if row["decision"] != "AUTO_APPROVE" else "AUTO_BLOCK"
        e.store.update_field(body.request_id, "decision", new)
        change = f"decision changed {row['decision']} -> {new}"
    elif body.mode == "explanation":
        c = dict(row["contributions"])
        top = max(c, key=lambda k: abs(c[k]))
        c[top] = round(c[top] * 0.1, 6)
        e.store.update_field(body.request_id, "contributions", c)
        change = f"SHAP contribution of {top} reduced by 90%"
    else:
        e.store.delete_decision(body.request_id)
        change = "record deleted from the operator database"
    return {"request_id": body.request_id, "mode": body.mode, "change": change}


@app.post("/api/v1/demo/restore")
def demo_restore():
    e = engine()
    restored = []
    for rid, row in list(_tamper_backup.items()):
        if e.store.get_decision(rid) is None:
            e.store.insert_decision({k: v for k, v in row.items()})
        else:
            for f in ("decision", "contributions"):
                e.store.update_field(rid, f, row[f])
        restored.append(rid)
        del _tamper_backup[rid]
    return {"restored": restored}


@app.post("/api/v1/demo/edge-attack/{kind}")
def demo_edge_attack(kind: Literal["tamper_payload", "replay", "stale", "unknown_device"]):
    e = engine()
    engine()  # ensure scenarios
    row = _scenarios["legitimate"]
    req = build_request(row, request_id=row["request_id"] + "-" + uuid.uuid4().hex[:6])
    env = req["telemetry"]
    if kind == "tamper_payload":
        env["payload"]["old_sim_last_seen_min"] = 99999.0     # hide that the victim's SIM is live
        what = "Man-in-the-middle edits one telemetry field in transit"
    elif kind == "replay":
        first = build_request(row, request_id=row["request_id"] + "-" + uuid.uuid4().hex[:6])
        e.store.remember_nonce(first["telemetry"]["nonce"], first["telemetry"]["device_id"], time.time())
        req["telemetry"] = first["telemetry"]
        what = "Attacker re-sends a previously captured, valid packet"
    elif kind == "stale":
        req["telemetry"] = build_envelope(row, ts=time.time() - 3600)
        what = "Packet captured an hour ago is submitted now"
    else:
        req["telemetry"] = build_envelope(row, device_id="EDGE-STORE-CHN-01")
        req["telemetry"]["device_id"] = "EDGE-ROGUE-99"
        what = "Packet claims to come from an unregistered device"
    try:
        e.evaluate(req)
        return {"kind": kind, "what": what, "accepted": True, "reason": "NOT DETECTED"}
    except TelemetryRejected as exc:
        return {"kind": kind, "what": what, "accepted": False, "reason": str(exc)}


@app.get("/api/v1/edge/rejections")
def rejections():
    return {"rejections": list(reversed(engine().rejections))[:20]}


@app.get("/api/v1/scenarios")
def scenarios():
    engine()
    return [{"key": k, "label": SCENARIO_INFO[k][0], "description": SCENARIO_INFO[k][1]} for k in _scenarios]


@app.get("/api/v1/scenarios/{key}")
def scenario(key: str):
    engine()
    if key not in _scenarios:
        raise HTTPException(404, "unknown scenario")
    row = _scenarios[key]
    return build_request(row, request_id=row["request_id"] + "-" + uuid.uuid4().hex[:6])


@app.get("/api/v1/metrics")
def metrics():
    out = {"meta": json.loads(MODEL_META_PATH.read_text(encoding="utf-8"))}
    comp = RESULTS_DIR / "model_comparison.json"
    if comp.exists():
        out["comparison"] = json.loads(comp.read_text(encoding="utf-8"))
    exp = RESULTS_DIR / "experiments.json"
    if exp.exists():
        out["experiments"] = json.loads(exp.read_text(encoding="utf-8"))
    return out


# ───────────────────────────── static dashboard ─────────────────────────────

if (RESULTS_DIR / "figures").exists():
    app.mount("/figures", StaticFiles(directory=str(RESULTS_DIR / "figures")), name="figures")
app.mount("/static", StaticFiles(directory=str(DASHBOARD_DIR)), name="static")


@app.get("/")
def index():
    return FileResponse(str(DASHBOARD_DIR / "index.html"))


if __name__ == "__main__":
    import os
    import uvicorn
    port = int(os.environ.get("SIMGUARD_PORT", "8051"))
    print(f"SIMGuard console: http://127.0.0.1:{port}   API docs: http://127.0.0.1:{port}/docs", flush=True)
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")
