"""
Model loading, scoring and SHAP explanations.

SHAP values are computed with XGBoost's built-in TreeSHAP
(`pred_contribs=True`), which is the exact algorithm of Lundberg et al. (2020)
and needs no extra dependency. Contributions are in log-odds space and satisfy
  base_value + sum(contributions) == model margin.
"""

import json
import sys
from functools import lru_cache
from pathlib import Path
from typing import Dict, List

import numpy as np
import xgboost as xgb

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import CHANNELS, FEATURE_COLS, MODEL_META_PATH, MODEL_PATH  # noqa: E402


@lru_cache(maxsize=1)
def load_model():
    booster = xgb.Booster()
    booster.load_model(str(MODEL_PATH))
    with open(MODEL_META_PATH, encoding="utf-8") as f:
        meta = json.load(f)
    return booster, meta


def score(features: Dict) -> Dict:
    """Return fraud probability plus the full SHAP vector for one request."""
    booster, meta = load_model()
    x = np.array([[float(features[c]) for c in FEATURE_COLS]], dtype=np.float32)
    dm = xgb.DMatrix(x, feature_names=FEATURE_COLS)
    contribs = booster.predict(dm, pred_contribs=True)[0]
    margin = float(contribs.sum())
    prob = float(1.0 / (1.0 + np.exp(-margin)))
    return {
        "probability": prob,
        "margin": margin,
        "base_value": float(contribs[-1]),
        "contributions": {c: float(v) for c, v in zip(FEATURE_COLS, contribs[:-1])},
        "model_version": meta["model_version"],
    }


def describe(feature: str, value: float) -> str:
    v = value
    templates = {
        "account_age_days": lambda: f"Account is {v:.0f} days old",
        "sim_age_days": lambda: f"Current SIM was issued {v:.0f} day(s) ago",
        "swaps_last_180d": lambda: f"{v:.0f} SIM swap(s) in the last 180 days",
        "imei_changed": lambda: "Number is moving to a different handset" if v else "Same handset as before",
        "device_age_days": lambda: ("New handset has never been seen on the network" if v == 0
                                    else f"New handset first seen {v:.0f} day(s) ago"),
        "old_sim_last_seen_min": lambda: f"Existing SIM was active {v:.0f} min ago",
        "distance_from_home_km": lambda: f"Request made {v:.0f} km from the home cell",
        "cell_changes_24h": lambda: f"{v:.0f} cell changes in the last 24 h",
        "hour_of_request": lambda: f"Requested at {int(v):02d}:00",
        "is_weekend": lambda: "Requested on a weekend" if v else "Requested on a weekday",
        "channel_code": lambda: f"Requested through the {CHANNELS[int(v)].replace('_', ' ').lower()} channel",
        "kyc_biometric_verified": lambda: "Biometric KYC completed" if v else "Biometric KYC not completed",
        "auth_failures_7d": lambda: f"{v:.0f} failed authentication attempt(s) in 7 days",
        "profile_change_7d": lambda: "Profile details changed in the last 7 days" if v else "No recent profile changes",
        "agent_swaps_24h": lambda: f"Handling agent processed {v:.0f} swaps in 24 h",
        "roaming_flag": lambda: "Subscriber is roaming" if v else "Subscriber not roaming",
    }
    return templates[feature]()


def top_reasons(features: Dict, contributions: Dict, k: int = 4) -> List[Dict]:
    ranked = sorted(contributions.items(), key=lambda kv: abs(kv[1]), reverse=True)[:k]
    return [{
        "feature": f,
        "value": float(features[f]),
        "shap": round(v, 4),
        "direction": "increases" if v > 0 else "decreases",
        "text": describe(f, float(features[f])),
    } for f, v in ranked]
