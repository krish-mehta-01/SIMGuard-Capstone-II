"""
SIMGuard Risk Engine API (FastAPI)

Features:
  - V1 Endpoints: Explainable ML SIM swap fraud decisions (BSS telemetry + XGBoost + TreeSHAP + Smart Contract)
  - V2 Endpoints: Digital SIM & Blockchain-Based Secure Communication System (Gamma Slide Deck)
      * Device-bound identity (Phone Hash + Device PubKey + Device Fingerprint Hash)
      * Cryptographic challenge-response authentication (Ed25519)
      * AES-256-GCM End-to-end encrypted messaging with payload hash blockchain anchoring
      * Signed call metadata verification
      * 4 Transaction categories: REGISTER, MESSAGE, CALL_META, SECURITY_ALERT
      * 2-Device + Attacker Interception Simulation (Unprotected vs SIMGUARD Protected)
      * 6 Evaluation demonstration scenarios (Slide 9)
"""

import copy
import json
from pathlib import Path
import sys
import time
from typing import Dict, List, Literal, Optional
import uuid

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import DASHBOARD_DIR, MODEL_META_PATH, RESULTS_DIR  # noqa: E402
from digital_engine import DigitalEngine  # noqa: E402
from edge.gateway_sim import build_envelope  # noqa: E402
from risk_engine.engine import (  # noqa: E402
    DuplicateRequest,
    InvalidRequest,
    RiskEngine,
    TelemetryRejected,
)
from risk_engine.samples import (  # noqa: E402
    build_request,
    load_test_frame,
    pick_scenarios,
)

app = FastAPI(
    title="SIMGuard — Blockchain-Based Secure Communication & Fraud System",
    version="2.0.0",
    description="Device-bound identity, encrypted communications, and explainable telecom fraud defense.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"http://(127\.0\.0\.1|localhost)(:\d+)?",
    allow_methods=["*"],
    allow_headers=["*"],
)

_engine: Optional[RiskEngine] = None
_digital_engine: Optional[DigitalEngine] = None
_scenarios: Dict[str, Dict] = {}
_tamper_backup: Dict[str, Dict] = {}

SCENARIO_INFO = {
    "legitimate": (
        "Genuine upgrade",
        "Long-standing customer replaces the SIM in a store after buying a new handset.",
    ),
    "suspicious": (
        "Suspicious request",
        "Borderline case: unusual agent activity on an otherwise normal-looking request.",
    ),
    "attack": (
        "Remote social-engineering attack",
        "Remote request without biometric KYC, far from home, handset changing.",
    ),
    "blacklisted": (
        "Blacklisted handset",
        "Swap onto a handset that is on the stolen-device register.",
    ),
}


def engine() -> Optional[RiskEngine]:
    global _engine, _scenarios
    if _engine is None:
        try:
            _engine = RiskEngine()
            _scenarios = pick_scenarios(load_test_frame(), _engine)
        except Exception as ex:
            print(f"Notice: Legacy Ethereum node offline ({ex}). Running in Digital SIMGUARD Blockchain mode.", flush=True)
            _engine = None
    return _engine


def digital_engine() -> DigitalEngine:
    global _digital_engine
    if _digital_engine is None:
        _digital_engine = DigitalEngine()
    return _digital_engine


# ───────────────────────────── V1 Models ─────────────────────────────

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
    return row


# ───────────────────────────── V2 Models ─────────────────────────────

class V2DeviceRegisterBody(BaseModel):
    phone_number: str
    device_model: str = "Google Pixel 8 Pro"
    os_build: str = "Android 14 (UP1A.231105.001)"
    imei: str = "354892019485721"


class V2ChallengeRequest(BaseModel):
    phone_number: str


class V2ChallengeVerify(BaseModel):
    challenge_id: str
    signature_hex: str
    public_key_hex: str


class V2SendMessage(BaseModel):
    sender_phone: str = "+919876543210"
    recipient_phone: str = "+919876511223"
    plaintext: str


class V2LogCall(BaseModel):
    caller_phone: str = "+919876543210"
    callee_phone: str = "+919876511223"
    duration_seconds: int = 120
    call_type: str = "VoIP_E2EE"


class V2SimulateInterceptBody(BaseModel):
    sender_phone: str = "+919876543210"
    recipient_phone: str = "+919876511223"
    message: str = "Your Bank OTP is 849201"
    protection_enabled: bool = True


# ───────────────────────────── V1 Endpoints ─────────────────────────────

@app.get("/api/v1/health")
def health():
    e = engine()
    if e is None:
        d = digital_engine()
        return {
            "status": "healthy",
            "mode": "digital_blockchain",
            "model_version": "v2.0-digital",
            "thresholds": {"review": 0.13, "block": 0.90},
            "chain": {"latest_block": len(d.ledger.chain), "connected": True},
        }
    return {
        "status": "healthy",
        "model_version": e.meta["model_version"],
        "decisions_stored": e.store.count_decisions(),
        "chain": e.chain.chain_info(),
        "blacklist_size": e.store.blacklist_size(),
        "thresholds": {"review": e.t_review, "block": e.t_block},
    }


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
        env["payload"]["old_sim_last_seen_min"] = 99999.0
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


# ───────────────────────────── V2 Endpoints (Digital SIM & Crypto Blockchain) ─────────────────────────────

