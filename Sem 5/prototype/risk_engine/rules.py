"""
Deterministic security rules and the three-tier decision policy.

The ML model estimates *how unusual* a request is; these rules encode
non-negotiable operator policy that must hold regardless of what the model
says (a blacklisted handset is never approved, a number cannot be swapped
twice inside the cooldown window without a human looking at it, ...).

Severity semantics:
  CRITICAL -> forces AUTO_BLOCK
  HIGH     -> forces at least MANUAL_REVIEW
  MEDIUM   -> adds MEDIUM_BOOST to the risk score
"""

from typing import Dict, List, Tuple

MEDIUM_BOOST = 0.10
SWAP_COOLDOWN_DAYS = 7
AGENT_VELOCITY_LIMIT = 12
ACTIVE_SIM_MINUTES = 15
REMOTE_DISTANCE_KM = 50
AUTH_FAILURE_LIMIT = 5
REMOTE_CHANNELS = {1, 2}  # CALL_CENTRE, ONLINE


def evaluate_rules(features: Dict, imei_blacklisted: bool) -> List[Dict]:
    flags = []
    if imei_blacklisted:
        flags.append({"rule": "IMEI_BLACKLISTED", "severity": "CRITICAL",
                      "detail": "Target handset IMEI is on the stolen/blocked device register"})
    if features["sim_age_days"] < SWAP_COOLDOWN_DAYS:
        flags.append({"rule": "SWAP_COOLDOWN", "severity": "HIGH",
                      "detail": f"Current SIM issued {int(features['sim_age_days'])} day(s) ago "
                                f"(< {SWAP_COOLDOWN_DAYS}-day cooldown)"})
    if features["agent_swaps_24h"] >= AGENT_VELOCITY_LIMIT:
        flags.append({"rule": "AGENT_VELOCITY", "severity": "HIGH",
                      "detail": f"Agent processed {int(features['agent_swaps_24h'])} swaps in 24 h "
                                f"(limit {AGENT_VELOCITY_LIMIT})"})
    if (features["old_sim_last_seen_min"] < ACTIVE_SIM_MINUTES
            and features["distance_from_home_km"] > REMOTE_DISTANCE_KM):
        flags.append({"rule": "ACTIVE_SIM_REMOTE_REQUEST", "severity": "HIGH",
                      "detail": "Existing SIM is active on the network while the swap is requested "
                                f"{features['distance_from_home_km']:.0f} km away"})
    if features["kyc_biometric_verified"] == 0 and int(features["channel_code"]) in REMOTE_CHANNELS:
        flags.append({"rule": "WEAK_KYC_REMOTE_CHANNEL", "severity": "MEDIUM",
                      "detail": "Remote channel without biometric KYC"})
    if features["auth_failures_7d"] >= AUTH_FAILURE_LIMIT:
        flags.append({"rule": "AUTH_FAILURE_SPIKE", "severity": "MEDIUM",
                      "detail": f"{int(features['auth_failures_7d'])} failed authentications in 7 days"})
    return flags


def decide(ml_probability: float, flags: List[Dict], t_review: float, t_block: float) -> Tuple[float, str]:
    """Combine the ML probability with rule flags into (risk_score, decision)."""
    severities = {f["severity"] for f in flags}
    n_medium = sum(1 for f in flags if f["severity"] == "MEDIUM")
    risk = min(1.0, ml_probability + MEDIUM_BOOST * n_medium)

    if "CRITICAL" in severities or risk >= t_block:
        decision = "AUTO_BLOCK"
    elif "HIGH" in severities or risk >= t_review:
        decision = "MANUAL_REVIEW"
    else:
        decision = "AUTO_APPROVE"
    return round(risk, 4), decision
