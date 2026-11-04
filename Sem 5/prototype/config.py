"""
Shared configuration for the SIM Swap Fraud Detection prototype.
Every module imports paths, feature order and policy constants from here so
that training, the risk engine, experiments and tests stay consistent.
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
RESULTS_DIR = BASE_DIR / "results"
FIGURES_DIR = RESULTS_DIR / "figures"
BLOCKCHAIN_DIR = BASE_DIR / "blockchain"
DASHBOARD_DIR = BASE_DIR / "dashboard"

DATASET_CSV = DATA_DIR / "sim_swap_dataset.csv"
MODEL_PATH = RESULTS_DIR / "xgb_sim_swap.json"
MODEL_META_PATH = RESULTS_DIR / "model_meta.json"
DB_PATH = Path(os.environ.get("SIMGUARD_DB", RESULTS_DIR / "simguard.db"))
CONTRACT_BUILD = BLOCKCHAIN_DIR / "build" / "SIMSwapAuditLog.json"
DEPLOYMENT_FILE = RESULTS_DIR / "chain_deployment.json"

RPC_URL = os.environ.get("SIMGUARD_RPC_URL", "http://127.0.0.1:8545")

# Secret keys. In production these live in an HSM / secrets manager;
# fixed values here keep the prototype reproducible.
OPERATOR_HMAC_KEY = os.environ.get("SIMGUARD_OPERATOR_KEY", "rmkec-capstone-operator-key").encode()
EDGE_DEVICE_KEYS = {
    "EDGE-STORE-CHN-01": b"edge-device-key-chn-01",
    "EDGE-STORE-CHN-02": b"edge-device-key-chn-02",
}
TELEMETRY_MAX_AGE_S = 120

# Feature order used by the model (must match training).
FEATURE_COLS = [
    "account_age_days",
    "sim_age_days",
    "swaps_last_180d",
    "imei_changed",
    "device_age_days",
    "old_sim_last_seen_min",
    "distance_from_home_km",
    "cell_changes_24h",
    "hour_of_request",
    "is_weekend",
    "channel_code",
    "kyc_biometric_verified",
    "auth_failures_7d",
    "profile_change_7d",
    "agent_swaps_24h",
    "roaming_flag",
]

CHANNELS = ["STORE", "CALL_CENTRE", "ONLINE", "RETAILER"]

FEATURE_LABELS = {
    "account_age_days": "Account age (days)",
    "sim_age_days": "Current SIM age (days)",
    "swaps_last_180d": "SIM swaps in last 180 days",
    "imei_changed": "Handset (IMEI) changed",
    "device_age_days": "New handset age on network (days)",
    "old_sim_last_seen_min": "Old SIM last seen (minutes)",
    "distance_from_home_km": "Distance from home cell (km)",
    "cell_changes_24h": "Cell changes in last 24 h",
    "hour_of_request": "Hour of request",
    "is_weekend": "Weekend request",
    "channel_code": "Request channel",
    "kyc_biometric_verified": "Biometric KYC verified",
    "auth_failures_7d": "Auth failures in last 7 days",
    "profile_change_7d": "Profile changed in last 7 days",
    "agent_swaps_24h": "Agent swaps in last 24 h",
    "roaming_flag": "Subscriber roaming",
}

DECISIONS = ["AUTO_APPROVE", "MANUAL_REVIEW", "AUTO_BLOCK"]
