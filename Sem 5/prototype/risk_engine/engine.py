"""
Cybersecurity Risk Engine: orchestrates one SIM replacement decision end to end.

  signed edge telemetry --verify--> feature vector --XGBoost + TreeSHAP--> fraud probability
                          + deterministic rules + IMEI blacklist (SQLite)
                          --> three-tier decision (policy thresholds from calibration)
                          --> canonical hashes --> smart-contract entry --> off-chain record
"""

import hashlib
import sys
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from blockchain.chain import AuditChain, compute_hashes, pseudonymise, sha256_hex  # noqa: E402
from config import CHANNELS, DATASET_CSV, FEATURE_COLS  # noqa: E402
from edge.telemetry import TELEMETRY_FIELDS, verify_envelope  # noqa: E402
from ml import explain  # noqa: E402
from risk_engine.rules import decide, evaluate_rules  # noqa: E402
from risk_engine.store import Store  # noqa: E402


class TelemetryRejected(Exception):
    pass


class DuplicateRequest(Exception):
    pass


class InvalidRequest(Exception):
    pass


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def mask_msisdn(msisdn: str) -> str:
    return msisdn[:3] + "X" * max(0, len(msisdn) - 7) + msisdn[-4:]


def build_summary(decision: str, risk: float, reasons: List[Dict], flags: List[Dict]) -> str:
    drivers = "; ".join(f"{r['text']} ({r['shap']:+.2f})" for r in reasons)
    text = f"{decision.replace('_', ' ').title()} at risk score {risk:.2f}. Main model drivers: {drivers}."
    if flags:
        text += " Policy rules triggered: " + "; ".join(f"{f['rule']} ({f['severity']})" for f in flags) + "."
    return text


