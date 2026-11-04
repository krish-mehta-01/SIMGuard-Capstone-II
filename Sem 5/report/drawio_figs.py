"""The report's architecture / UML diagrams, authored as draw.io files (report/drawio/*.drawio) and rendered with
draw.io's own viewer to report/figures/*.png.   Run:  python drawio_figs.py

Layout rules used throughout (so nothing looks cramped when scaled to the page width):
  * at least 50 px between connected shapes, 60+ px wherever an edge carries a label
  * shapes are sized for their text with margin to spare (3-line ellipse labels get 90 px of height)
  * edge labels are short and sit in clear space, never on top of a shape
  * diagrams grow taller rather than denser (the page has plenty of height)"""

from pathlib import Path

from drawio_kit import Diagram, render_all

HERE = Path(__file__).resolve().parent


# ───────────────────────────── 1. use case ─────────────────────────────
def use_case():
    d = Diagram("use_case", 760, 600, fs=1.3)
    d.container(200, 10, 360, 520, "SIMGuard system", "gray", extra="align=center;spacingLeft=0;")
    names = ["Submit SIM replacement<br>request", "Sign and forward<br>edge telemetry", "Evaluate risk and<br>explain decision",
             "Anchor decision<br>on blockchain", "Resolve manual review", "Verify audit trail"]
    uc = []
    for i, n in enumerate(names):
        uc.append(d.ellipse(235, 55 + i * 78, 290, 62, n, "white"))
    agent = d.actor(80, 30, "Retail agent /<br>call-centre staff")
    edge = d.actor(80, 185, "Edge gateway<br>(SIM800L + MCU)")
    admin = d.actor(650, 190, "Network<br>administrator")
    analyst = d.actor(650, 340, "Fraud analyst")
    auditor = d.actor(650, 450, "Auditor /<br>regulator")
    for a, u in ((agent, 0), (edge, 1), (admin, 2), (admin, 3), (analyst, 4), (auditor, 5)):
        d.edge(a, uc[u], straight=True, end=False, color="#000000")
    return d


# ───────────────────────────── 2. architecture ─────────────────────────────
def architecture():
    d = Diagram("architecture", 910, 690, fs=1.35)
    d.container(265, 10, 340, 110, "Presentation layer", "gray")
    console = d.box(285, 52, 300, 54, "Operations console<br>(HTML / JS dashboard)", "white")

    d.container(10, 160, 170, 510, "Edge layer (ECE)", "green")
    h = d.box(25, 215, 140, 72, "Handset / SIM slot", "green")
    m = d.box(25, 345, 140, 72, "SIM800L modem<br>(AT commands)", "green")
    g = d.box(25, 475, 140, 72, "Gateway MCU<br>HMAC-SHA256 signer", "green")
    d.edge(h, m)
    d.edge(m, g)

    eng = d.container(265, 160, 340, 510, "Risk engine (IT)", "purple")
    ys = [215, 335, 455, 575]
    m1 = d.box(280, ys[0], 130, 72, "1. Telemetry<br>verifier", "purple")
    m2 = d.box(280, ys[1], 130, 72, "2. Feature<br>builder", "purple")
    m3 = d.box(280, ys[2], 130, 72, "3. XGBoost +<br>TreeSHAP (CSE)", "blue")
    m4 = d.box(280, ys[3], 130, 72, "4. Rules and<br>3-tier policy", "purple")
    m8 = d.box(465, ys[0], 130, 72, "8. REST API<br>(OpenAPI)", "purple")
    m7 = d.box(465, ys[1], 130, 72, "7. Audit and<br>verification", "purple")
    m6 = d.box(465, ys[2], 130, 72, "6. Anchoring<br>client (web3)", "purple")
    m5 = d.box(465, ys[3], 130, 72, "5. Hashing and<br>record store", "purple")
    for a, b in ((m1, m2), (m2, m3), (m3, m4), (m4, m5), (m5, m6), (m6, m7), (m7, m8)):
        d.edge(a, b)

    d.container(700, 160, 200, 250, "Blockchain layer", "orange")
    node = d.box(720, 215, 160, 72, "Ethereum node<br>(Ganache / Sepolia)", "orange")
    contract = d.box(720, 315, 160, 72, "SIMSwapAuditLog<br>(Solidity 0.8.24)", "orange")
    d.edge(node, contract)
    datac = d.container(700, 440, 200, 230, "Data layer", "yellow")
    d.box(720, 485, 160, 72, "SQLite<br>decision records", "yellow")
    d.box(720, 575, 160, 72, "IMEI blacklist,<br>used nonces", "yellow")

    d.edge(g, m1, "signed<br>packets", exit=(1, 0.5), entry=(0, 0.5))
    d.edge(console, m8, "HTTP / JSON", exit=(0.82, 1), entry=(0.5, 0), start=True, label_pos=-0.5)
    d.edge(m6, contract, "anchor", exit=(1, 0.5), entry=(0, 0.5))
    d.edge(datac, eng, "records,<br>lookups", exit=(0, 0.5), entry=(1, 0.77), start=True)
    return d


