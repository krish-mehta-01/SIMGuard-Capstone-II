import copy

import numpy as np
import xgboost as xgb

from blockchain.chain import compute_hashes, pseudonymise
from config import FEATURE_COLS
from ml import explain

FEATS = {"account_age_days": 900, "sim_age_days": 400, "swaps_last_180d": 0, "imei_changed": 1, "device_age_days": 0,
         "old_sim_last_seen_min": 12, "distance_from_home_km": 60, "cell_changes_24h": 4, "hour_of_request": 14,
         "is_weekend": 0, "channel_code": 1, "kyc_biometric_verified": 0, "auth_failures_7d": 2,
         "profile_change_7d": 1, "agent_swaps_24h": 5, "roaming_flag": 0}


def record():
    sc = explain.score(FEATS)
    return {"request_id": "REQ-1", "subscriber_ref": pseudonymise("+919876543210"), "decision": "MANUAL_REVIEW",
            "risk_score": 0.4321, "ml_probability": sc["probability"], "rule_flags": ["A", "B"],
            "model_version": sc["model_version"], "timestamp": "2026-10-07T10:00:00.000Z",
            "base_value": sc["base_value"], "contributions": sc["contributions"],
            "features": {k: float(v) for k, v in FEATS.items()}}


def test_hash_is_deterministic_and_order_independent():
    r = record()
    shuffled = dict(reversed(list(r.items())))
    shuffled["rule_flags"] = ["B", "A"]
    assert compute_hashes(r) == compute_hashes(shuffled)


def test_changing_any_covered_field_changes_the_matching_hash():
    r = record()
    h0 = compute_hashes(r)
    for field, value in [("decision", "AUTO_APPROVE"), ("risk_score", 0.1), ("request_id", "REQ-2"),
                         ("timestamp", "2026-10-07T10:00:01.000Z"), ("rule_flags", [])]:
        x = copy.deepcopy(r)
        x[field] = value
        assert compute_hashes(x)["decision_hash"] != h0["decision_hash"], field
    x = copy.deepcopy(r)
    x["contributions"]["distance_from_home_km"] += 0.01
    assert compute_hashes(x)["shap_hash"] != h0["shap_hash"]
    x = copy.deepcopy(r)
    x["features"]["auth_failures_7d"] = 9.0
    assert compute_hashes(x)["shap_hash"] != h0["shap_hash"]


def test_pseudonym_is_stable_and_does_not_leak_the_number():
    a = pseudonymise("+919876543210")
    assert a == pseudonymise("+919876543210") and a != pseudonymise("+919876543211")
    assert "9876543210" not in a and len(a) == 64


def test_shap_values_are_additive_and_match_the_model_margin():
    sc = explain.score(FEATS)
    booster, _ = explain.load_model()
    x = np.array([[FEATS[c] for c in FEATURE_COLS]], dtype=np.float32)
    margin = float(booster.predict(xgb.DMatrix(x, feature_names=FEATURE_COLS), output_margin=True)[0])
    assert abs(sc["base_value"] + sum(sc["contributions"].values()) - margin) < 1e-4
    assert 0.0 < sc["probability"] < 1.0


def test_top_reasons_are_sorted_by_magnitude_and_readable():
    sc = explain.score(FEATS)
    reasons = explain.top_reasons(FEATS, sc["contributions"], k=5)
    mags = [abs(r["shap"]) for r in reasons]
    assert mags == sorted(mags, reverse=True)
    assert all(isinstance(r["text"], str) and len(r["text"]) > 8 for r in reasons)
