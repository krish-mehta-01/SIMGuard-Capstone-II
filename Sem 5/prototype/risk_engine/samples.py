"""Builds API requests from held-out dataset rows, with telemetry signed by the (emulated) edge gateway."""

import json
import sys
from pathlib import Path
from typing import Dict, List

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import DATASET_CSV, RESULTS_DIR  # noqa: E402
from edge.gateway_sim import build_envelope  # noqa: E402

BSS_FIELDS = ["account_age_days", "sim_age_days", "swaps_last_180d", "hour_of_request", "is_weekend",
              "kyc_biometric_verified", "auth_failures_7d", "profile_change_7d", "agent_swaps_24h"]


def load_test_frame() -> pd.DataFrame:
    df = pd.read_csv(DATASET_CSV, dtype={"msisdn": str, "new_imei": str})
    ids = set(json.loads((RESULTS_DIR / "splits.json").read_text())["test"])
    return df[df.request_id.isin(ids)].reset_index(drop=True)


def build_request(row, device_id: str = "EDGE-STORE-CHN-01", request_id=None) -> Dict:
    r = row if isinstance(row, dict) else row.to_dict()
    return {
        "request_id": request_id or r["request_id"],
        "msisdn": r["msisdn"],
        "channel": r["channel"],
        "agent_id": r["agent_id"],
        "bss": {k: float(r[k]) for k in BSS_FIELDS},
        "telemetry": build_envelope(r, device_id=device_id),
    }


def pick_scenarios(test: pd.DataFrame, engine) -> Dict[str, Dict]:
    """Choose one real held-out request for each dashboard scenario by scoring the test split."""
    from ml import explain
    from risk_engine.rules import decide, evaluate_rules

    picks: Dict[str, int] = {}
    cands = []
    for i, r in test.iterrows():
        feats = {k: float(r[k]) for k in explain.FEATURE_COLS}
        p = explain.score(feats)["probability"]
        flags = evaluate_rules(feats, bool(r.imei_blacklisted))
        risk, dec = decide(p, flags, engine.t_review, engine.t_block)
        cands.append((i, int(r.is_fraud), p, dec, bool(r.imei_blacklisted)))
        if len(cands) >= 1500:
            break
    c = pd.DataFrame(cands, columns=["i", "fraud", "p", "dec", "black"])
    legit = c[(c.fraud == 0) & (c.dec == "AUTO_APPROVE") & (c.p < 0.01)]
    review = c[(c.fraud == 1) & (c.dec == "MANUAL_REVIEW")]
    attack = c[(c.fraud == 1) & (c.dec == "AUTO_BLOCK") & (~c.black) & (c.p > 0.9)]
    black = c[(c.fraud == 1) & c.black]
    out = {}
    for name, frame in [("legitimate", legit), ("suspicious", review), ("attack", attack), ("blacklisted", black)]:
        if len(frame):
            out[name] = int(frame.iloc[0].i)
    return {k: test.iloc[v].to_dict() for k, v in out.items()}