# ───────────────────────────── 3. data flow diagram ─────────────────────────────
def dfd():
    d = Diagram("dfd", 880, 960, fs=1.35)
    # external entities
    gw = d.box(10, 65, 150, 70, "Edge gateway", "green", rounded=False)
    agent = d.box(10, 200, 150, 70, "Retail agent /<br>call centre", "gray", rounded=False)
    analyst = d.box(10, 740, 150, 70, "Fraud analyst", "gray", rounded=False)
    auditor = d.box(325, 875, 150, 70, "Auditor /<br>regulator", "gray", rounded=False)
    # processes: one vertical chain in the middle, 51 px between ellipses
    x, w, h = 315, 170, 86
    p1 = d.ellipse(x, 57, w, h, "P1<br>Verify edge<br>telemetry", "purple")
    p2 = d.ellipse(x, 192, w, h, "P2<br>Build feature<br>vector", "purple")
    p3 = d.ellipse(x, 327, w, h, "P3<br>Score + explain<br>XGBoost, SHAP", "blue")
    p4 = d.ellipse(x, 462, w, h, "P4<br>Apply rules<br>and policy", "purple")
    p5 = d.ellipse(x, 597, w, h, "P5<br>Hash, anchor<br>and store", "purple")
    p6 = d.ellipse(x, 732, w, h, "P6<br>Resolve review<br>and audit", "purple")
    # data stores on the right
    d1 = d.store(650, 83, 160, 36, "D1  Used nonces")
    d4 = d.store(650, 487, 160, 36, "D4  IMEI blacklist")
    d3 = d.store(650, 591, 160, 36, "D3  On-chain ledger", "orange")
    d2 = d.store(650, 653, 160, 36, "D2  Decision records")

    d.edge(gw, p1, "signed packet", exit=(1, 0.5), entry=(0, 0.5))
    d.edge(d1, p1, "nonce check", exit=(0, 0.5), entry=(1, 0.5))
    d.edge(agent, p2, "request fields", exit=(1, 0.5), entry=(0, 0.5))
    d.edge(p1, p2, "verified", exit=(0.5, 1), entry=(0.5, 0))
    d.edge(p2, p3, "features", exit=(0.5, 1), entry=(0.5, 0))
    d.edge(p3, p4, "probability + SHAP", exit=(0.5, 1), entry=(0.5, 0))
    d.edge(d4, p4, "blacklist", exit=(0, 0.5), entry=(1, 0.5))
    d.edge(p4, p5, "decision", exit=(0.5, 1), entry=(0.5, 0))
    d.edge(p5, agent, "decision, reasons, anchor", exit=(0, 0.5), entry=(0.5, 1))
    d.edge(p5, d3, "hashes", exit=(0.855, 0.145), entry=(0, 0.5))
    d.edge(p5, d2, "record", exit=(0.855, 0.855), entry=(0, 0.5))
    d.edge(analyst, p6, "outcome", exit=(1, 0.5), entry=(0, 0.5))
    d.edge(d2, p6, "records", exit=(0.5, 1), entry=(1, 0.5))
    d.edge(d3, p6, "entries / resolution", exit=(1, 0.5), entry=(0.855, 0.855), start=True, pts=[(845, 609), (845, 806)],
           label_pos=0.4)
    d.edge(p6, auditor, "audit report", exit=(0.5, 1), entry=(0.5, 0))
    return d


