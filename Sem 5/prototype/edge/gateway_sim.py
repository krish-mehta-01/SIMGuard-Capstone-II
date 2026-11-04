"""
Software emulation of the edge gateway's SIM800L GSM modem.

The physical gateway (SIM800L + microcontroller) is emulated here so the full
pipeline can be exercised and measured without hardware. The emulator speaks the
same AT-command dialogue the real modem does and the parser below is the code that
would run on the gateway firmware's host side:

    AT+GSN      -> IMEI of the handset in the slot
    AT+CCID     -> SIM serial number
    AT+CSQ      -> signal quality (0-31)  -> RSSI in dBm = -113 + 2 * value
    AT+CREG?    -> registration status
    AT+CENG?    -> serving cell id

Measured radio quantities that cannot come from a modem alone (time since the old
SIM was last seen, distance from the home cell, cell-change count) are supplied by
the network element (HLR/HSS probe); the emulator takes them from the request
record so that the held-out evaluation data drive the real code path.
"""

import hashlib
import re
from typing import Dict

from edge.telemetry import sign_envelope


class Sim800lEmulator:
    def __init__(self, record: Dict):
        self.r = record
        h = int(hashlib.sha256(str(record["request_id"]).encode()).hexdigest(), 16)
        self._csq = 8 + h % 20                    # 8..27
        self._cell = 40000 + (h >> 8) % 20000

    def send(self, cmd: str) -> str:
        cmd = cmd.strip()
        if cmd == "AT+GSN":
            return f"\r\n{self.r['new_imei']}\r\n\r\nOK\r\n"
        if cmd == "AT+CCID":
            serial = int(hashlib.sha256(self.r["msisdn"].encode()).hexdigest(), 16) % 10**15
            return "\r\n8991" + str(serial).zfill(15) + "\r\n\r\nOK\r\n"
        if cmd == "AT+CSQ":
            return f"\r\n+CSQ: {self._csq},0\r\n\r\nOK\r\n"
        if cmd == "AT+CREG?":
            stat = 5 if int(self.r["roaming_flag"]) else 1   # 1 home, 5 roaming
            return f"\r\n+CREG: 0,{stat}\r\n\r\nOK\r\n"
        if cmd == "AT+CENG?":
            return f"\r\n+CENG: 0,\"{self._cell},{self._csq},0,404,45\"\r\n\r\nOK\r\n"
        return "\r\nERROR\r\n"


def read_modem(modem: Sim800lEmulator) -> Dict:
    imei = re.search(r"(\d{15})", modem.send("AT+GSN")).group(1)
    csq = int(re.search(r"\+CSQ: (\d+)", modem.send("AT+CSQ")).group(1))
    creg = int(re.search(r"\+CREG: \d,(\d)", modem.send("AT+CREG?")).group(1))
    cell = int(re.search(r'"(\d+),', modem.send("AT+CENG?")).group(1))
    return {"imei": imei, "rssi_dbm": -113 + 2 * csq, "cell_id": cell, "roaming_flag": 1 if creg == 5 else 0}


def build_envelope(record: Dict, device_id: str = "EDGE-STORE-CHN-01", ts=None, nonce=None) -> Dict:
    """Read the (emulated) modem, add network-element measurements, sign the packet."""
    radio = read_modem(Sim800lEmulator(record))
    payload = radio | {
        "imei_changed": int(record["imei_changed"]),
        "device_age_days": float(record["device_age_days"]),
        "old_sim_last_seen_min": float(record["old_sim_last_seen_min"]),
        "distance_from_home_km": float(record["distance_from_home_km"]),
        "cell_changes_24h": float(record["cell_changes_24h"]),
    }
    return sign_envelope(device_id, payload, ts=ts, nonce=nonce)