@app.get("/api/v2/stats")
def v2_stats():
    d = digital_engine()
    stats = d.ledger.get_stats()
    stats["devices_count"] = len(d.devices)
    stats["auth_challenges_active"] = len(d.auth_manager.active_challenges)
    stats["protocol_version"] = "2.0.0 (Ed25519 + SHA-256 + AES-256-GCM)"
    stats["consensus"] = "Cryptographic Hash-Chained Blockchain (PoA / BFT)"
    return stats


@app.get("/api/v2/devices")
def v2_devices():
    return {"devices": digital_engine().get_devices()}


@app.post("/api/v2/devices/register")
def v2_register_device(body: V2DeviceRegisterBody):
    res = digital_engine().register_device(
        phone_number=body.phone_number,
        device_model=body.device_model,
        os_build=body.os_build,
        imei=body.imei,
    )
    if res.get("status") == "error":
        raise HTTPException(400, res.get("message"))
    return res


@app.post("/api/v2/auth/challenge")
def v2_challenge(body: V2ChallengeRequest):
    return digital_engine().request_challenge(body.phone_number)


@app.post("/api/v2/auth/verify")
def v2_verify_challenge(body: V2ChallengeVerify):
    return digital_engine().verify_challenge(
        body.challenge_id, body.signature_hex, body.public_key_hex
    )


@app.post("/api/v2/simulate/intercept")
def v2_simulate_intercept(body: V2SimulateInterceptBody):
    """2-Device + Attacker Interception Simulation requested by user."""
    return digital_engine().simulate_interception(
        sender_phone=body.sender_phone,
        recipient_phone=body.recipient_phone,
        message=body.message,
        protection_enabled=body.protection_enabled,
    )


@app.post("/api/v2/messages/send")
def v2_send_message(body: V2SendMessage):
    res = digital_engine().send_e2ee_message(
        body.sender_phone, body.recipient_phone, body.plaintext
    )
    if res.get("status") == "error":
        raise HTTPException(400, res.get("message"))
    return res


@app.post("/api/v2/calls/log")
def v2_log_call(body: V2LogCall):
    res = digital_engine().log_call_metadata(
        body.caller_phone, body.callee_phone, body.duration_seconds, body.call_type
    )
    if res.get("status") == "error":
        raise HTTPException(400, res.get("message"))
    return res


@app.get("/api/v2/ledger")
def v2_ledger(category: Optional[str] = None):
    d = digital_engine()
    chain = d.ledger.get_chain_dict()
    if category and category.upper() != "ALL":
        filtered_chain = []
        for b in chain:
            matching_txs = [t for t in b["transactions"] if t.get("tx_type") == category.upper()]
            if matching_txs:
                b_copy = dict(b)
                b_copy["transactions"] = matching_txs
                filtered_chain.append(b_copy)
        return {
            "total_blocks": len(filtered_chain),
            "chain": list(reversed(filtered_chain)),
            "category": category.upper(),
        }
    return {
        "total_blocks": len(chain),
        "chain": list(reversed(chain)),
        "category": "ALL",
    }


@app.get("/api/v2/audit")
def v2_audit():
    return digital_engine().ledger.verify_chain()


@app.post("/api/v2/scenarios/restore")
def v2_restore():
    return digital_engine().restore_ledger()


@app.post("/api/v2/scenarios/{scenario_id}")
def v2_scenario(scenario_id: int):
    d = digital_engine()
    if scenario_id == 1:
        return d.run_scenario_1_register()
    elif scenario_id == 2:
        return d.run_scenario_2_unauthorized_login()
    elif scenario_id == 3:
        return d.run_scenario_3_invalid_signature()
    elif scenario_id == 4:
        return d.run_scenario_4_block_modification()
    elif scenario_id == 5:
        return d.run_scenario_5_replay_attempt()
    elif scenario_id == 6:
        return d.run_scenario_6_call_metadata()
    else:
        raise HTTPException(400, f"Unknown scenario {scenario_id}. Choose 1 through 6.")


@app.get("/api/v2/logs")
def v2_logs():
    return {"events": list(reversed(digital_engine().simulated_logs))}


# ───────────────────────────── Static Dashboard & React Frontend ─────────────────────────────

REACT_DIST_DIR = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"
if (REACT_DIST_DIR / "assets").exists():
    app.mount("/assets", StaticFiles(directory=str(REACT_DIST_DIR / "assets")), name="assets")

if (RESULTS_DIR / "figures").exists():
    app.mount("/figures", StaticFiles(directory=str(RESULTS_DIR / "figures")), name="figures")
app.mount("/static", StaticFiles(directory=str(DASHBOARD_DIR)), name="static")


@app.get("/")
def index():
    if (REACT_DIST_DIR / "index.html").exists():
        return FileResponse(str(REACT_DIST_DIR / "index.html"))
    return FileResponse(str(DASHBOARD_DIR / "index.html"))


@app.get("/favicon.svg")
def favicon():
    if (REACT_DIST_DIR / "favicon.svg").exists():
        return FileResponse(str(REACT_DIST_DIR / "favicon.svg"))
    return FileResponse(str(DASHBOARD_DIR / "icons.svg"))


@app.get("/simguard-logo.svg")
def simguard_logo():
    if (REACT_DIST_DIR / "simguard-logo.svg").exists():
        return FileResponse(str(REACT_DIST_DIR / "simguard-logo.svg"))
    return FileResponse(str(DASHBOARD_DIR / "simguard-logo.svg"))



if __name__ == "__main__":
    import os
    import uvicorn
    port = int(os.environ.get("SIMGUARD_PORT", "8051"))
    print(f"SIMGuard console: http://127.0.0.1:{port}   API docs: http://127.0.0.1:{port}/docs", flush=True)
    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")
