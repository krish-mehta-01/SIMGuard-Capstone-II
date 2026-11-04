"""
Edge telemetry integrity (ECE module).

A hardware edge gateway (SIM800L GSM modem + microcontroller) reads handset and
radio parameters at the point of sale / network edge and forwards them to the
cloud risk engine. Everything the model relies on from the radio side must reach
the engine unaltered, so every packet is:

  * bound to a registered device (per-device secret key)
  * authenticated with HMAC-SHA256 over a canonical encoding of the packet
  * fresh        (timestamp within TELEMETRY_MAX_AGE_S of the engine clock)
  * non-replayable (single-use nonce, remembered by the engine)
  * plausibility-checked (IMEI Luhn checksum, RSSI range, non-negative counters)
"""

import copy
import hashlib
import hmac
import json
import sys
import time
import uuid
from pathlib import Path
from typing import Dict, Optional, Set, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import EDGE_DEVICE_KEYS, TELEMETRY_MAX_AGE_S  # noqa: E402

# Radio-side values that override anything the caller states about the handset.
TELEMETRY_FIELDS = ["imei", "imei_changed", "device_age_days", "old_sim_last_seen_min",
                    "distance_from_home_km", "cell_changes_24h", "roaming_flag"]


def _normalise(obj):
    """Make the encoding language-neutral: a JSON round-trip through JavaScript turns 12.0 into 12,
    so integral floats are canonicalised to integers on both the signing and verifying side."""
    if isinstance(obj, dict):
        return {k: _normalise(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_normalise(v) for v in obj]
    if isinstance(obj, float) and obj.is_integer():
        return int(obj)
    return obj


def _canonical(obj) -> bytes:
    return json.dumps(_normalise(obj), sort_keys=True, separators=(",", ":")).encode()


def luhn_valid(number: str) -> bool:
    if not number.isdigit() or len(number) != 15:
        return False
    total = 0
    for i, ch in enumerate(reversed(number)):
        d = int(ch)
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0


def sign_envelope(device_id: str, payload: Dict, ts: Optional[float] = None,
                  nonce: Optional[str] = None, key: Optional[bytes] = None) -> Dict:
    ts = time.time() if ts is None else ts
    nonce = nonce or uuid.uuid4().hex
    key = key or EDGE_DEVICE_KEYS[device_id]
    payload = copy.deepcopy(payload)       # the envelope must not alias the caller's dict
    body = {"device_id": device_id, "nonce": nonce, "ts": round(ts, 3), "payload": payload}
    sig = hmac.new(key, _canonical(body), hashlib.sha256).hexdigest()
    return body | {"signature": sig}


def verify_envelope(env: Dict, seen_nonces: Set[str], now: Optional[float] = None) -> Tuple[bool, str]:
    """Return (accepted, reason). Does NOT record the nonce; the caller does so
    after the request has been fully processed."""
    now = time.time() if now is None else now
    try:
        device_id, nonce, ts, payload, sig = (env["device_id"], env["nonce"], env["ts"],
                                              env["payload"], env["signature"])
    except KeyError as exc:
        return False, f"malformed envelope (missing {exc.args[0]})"
    key = EDGE_DEVICE_KEYS.get(device_id)
    if key is None:
        return False, "unknown edge device"
    body = {"device_id": device_id, "nonce": nonce, "ts": ts, "payload": payload}
    expected = hmac.new(key, _canonical(body), hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, str(sig)):
        return False, "signature mismatch (payload altered or wrong key)"
    if abs(now - float(ts)) > TELEMETRY_MAX_AGE_S:
        return False, "stale telemetry (outside freshness window)"
    if nonce in seen_nonces:
        return False, "replayed nonce"
    imei = str(payload.get("imei", ""))
    if not luhn_valid(imei):
        return False, "implausible IMEI (checksum failed)"
    if not -120 <= float(payload.get("rssi_dbm", -70)) <= -30:
        return False, "implausible RSSI"
    for f in ("old_sim_last_seen_min", "distance_from_home_km", "cell_changes_24h", "device_age_days"):
        if float(payload.get(f, 0)) < 0:
            return False, f"negative value for {f}"
    return True, "ok"
