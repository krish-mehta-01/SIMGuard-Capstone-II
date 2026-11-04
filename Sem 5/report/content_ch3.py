"""Chapter 3: External interface requirements (user, hardware, software interfaces)."""

import sqlite3
import sys

from refs import cite


def build(r, D):
    r.chapter(3, "External Interface Requirements")
    user_interfaces(r, D)
    hardware_interfaces(r, D)
    software_interfaces(r, D)


def user_interfaces(r, D):
    r.h2("3.1 User Interfaces")
    r.p("The system provides two user-facing interfaces. The **operations console** is a web application for analysts, administrators and "
        "auditors; it carries every function a person needs without any command-line access. The **interactive API documentation** "
        "generated from the service's OpenAPI description lets developers and integrators try each endpoint. The two are served by "
        "the same risk-engine process and share one source of truth: every value on every console screen is returned by the API "
        "from the model, the database or the smart contract, and none is computed or invented in the browser.")
    r.p("**Evaluate request view.** The analyst chooses one of four scenarios, each a real held-out request: a genuine upgrade, a "
        "suspicious request, a remote social-engineering attack and a swap onto a blacklisted handset. The left panel shows the request "
        "fields and the signed edge telemetry with its verification status. The centre panel shows the decision with an icon, label and risk "
        "score, a gauge marking the review and block thresholds, the model probability, the rules that fired, and a diverging bar chart of "
        "the leading SHAP contributions with a plain-language summary. The right panel shows the blockchain anchor (ledger entry, block, "
        "transaction hash, gas, both hashes and the subscriber reference) and a breakdown of the time taken by each processing step. "
        f"The whole view is shown in {r.ref('shot_overview')}, the request and anchor panels in {r.ref('shot_request')} and the decision "
        f"panel for each scenario in {r.ref('shot_legit')}, {r.ref('shot_suspicious')}, {r.ref('shot_attack')} and {r.ref('shot_black')}.")
    r.p(f"**Decision log.** A filterable table of stored decisions with the entry number, time, masked subscriber number, channel, tier, "
        f"risk score, rules triggered and transaction. Requests in the manual-review tier carry a **Resolve** action that opens a dialog "
        f"for the analyst's final decision and written justification; the outcome is then recorded on-chain "
        f"({r.ref('shot_log')}, {r.ref('shot_dialog')}).")
    r.p(f"**Blockchain ledger.** Counters per tier read from the contract, the contract address, compiler, latest block and deployment gas, "
        f"and a table of the latest on-chain entries with their hashes and any analyst outcome ({r.ref('shot_ledger')}).")
    r.p(f"**Integrity audit.** An auditor can recompute every stored record's hashes and compare them with the chain. Two simulations "
        f"demonstrate the protection: an insider edit of the off-chain database (change a decision, alter an explanation, delete a record), "
        f"after which the audit lists exactly which entry was altered and how; and four attacks on the edge telemetry, each of which "
        f"the engine rejects with a stated reason ({r.ref('shot_audit_ok')}, {r.ref('shot_audit_bad')}).")
    r.p(f"**Model performance.** The held-out comparison of the five models, the operating policy (thresholds and cost weights) and the "
        f"ROC, precision-recall and feature-importance figures ({r.ref('shot_model')}).")


def hardware_interfaces(r, D):
    r.h2("3.2 Hardware Interfaces")
    r.p("The edge layer is designed around commodity components. In this prototype the modem and microcontroller are replaced by a "
        "software emulation that speaks the same AT-command dialogue and runs the same signing code, so the complete pipeline can be "
        "exercised and measured without hardware; the table states which interfaces are real and which are emulated.")
    r.table(["Component", "Interface", "Role", "Status in this prototype"], [
        ["SIM800L GSM module", "UART, AT commands; 3.4-4.4 V supply", "Reads handset IMEI, signal quality, registration status and serving cell", "Emulated (gateway_sim.py)"],
        ["Gateway microcontroller (ESP32 / Arduino class)", "UART to the modem; Wi-Fi or Ethernet to the engine", "Assembles the packet, holds the device key, computes HMAC-SHA256", "Signing code real; hardware not built"],
        ["SIM / handset slot", "ISO 7816 SIM contacts", "Presents the new SIM and handset at the point of sale", "Not applicable"],
        ["Network probe (HLR / HSS feed)", "Operator network API", "Time since the old SIM was seen, distance from home cell, cell changes", "Values supplied from the dataset"],
        ["Risk-engine host", "Ethernet, HTTP on localhost", "Runs the model, the API, SQLite and the Ethereum client", "Windows 11 laptop, Python 3.10"],
        ["Ethereum node", "JSON-RPC over HTTP, port 8545", "Hosts the audit contract", "Ganache 7.9.2 (local, chain id 1337)"],
    ], [1.55, 1.65, 1.85, 1.25], caption="Hardware interfaces", key="tab_hw", font=10)
    r.p(f"The SIM800L is controlled with the AT command set {cite('sim800')}. The gateway uses five commands, listed with the software "
        f"interfaces in Section 3.3. The microcontroller never sends raw modem output to the engine: it extracts the fields it needs and "
        f"signs the resulting packet, so the engine verifies an authenticated structure and not text that could be edited in transit.")


