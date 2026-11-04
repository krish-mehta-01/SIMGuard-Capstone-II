"""
SQLite persistence for the risk engine (off-chain record of every decision).

The database holds the full decision record, the SHAP explanation and the IMEI
blacklist. It is deliberately *not* trusted for integrity: the hashes anchored in
the smart contract are what a later audit compares it against.
"""

import json
import sqlite3
import sys
from contextlib import contextmanager
from pathlib import Path
from typing import Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import DB_PATH  # noqa: E402

SCHEMA = """
CREATE TABLE IF NOT EXISTS decisions (
    request_id      TEXT PRIMARY KEY,
    entry_id        INTEGER,
    subscriber_ref  TEXT NOT NULL,
    msisdn_masked   TEXT NOT NULL,
    channel         TEXT NOT NULL,
    agent_ref       TEXT NOT NULL,
    decision        TEXT NOT NULL,
    risk_score      REAL NOT NULL,
    ml_probability  REAL NOT NULL,
    rule_flags      TEXT NOT NULL,
    rule_detail     TEXT NOT NULL,
    model_version   TEXT NOT NULL,
    timestamp       TEXT NOT NULL,
    base_value      REAL NOT NULL,
    contributions   TEXT NOT NULL,
    features        TEXT NOT NULL,
    reasons         TEXT NOT NULL,
    summary         TEXT NOT NULL,
    edge_device     TEXT,
    decision_hash   TEXT NOT NULL,
    shap_hash       TEXT NOT NULL,
    tx_hash         TEXT,
    block_number    INTEGER,
    gas_used        INTEGER,
    latency_ms      TEXT NOT NULL,
    resolution      TEXT
);
CREATE INDEX IF NOT EXISTS idx_decisions_entry ON decisions(entry_id);
CREATE TABLE IF NOT EXISTS imei_blacklist (
    imei    TEXT PRIMARY KEY,
    reason  TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS used_nonces (
    nonce      TEXT PRIMARY KEY,
    device_id  TEXT NOT NULL,
    ts         REAL NOT NULL
);
"""

JSON_COLS = ("rule_flags", "rule_detail", "contributions", "features", "reasons", "latency_ms", "resolution")


class Store:
    def __init__(self, path: Path = DB_PATH):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.conn() as c:
            c.executescript(SCHEMA)

    @contextmanager
    def conn(self):
        c = sqlite3.connect(self.path, timeout=30)
        c.row_factory = sqlite3.Row
        try:
            yield c
            c.commit()
        finally:
            c.close()

    @staticmethod
    def _row(row: Optional[sqlite3.Row]) -> Optional[Dict]:
        if row is None:
            return None
        d = dict(row)
        for k in JSON_COLS:
            if d.get(k) is not None:
                d[k] = json.loads(d[k])
        return d

    # --- blacklist / nonces ------------------------------------------------
    def seed_blacklist(self, imeis: Dict[str, str]):
        with self.conn() as c:
            c.executemany("INSERT OR IGNORE INTO imei_blacklist(imei, reason) VALUES (?, ?)", imeis.items())

    def is_blacklisted(self, imei: str) -> bool:
        with self.conn() as c:
            return c.execute("SELECT 1 FROM imei_blacklist WHERE imei = ?", (imei,)).fetchone() is not None

    def blacklist_size(self) -> int:
        with self.conn() as c:
            return c.execute("SELECT COUNT(*) FROM imei_blacklist").fetchone()[0]

    def nonce_seen(self, nonce: str) -> bool:
        with self.conn() as c:
            return c.execute("SELECT 1 FROM used_nonces WHERE nonce = ?", (nonce,)).fetchone() is not None

    def remember_nonce(self, nonce: str, device_id: str, ts: float):
        with self.conn() as c:
            c.execute("INSERT OR IGNORE INTO used_nonces(nonce, device_id, ts) VALUES (?, ?, ?)",
                      (nonce, device_id, ts))

    # --- decisions ---------------------------------------------------------
    def insert_decision(self, rec: Dict):
        cols = list(rec.keys())
        vals = [json.dumps(rec[k]) if k in JSON_COLS else rec[k] for k in cols]
        with self.conn() as c:
            c.execute(f"INSERT INTO decisions({','.join(cols)}) VALUES ({','.join('?' * len(cols))})", vals)

    def get_decision(self, request_id: str) -> Optional[Dict]:
        with self.conn() as c:
            return self._row(c.execute("SELECT * FROM decisions WHERE request_id = ?", (request_id,)).fetchone())

    def get_by_entry(self, entry_id: int) -> Optional[Dict]:
        with self.conn() as c:
            return self._row(c.execute("SELECT * FROM decisions WHERE entry_id = ?", (entry_id,)).fetchone())

    def list_decisions(self, limit: int = 50, decision: Optional[str] = None) -> List[Dict]:
        q, args = "SELECT * FROM decisions", []
        if decision:
            q += " WHERE decision = ?"
            args.append(decision)
        q += " ORDER BY entry_id DESC LIMIT ?"
        args.append(limit)
        with self.conn() as c:
            return [self._row(r) for r in c.execute(q, args).fetchall()]

    def all_decisions(self) -> List[Dict]:
        with self.conn() as c:
            return [self._row(r) for r in c.execute("SELECT * FROM decisions ORDER BY entry_id").fetchall()]

    def count_decisions(self) -> int:
        with self.conn() as c:
            return c.execute("SELECT COUNT(*) FROM decisions").fetchone()[0]

    def update_field(self, request_id: str, field: str, value):
        if field not in {"decision", "risk_score", "contributions", "features", "rule_flags",
                         "ml_probability", "resolution"}:
            raise ValueError("field not editable")
        v = json.dumps(value) if field in JSON_COLS else value
        with self.conn() as c:
            c.execute(f"UPDATE decisions SET {field} = ? WHERE request_id = ?", (v, request_id))

    def delete_decision(self, request_id: str):
        with self.conn() as c:
            c.execute("DELETE FROM decisions WHERE request_id = ?", (request_id,))

    def reset(self):
        with self.conn() as c:
            c.execute("DELETE FROM decisions")
            c.execute("DELETE FROM used_nonces")