class RiskEngine:
    def __init__(self, store: Optional[Store] = None, chain: Optional[AuditChain] = None):
        self.store = store or Store()
        self.chain = chain or AuditChain()
        _, meta = explain.load_model()
        self.meta = meta
        self.t_review = meta["policy"]["t_review"]
        self.t_block = meta["policy"]["t_block"]
        self._chain_lock = threading.Lock()
        # A new, empty operator database must not inherit another database's audit trail:
        # anchor it to a fresh contract instance (the old one remains on the chain, immutable).
        if self.store.count_decisions() == 0 and self.chain.entry_count() > 0:
            self.chain.contract = self.chain.deploy()
        self.rejections: List[Dict] = []
        self._seed_blacklist()

    def _seed_blacklist(self):
        if self.store.blacklist_size() == 0 and DATASET_CSV.exists():
            import pandas as pd
            df = pd.read_csv(DATASET_CSV, usecols=["new_imei", "imei_blacklisted"], dtype={"new_imei": str})
            hits = df[df.imei_blacklisted == 1].new_imei.astype(str).unique()
            self.store.seed_blacklist({i: "Reported stolen / blocked (CEIR register)" for i in hits})

    # ------------------------------------------------------------------
    def _features(self, req: Dict, payload: Dict) -> Dict:
        bss = req["bss"]
        if req["channel"] not in CHANNELS:
            raise InvalidRequest(f"unknown channel {req['channel']}")
        f = {k: float(bss[k]) for k in ("account_age_days", "sim_age_days", "swaps_last_180d",
                                         "hour_of_request", "is_weekend", "kyc_biometric_verified",
                                         "auth_failures_7d", "profile_change_7d", "agent_swaps_24h")}
        f["channel_code"] = float(CHANNELS.index(req["channel"]))
        for k in TELEMETRY_FIELDS:
            if k != "imei":
                f[k] = float(payload[k])
        return {k: f[k] for k in FEATURE_COLS}

    def evaluate(self, req: Dict) -> Dict:
        t_all = time.perf_counter()
        lat: Dict[str, float] = {}

        # 1. Telemetry integrity -------------------------------------------------
        t = time.perf_counter()
        env = req.get("telemetry")
        if not env:
            raise TelemetryRejected("missing signed edge telemetry")
        seen = {env.get("nonce")} if self.store.nonce_seen(str(env.get("nonce"))) else set()
        ok, reason = verify_envelope(env, seen)
        if not ok:
            self.rejections.append({"time": utc_now(), "device": env.get("device_id"), "reason": reason})
            self.rejections = self.rejections[-100:]
            raise TelemetryRejected(reason)
        payload = env["payload"]
        lat["telemetry_ms"] = (time.perf_counter() - t) * 1000

        request_id = req.get("request_id") or "REQ-" + uuid.uuid4().hex[:10].upper()
        if self.store.get_decision(request_id):
            raise DuplicateRequest(request_id)

        # 2. Features, ML score and SHAP ------------------------------------------
        features = self._features(req, payload)
        t = time.perf_counter()
        sc = explain.score(features)
        lat["ml_shap_ms"] = (time.perf_counter() - t) * 1000

        # 3. Deterministic rules + blacklist --------------------------------------
        t = time.perf_counter()
        blacklisted = self.store.is_blacklisted(str(payload["imei"]))
        flags = evaluate_rules(features, blacklisted)
        risk, decision = decide(sc["probability"], flags, self.t_review, self.t_block)
        reasons = explain.top_reasons(features, sc["contributions"], k=8)
        lat["rules_ms"] = (time.perf_counter() - t) * 1000

        # 4. Canonical record and hashes ------------------------------------------
        t = time.perf_counter()
        ts = utc_now()
        record = {
            "request_id": request_id,
            "subscriber_ref": pseudonymise(req["msisdn"]),
            "decision": decision,
            "risk_score": risk,
            "ml_probability": sc["probability"],
            "rule_flags": [f["rule"] for f in flags],
            "model_version": sc["model_version"],
            "timestamp": ts,
            "base_value": sc["base_value"],
            "contributions": sc["contributions"],
            "features": features,
        }
        hashes = compute_hashes(record)
        lat["hashing_ms"] = (time.perf_counter() - t) * 1000

        # 5. Anchor on the blockchain ---------------------------------------------
        with self._chain_lock:
            anchor = self.chain.log_decision(record["subscriber_ref"], decision, risk,
                                             hashes["decision_hash"], hashes["shap_hash"])
        lat["chain_ms"] = anchor["chain_ms"]

        # 6. Persist the off-chain record -----------------------------------------
        t = time.perf_counter()
        self.store.remember_nonce(env["nonce"], env["device_id"], float(env["ts"]))
        row = {
            "request_id": request_id,
            "entry_id": anchor["entry_id"],
            "subscriber_ref": record["subscriber_ref"],
            "msisdn_masked": mask_msisdn(req["msisdn"]),
            "channel": req["channel"],
            "agent_ref": hashlib.sha256(str(req.get("agent_id", "")).encode()).hexdigest()[:12],
            "decision": decision,
            "risk_score": risk,
            "ml_probability": sc["probability"],
            "rule_flags": record["rule_flags"],
            "rule_detail": flags,
            "model_version": sc["model_version"],
            "timestamp": ts,
            "base_value": sc["base_value"],
            "contributions": sc["contributions"],
            "features": features,
            "reasons": reasons,
            "summary": build_summary(decision, risk, reasons[:4], flags),
            "edge_device": env["device_id"],
            "decision_hash": hashes["decision_hash"],
            "shap_hash": hashes["shap_hash"],
            "tx_hash": anchor["tx_hash"],
            "block_number": anchor["block_number"],
            "gas_used": anchor["gas_used"],
            "latency_ms": {},
        }
        lat["db_ms"] = (time.perf_counter() - t) * 1000
        lat["total_ms"] = (time.perf_counter() - t_all) * 1000
        row["latency_ms"] = {k: round(v, 2) for k, v in lat.items()}
        self.store.insert_decision(row)
        return row

    # ------------------------------------------------------------------
    def resolve(self, request_id: str, final_decision: str, analyst_id: str, note: str) -> Dict:
        row = self.store.get_decision(request_id)
        if row is None:
            raise InvalidRequest("unknown request")
        if row["decision"] != "MANUAL_REVIEW":
            raise InvalidRequest("only MANUAL_REVIEW decisions can be resolved")
        if row.get("resolution"):
            raise InvalidRequest("already resolved")
        if final_decision not in ("AUTO_APPROVE", "AUTO_BLOCK"):
            raise InvalidRequest("final decision must be AUTO_APPROVE or AUTO_BLOCK")
        analyst_ref = pseudonymise("analyst:" + analyst_id)
        note_hash = sha256_hex(note.encode())
        with self._chain_lock:
            tx = self.chain.resolve_review(row["entry_id"], final_decision, analyst_ref, note_hash)
        resolution = {"final_decision": final_decision, "analyst_ref": analyst_ref[:12],
                      "note": note, "note_hash": note_hash, "tx_hash": tx["tx_hash"],
                      "gas_used": tx["gas_used"], "timestamp": utc_now()}
        self.store.update_field(request_id, "resolution", resolution)
        return resolution

    # ------------------------------------------------------------------
    @staticmethod
    def hashable(row: Dict) -> Dict:
        keys = ("request_id", "subscriber_ref", "decision", "risk_score", "ml_probability", "rule_flags",
                "model_version", "timestamp", "base_value", "contributions", "features")
        return {k: row[k] for k in keys}

    def audit(self) -> Dict:
        """Verify every off-chain record against the blockchain."""
        t0 = time.perf_counter()
        n_chain = self.chain.entry_count()
        rows = self.store.all_decisions()
        by_entry = {r["entry_id"]: r for r in rows if r["entry_id"] is not None}
        findings, checked, ok_count = [], 0, 0
        for eid in range(n_chain):
            row = by_entry.get(eid)
            if row is None:
                findings.append({"entry_id": eid, "request_id": None, "reason":
                                 "on-chain entry has no off-chain record (record deleted or never stored)"})
                continue
            checked += 1
            res = self.chain.verify_record(self.hashable(row), eid)
            if res["ok"]:
                ok_count += 1
            else:
                findings.append({"entry_id": eid, "request_id": row["request_id"], "reason": res["reason"]})
        for r in rows:
            if r["entry_id"] is None or r["entry_id"] >= n_chain:
                findings.append({"entry_id": r["entry_id"], "request_id": r["request_id"],
                                 "reason": "off-chain record is not anchored on the blockchain"})
        return {"on_chain_entries": n_chain, "off_chain_records": len(rows), "verified": ok_count,
                "tampered": len(findings), "integrity_ok": not findings, "findings": findings,
                "audit_seconds": round(time.perf_counter() - t0, 3)}
