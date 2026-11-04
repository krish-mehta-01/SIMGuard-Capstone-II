import json
import time

from edge.telemetry import luhn_valid, sign_envelope, verify_envelope

PAYLOAD = {"imei": "352092114951370", "imei_changed": 1, "device_age_days": 0.0, "old_sim_last_seen_min": 12.0,
           "distance_from_home_km": 40.0, "cell_changes_24h": 3.0, "roaming_flag": 0, "rssi_dbm": -71, "cell_id": 51890}
DEV = "EDGE-STORE-CHN-01"


def test_genuine_packet_is_accepted():
    ok, why = verify_envelope(sign_envelope(DEV, PAYLOAD), set())
    assert ok, why


def test_payload_tampering_is_rejected():
    env = sign_envelope(DEV, PAYLOAD)
    env["payload"]["old_sim_last_seen_min"] = 9999.0
    assert verify_envelope(env, set()) == (False, "signature mismatch (payload altered or wrong key)")


def test_replay_is_rejected():
    env = sign_envelope(DEV, PAYLOAD)
    assert verify_envelope(env, {env["nonce"]})[1] == "replayed nonce"


def test_stale_packet_is_rejected():
    env = sign_envelope(DEV, PAYLOAD, ts=time.time() - 3600)
    assert "stale" in verify_envelope(env, set())[1]


def test_unknown_device_is_rejected():
    env = sign_envelope(DEV, PAYLOAD)
    env["device_id"] = "EDGE-ROGUE-1"
    assert verify_envelope(env, set())[1] == "unknown edge device"


def test_wrong_key_is_rejected():
    env = sign_envelope(DEV, PAYLOAD, key=b"not-the-device-key")
    assert "signature" in verify_envelope(env, set())[1]


def test_bad_imei_checksum_is_rejected_even_if_correctly_signed():
    env = sign_envelope(DEV, PAYLOAD | {"imei": "352092114951371"})
    assert "IMEI" in verify_envelope(env, set())[1]


def test_malformed_envelope_is_rejected():
    assert verify_envelope({"device_id": DEV}, set())[0] is False


def test_signature_survives_a_javascript_style_json_round_trip():
    """Browsers turn 12.0 into 12; the canonical encoding must not care."""
    env = sign_envelope(DEV, PAYLOAD)
    text = json.dumps(env)
    js_like = json.loads(text.replace(".0,", ",").replace(".0}", "}"))
    assert js_like["payload"]["old_sim_last_seen_min"] == 12 and verify_envelope(js_like, set())[0]


def test_luhn():
    assert luhn_valid("352092114951370")
    assert not luhn_valid("352092114951371")
    assert not luhn_valid("12345")