def software_interfaces(r, D):
    v = D.ver
    r.h2("3.3 Software Interfaces")
    r.p("The software stack and its versions in the measured prototype are listed below. All components are open source.")
    r.table(["Component", "Version", "Use"], [
        ["Python", f"{sys.version.split()[0]}", "Model, risk engine, API, experiments, report tooling"],
        ["XGBoost", v("xgboost"), "Gradient-boosted classifier and native TreeSHAP"],
        ["scikit-learn / pandas / NumPy", f"{v('scikit-learn')} / {v('pandas')} / {v('numpy')}", "Baselines, metrics, data handling"],
        ["FastAPI / Uvicorn / Pydantic", f"{v('fastapi')} / {v('uvicorn')} / {v('pydantic')}", "REST service, validation, OpenAPI documentation"],
        ["web3.py", v("web3"), "Ethereum JSON-RPC client"],
        ["Solidity compiler (solc-js)", "0.8.24", "Compiles SIMSwapAuditLog.sol (optimiser on, EVM version shanghai)"],
        ["Ganache", "7.9.2", "Local Ethereum node"],
        ["Node.js", "24.x", "Runs the compiler script and Ganache"],
        ["SQLite", sqlite3.sqlite_version, "Off-chain decision store"],
        ["pytest", v("pytest"), "43 automated tests"],
        ["Playwright + Chrome", v("playwright"), "Console screenshots and a JavaScript-error smoke test"],
        ["Browser", "HTML, CSS, JavaScript (no framework)", "Operations console"],
    ], [2.1, 1.7, 2.5], caption="Software stack", key="tab_sw", font=10)
    r.p("**REST API.** The risk engine exposes the following endpoints under /api/v1. Request and response bodies are JSON, validated "
        "by Pydantic models; invalid input returns 422, doctored telemetry 401 and a repeated request identifier 409.")
    r.table(["Method and path", "Purpose"], [
        ["POST /evaluate", "Evaluate one SIM replacement request; returns the decision, reasons, anchor and timings"],
        ["GET /decisions, /decisions/{id}", "List stored decisions (filter by tier) or fetch one"],
        ["POST /decisions/{id}/resolve", "Analyst outcome for a MANUAL_REVIEW decision, recorded on-chain"],
        ["GET /ledger", "On-chain entries, counters per tier and contract information"],
        ["GET /audit/verify", "Recompute every record's hashes and compare with the chain"],
        ["POST /demo/tamper, /demo/restore", "Simulate and undo an insider edit of the off-chain store"],
        ["POST /demo/edge-attack/{kind}", "Submit doctored telemetry (altered, replayed, stale, unknown device)"],
        ["GET /scenarios, /scenarios/{key}", "Real held-out requests, freshly signed, for the console presets"],
        ["GET /metrics, /health, /edge/rejections", "Model comparison and policy; service status; recent rejected packets"],
    ], [2.5, 3.8], caption="REST API endpoints", key="tab_api", font=10)
    r.p("**Signed telemetry packet.** The structure below is what the edge gateway sends and the engine verifies. The signature is an "
        "HMAC-SHA256 over the canonical JSON of the other four fields (sorted keys, no whitespace, integral numbers written as integers):")
    r.code('''{
  "device_id": "EDGE-STORE-CHN-01",
  "nonce": "3e49e9406bca4963bb260f35d58d526b",
  "ts": 1791430483.471,
  "payload": {
    "imei": "352092114951370", "rssi_dbm": -71, "cell_id": 51890, "roaming_flag": 0,
    "imei_changed": 1, "device_age_days": 0, "old_sim_last_seen_min": 12.4,
    "distance_from_home_km": 40.0, "cell_changes_24h": 3
  },
  "signature": "7b8a1d1ef6c1...d4fbf7"
}''')
    r.p("**Modem AT commands.** The gateway issues the following commands to the SIM800L:")
    r.table(["Command", "Returns", "Used for"], [
        ["AT+GSN", "15-digit IMEI of the handset", "Handset identity; blacklist lookup; Luhn check"],
        ["AT+CCID", "SIM serial number", "Identity of the SIM in the slot"],
        ["AT+CSQ", "Signal quality 0-31", "RSSI in dBm = -113 + 2 x value"],
        ["AT+CREG?", "Registration status (1 home, 5 roaming)", "roaming_flag"],
        ["AT+CENG?", "Serving cell identifier", "Cell id; cell-change count"],
    ], [1.3, 2.4, 2.6], caption="AT commands used by the edge gateway", key="tab_at", font=10)
    r.p(f"**Smart contract events.** Applications that monitor the ledger subscribe to three events: DecisionLogged (entry id, subscriber "
        f"reference, tier, risk in basis points, decision hash, SHAP hash), ReviewResolved (entry id, final tier, analyst reference, note "
        f"hash) and EngineAuthorized / EngineRevoked. The contract interface is summarised in {r.ref('tab_contract')} and the full source "
        f"is in the Sample Coding section.")
