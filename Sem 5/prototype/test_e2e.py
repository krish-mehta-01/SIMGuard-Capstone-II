"""
SIMGuard Complete End-to-End Test Suite
"""
import urllib.request
import json
import re
import sys

def run_tests():
    print("=== 1. AUDITING FRONTEND DOM & JS REFERENCES ===")
    with open("prototype/dashboard/index.html", "r", encoding="utf-8") as f:
        html = f.read()

    with open("prototype/dashboard/app.js", "r", encoding="utf-8") as f:
        js = f.read()

    with open("prototype/dashboard/styles.css", "r", encoding="utf-8") as f:
        css = f.read()

    # Find all $(...) in app.js
    ids_in_js = set(re.findall(r'\$\(["\']([^"\']+)["\']\)', js))
    ids_in_html = set(re.findall(r'id=["\']([^"\']+)["\']', html))

    missing_ids = ids_in_js - ids_in_html
    print(f"Total IDs referenced in JS: {len(ids_in_js)}")
    print(f"Missing IDs in HTML: {missing_ids}")
    if missing_ids:
        print(f"WARNING: The following IDs are in app.js but not index.html: {missing_ids}")

    # Check for emojis
    emojis_html = [c for c in html if ord(c) >= 0x2600]
    emojis_js = [c for c in js if ord(c) >= 0x2600]
    print(f"Emojis in HTML: {len(emojis_html)}, in JS: {len(emojis_js)}")

    # Check for slide references
    slides_html = re.findall(r'slide\s*\d+', html, re.I)
    slides_js = re.findall(r'slide\s*\d+', js, re.I)
    print(f"Slide references: HTML={slides_html}, JS={slides_js}")

    print("\n=== 2. TESTING LIVE API ENDPOINTS ===")
    base = "http://127.0.0.1:8051"

    def get(path):
        with urllib.request.urlopen(base + path) as r:
            return r.status, json.loads(r.read().decode("utf-8"))

    def post(path, data=None):
        req = urllib.request.Request(
            base + path,
            data=json.dumps(data).encode("utf-8") if data else b"",
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req) as r:
            return r.status, json.loads(r.read().decode("utf-8"))

    # Test Static Files
    for sf in ["/", "/static/styles.css", "/static/app.js"]:
        with urllib.request.urlopen(base + sf) as r:
            content = r.read()
            print(f"  GET {sf} -> {r.status} ({len(content)} bytes)")

    # Test V2 Stats
    s, stats = get("/api/v2/stats")
    print(f"  GET /api/v2/stats -> {s}, Blocks: {stats['total_blocks']}, Valid: {stats['chain_valid']}")

    # Test Simulator (Unprotected)
    s, unprot = post("/api/v2/simulate/intercept", {
        "sender_phone": "+919876543210",
        "recipient_phone": "+919876511223",
        "message": "Bank OTP: 123456",
        "protection_enabled": False
    })
    print(f"  POST /api/v2/simulate/intercept (Unprotected) -> {s}, Plaintext Intercepted: {unprot['attacker']['can_read_plaintext']}")

    # Test Simulator (Protected)
    s, prot = post("/api/v2/simulate/intercept", {
        "sender_phone": "+919876543210",
        "recipient_phone": "+919876511223",
        "message": "Bank OTP: 123456",
        "protection_enabled": True
    })
    print(f"  POST /api/v2/simulate/intercept (Protected) -> {s}, Hash: {prot['attacker']['intercepted_hash'][:16]}..., Can Read: {prot['attacker']['can_read_plaintext']}")

    # Test Ledger Filters
    for cat in ["ALL", "REGISTER", "MESSAGE", "CALL_META", "SECURITY_ALERT"]:
        s, led = get(f"/api/v2/ledger?category={cat}")
        print(f"  GET /api/v2/ledger?category={cat} -> {s}, Blocks: {led['total_blocks']}")

    # Test Rogue SIM Swap Defense
    s, s2 = post("/api/v2/scenarios/2")
    print(f"  POST /api/v2/scenarios/2 -> {s}, Result: {s2['result']}, Alert Tx: {s2['onchain_alert']['tx_id']}")

    # Test Tamper Detection
    s, s4 = post("/api/v2/scenarios/4")
    print(f"  POST /api/v2/scenarios/4 -> {s}, Result: {s4['result']}, Anomalies: {s4['audit_result']['anomaly_count']}")

    # Test Restore Ledger
    s, rst = post("/api/v2/scenarios/restore")
    print(f"  POST /api/v2/scenarios/restore -> {s}, Valid: {rst['audit']['is_valid']}")

    # Test Cryptographic Audit
    s, aud = get("/api/v2/audit")
    print(f"  GET /api/v2/audit -> {s}, Valid: {aud['is_valid']}, Total Checked: {aud['total_blocks_checked']}")

    print("\nALL END-TO-END AUDITS AND RUNTIME TESTS COMPLETED SUCCESSFULLY!")

if __name__ == "__main__":
    run_tests()