# ───────────────────────────── 4. sequence ─────────────────────────────
def sequence():
    d = Diagram("sequence", 930, 800, fs=1.35)
    cols = [("Retail agent /<br>CRM", 75, "gray", 110), ("Edge<br>gateway", 215, "green", 100), ("Risk engine<br>API", 360, "purple", 110),
            ("XGBoost +<br>SHAP", 510, "blue", 100), ("SQLite", 635, "yellow", 90), ("Smart<br>contract", 755, "orange", 100),
            ("Fraud<br>analyst", 865, "gray", 90)]
    X = []
    for label, cx, col, w in cols:
        d.lifeline(cx, 10, w, 780, label, col, size=48)
        X.append(cx)
    y = 100
    msgs = [
        (0, 1, "1  read IMEI, cell, RSSI", False), (1, 0, "2  signed packet", True),
        (0, 2, "3  POST /evaluate {request, packet}", False),
        (2, 2, "4  verify HMAC, freshness, nonce, IMEI", None),
        (2, 4, "5  nonce and blacklist lookup", False), (4, 2, "6  result", True),
        (2, 3, "7  features", False), (3, 2, "8  probability + SHAP", True),
        (2, 2, "9  rules, risk score, 3-tier decision", None), (2, 2, "10  canonical JSON, SHA-256 hashes", None),
        (2, 5, "11  logDecision(ref, tier, risk, hashes)", False), (5, 2, "12  entryId, tx hash, gas", True),
        (2, 4, "13  store record + explanation", False), (2, 0, "14  decision, reasons, anchor", True),
        (2, 6, "15  MANUAL_REVIEW queue", False), (6, 2, "16  resolve(final decision, note)", False),
        (2, 5, "17  resolveReview(entryId, note hash)", False),
    ]
    for a, b, label, dashed in msgs:
        if dashed is None:
            d.activation(X[a], y - 14, 28)
            d.text(X[a] + 14, y - 16, 330, 32, label, font=11, align="left", extra="fillColor=#ffffff;")
        else:
            d.edge(label=label, p1=(X[a], y), p2=(X[b], y), straight=True, dashed=dashed, arrow="block",
                   end_arrow="open" if dashed else "block", extra="verticalAlign=bottom;spacingBottom=2;")
        y += 40
    return d


# ───────────────────────────── 5. ER ─────────────────────────────
def er():
    d = Diagram("er_diagram", 760, 560, fs=1.35)
    dec_rows = ["<b>PK</b>  request_id : TEXT", "<b>FK</b>  entry_id : INTEGER (chain id)",
                "subscriber_ref : HMAC pseudonym", "msisdn_masked, channel, agent_ref", "decision : 3 tiers",
                "risk_score, ml_probability", "rule_flags, rule_detail : JSON", "features, contributions : JSON",
                "reasons, summary", "decision_hash, shap_hash", "tx_hash, block_number, gas_used",
                "latency_ms : JSON", "resolution : JSON"]
    dec, dr = d.table(10, 20, 290, "decisions (SQLite, off-chain)", dec_rows, "yellow", row_h=22)
    ae_rows = ["<b>PK</b>  id : uint256", "subscriberRef : bytes32", "decisionHash : bytes32", "shapHash : bytes32",
               "timestamp : uint48", "riskBps : uint16", "decision : enum", "loggedBy : address"]
    ae, ar = d.table(500, 44, 240, "AuditEntry (on-chain)", ae_rows, "orange", row_h=22)
    res_rows = ["<b>FK</b>  entryId : uint256", "finalDecision : enum", "analystRef : bytes32", "noteHash : bytes32",
                "timestamp : uint48", "resolvedBy : address"]
    res, rr = d.table(500, 330, 240, "Resolution (on-chain)", res_rows, "orange", row_h=22)
    d.table(10, 400, 220, "imei_blacklist", ["<b>PK</b>  imei : TEXT", "reason : TEXT"], "yellow", row_h=22)
    d.table(260, 400, 220, "used_nonces", ["<b>PK</b>  nonce : TEXT", "device_id : TEXT", "ts : REAL"], "yellow", row_h=22)
    d.edge(dr[1], ar[0], "entry_id = id", exit=(1, 0.5), entry=(0, 0.5), straight=True, start_arrow="ERmandOne",
           end_arrow="ERmandOne")
    d.text(320, 110, 160, 70, "Recomputed hashes must equal the anchored hashes", font=11, color="#666666")
    d.edge(ae, res, "0..1 per MANUAL_REVIEW", exit=(0.5, 1), entry=(0.5, 0), straight=True, start_arrow="ERmandOne",
           end_arrow="ERzeroToOne")
    return d


# ───────────────────────────── 6. policy flowchart ─────────────────────────────
def policy_flow():
    d = Diagram("policy_flow", 720, 900, fs=1.3)
    n1 = d.box(90, 10, 300, 64, "Verified request +<br>ML fraud probability p", "blue", extra="arcSize=50;")
    n2 = d.box(90, 114, 300, 64, "Evaluate rules: flags<br>(CRITICAL / HIGH / MEDIUM)", "purple")
    n3 = d.box(90, 218, 300, 72, "risk = min(1, p + 0.10 ×<br>number of MEDIUM flags)", "purple")
    d1 = d.rhombus(55, 330, 370, 120, "any CRITICAL flag<br>or risk ≥ 0.90 ?", "white")
    blk = d.box(500, 360, 170, 60, "AUTO_BLOCK", "red", bold=True)
    d2 = d.rhombus(55, 500, 370, 120, "any HIGH flag<br>or risk ≥ 0.13 ?", "white")
    rev = d.box(500, 530, 170, 60, "MANUAL_REVIEW", "yellow", bold=True)
    app = d.box(125, 670, 230, 60, "AUTO_APPROVE", "green", bold=True)
    fin = d.box(20, 780, 520, 100, "Hash decision record and SHAP<br>explanation (SHA-256) → logDecision()<br>on the smart contract → store record in SQLite", "orange")
    d.edge(n1, n2)
    d.edge(n2, n3)
    d.edge(n3, d1)
    d.edge(d1, blk, "yes", exit=(1, 0.5), entry=(0, 0.5))
    d.edge(d1, d2, "no", exit=(0.5, 1), entry=(0.5, 0))
    d.edge(d2, rev, "yes", exit=(1, 0.5), entry=(0, 0.5))
    d.edge(d2, app, "no", exit=(0.5, 1), entry=(0.5, 0))
    d.edge(app, fin, exit=(0.5, 1), entry=(0.46, 0))
    d.edge(blk, fin, exit=(1, 0.5), entry=(1, 0.3), pts=[(700, 390), (700, 810)])
    d.edge(rev, fin, exit=(1, 0.5), entry=(1, 0.7), pts=[(690, 560), (690, 850)])
    return d


