from risk_engine.rules import decide, evaluate_rules

BASE = dict(sim_age_days=400, agent_swaps_24h=4, old_sim_last_seen_min=500, distance_from_home_km=3,
            kyc_biometric_verified=1, channel_code=0, auth_failures_7d=0)


def names(flags):
    return {f["rule"] for f in flags}


def test_clean_request_has_no_flags():
    assert evaluate_rules(BASE, False) == []


def test_blacklist_is_critical_and_forces_block():
    flags = evaluate_rules(BASE, True)
    assert names(flags) == {"IMEI_BLACKLISTED"}
    risk, dec = decide(0.0, flags, 0.13, 0.9)
    assert dec == "AUTO_BLOCK"


def test_cooldown_is_high_and_forces_at_least_review():
    flags = evaluate_rules(BASE | {"sim_age_days": 3}, False)
    assert names(flags) == {"SWAP_COOLDOWN"}
    assert decide(0.0, flags, 0.13, 0.9)[1] == "MANUAL_REVIEW"


def test_agent_velocity_boundary():
    assert "AGENT_VELOCITY" not in names(evaluate_rules(BASE | {"agent_swaps_24h": 11}, False))
    assert "AGENT_VELOCITY" in names(evaluate_rules(BASE | {"agent_swaps_24h": 12}, False))


def test_active_sim_remote_request_needs_both_conditions():
    assert "ACTIVE_SIM_REMOTE_REQUEST" not in names(evaluate_rules(BASE | {"old_sim_last_seen_min": 5}, False))
    assert "ACTIVE_SIM_REMOTE_REQUEST" not in names(evaluate_rules(BASE | {"distance_from_home_km": 90}, False))
    both = evaluate_rules(BASE | {"old_sim_last_seen_min": 5, "distance_from_home_km": 90}, False)
    assert "ACTIVE_SIM_REMOTE_REQUEST" in names(both)


def test_weak_kyc_only_matters_on_remote_channels():
    assert "WEAK_KYC_REMOTE_CHANNEL" not in names(evaluate_rules(BASE | {"kyc_biometric_verified": 0}, False))
    assert "WEAK_KYC_REMOTE_CHANNEL" in names(
        evaluate_rules(BASE | {"kyc_biometric_verified": 0, "channel_code": 1}, False))


def test_three_tiers_from_probability_alone():
    assert decide(0.05, [], 0.13, 0.9)[1] == "AUTO_APPROVE"
    assert decide(0.13, [], 0.13, 0.9)[1] == "MANUAL_REVIEW"
    assert decide(0.50, [], 0.13, 0.9)[1] == "MANUAL_REVIEW"
    assert decide(0.90, [], 0.13, 0.9)[1] == "AUTO_BLOCK"


def test_medium_flags_boost_the_score_but_cannot_exceed_one():
    flags = evaluate_rules(BASE | {"kyc_biometric_verified": 0, "channel_code": 1, "auth_failures_7d": 6}, False)
    assert len(flags) == 2
    risk, _ = decide(0.85, flags, 0.13, 0.9)
    assert risk == 1.0
    assert decide(0.1, flags, 0.13, 0.9)[0] == 0.3