# ───────────────────────────── 7. anchoring ─────────────────────────────
def anchoring():
    d = Diagram("anchoring", 1060, 540, fs=1.3)
    d.container(10, 10, 420, 520, "Operator database (off-chain, mutable)", "yellow")
    r = d.box(30, 70, 180, 240, "Decision record<br><br>request_id, subscriber ref, decision, risk, rule flags, "
              "model version, timestamp", "yellow", font=14)
    s = d.box(230, 70, 180, 240, "SHAP explanation<br><br>base value, 16 contributions, 16 feature values", "yellow", font=14)
    h = d.box(30, 390, 380, 120, "Canonical JSON, then SHA-256<br>(decision hash, SHAP hash)", "purple", font=14)
    d.edge(r, h, exit=(0.5, 1), entry=(0.24, 0))
    d.edge(s, h, exit=(0.5, 1), entry=(0.76, 0))
    d.container(630, 10, 420, 520, "Smart contract (on-chain, append-only)", "orange")
    res = d.box(650, 70, 380, 130, "Resolution (optional, separate record)<br><br>final tier, analyst reference, note hash",
                "orange", font=14)
    ae = d.box(650, 380, 380, 130, "AuditEntry #n<br><br>decisionHash, shapHash, subscriberRef, "
               "risk (basis points), tier, timestamp", "orange", font=14)
    d.edge(h, ae, "logDecision()<br>at decision time", exit=(1, 0.3), entry=(0, 0.3), color="#b85450")
    d.edge(ae, h, "audit: recompute<br>and compare", exit=(0, 0.75), entry=(1, 0.75), dashed=True, color="#b85450")
    d.edge(ae, res, "optional: analyst resolution", exit=(0.5, 0), entry=(0.5, 1), end=True, dashed=True)
    return d


# ───────────────────────────── 8. work split across departments ─────────────────────────────
def modules():
    d = Diagram("modules", 960, 470, fs=1.3)
    cols = [("ECE: hardware edge", "green", 10, ["SIM800L GSM modem, AT-command interface", "Handset IMEI, cell id, RSSI, roaming status",
                                                  "Per-device HMAC-SHA256 signing", "Freshness window, single-use nonce",
                                                  "IMEI Luhn and RSSI plausibility checks"]),
            ("CSE: data science and AI", "blue", 340, ["Synthetic dataset, 4 attack archetypes", "XGBoost classifier + 4 baselines",
                                                       "TreeSHAP local and global explanations", "Validation-based threshold calibration",
                                                       "Held-out evaluation and ablations"]),
            ("IT: governance, security", "purple", 670, ["Cybersecurity risk engine (FastAPI)", "Deterministic rules, IMEI blacklist",
                                                         "Three-tier decision policy", "Solidity audit contract, web3 anchoring",
                                                         "SQLite store, console, integrity audit"])]
    ids = []
    for title, color, x, items in cols:
        ids.append(d.container(x, 10, 280, 450, title, color))
        for i, it in enumerate(items):
            d.box(x + 14, 62 + i * 77, 252, 66, it, color, font=14, extra="spacingLeft=6;spacingRight=6;")
    d.edge(ids[0], ids[1], exit=(1, 0.5), entry=(0, 0.5))
    d.edge(ids[1], ids[2], exit=(1, 0.5), entry=(0, 0.5))
    return d


def main():
    diagrams = [use_case(), architecture(), dfd(), sequence(), er(), policy_flow(), anchoring(), modules()]
    for d in diagrams:
        d.save(HERE / "drawio")
    render_all(diagrams, HERE / "figures", scale=3)
    print("done:", ", ".join(d.name for d in diagrams))


if __name__ == "__main__":
    main()
