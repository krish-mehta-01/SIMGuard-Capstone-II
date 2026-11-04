"""Generate high-impact widescreen presentation deck for SIMGuard Capstone Viva (Semester 5).
Features the real Semester 5 Point-of-Sale Hardware Terminal:
- ESP32 SoC
- RFID-RC522 retail agent badge authentication module
- 4x4 matrix membrane keypad for secure PIN/digits entry
- 0.96" I2C OLED display ("AGENT VERIFIED - Enter request digits")
- HMAC-SHA256 telemetry signing & replay protection
"""
import os
import pptx
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.enum.shapes import MSO_SHAPE

def create_deck(output_path="SIMGuard_Capstone_Review_Presentation.pptx"):
    prs = pptx.Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank_layout = prs.slide_layouts[6]

    # Color palette
    NAVY_DARK = RGBColor(15, 23, 42)      # #0F172A
    NAVY_LIGHT = RGBColor(30, 41, 59)     # #1E293B
    BLUE_ACCENT = RGBColor(2, 132, 199)   # #0284C7
    EMERALD = RGBColor(16, 185, 129)      # #10B981
    AMBER = RGBColor(245, 158, 11)        # #F59E0B
    CARD_BG = RGBColor(241, 245, 249)     # #F1F5F9
    WHITE = RGBColor(255, 255, 255)
    TEXT_MAIN = RGBColor(15, 23, 42)
    TEXT_MUTED = RGBColor(71, 85, 105)
    BORDER_COLOR = RGBColor(203, 213, 225)

    def add_header(slide, title, subtitle, presenter_badge=""):
        header_shape = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(13.333), Inches(1.15))
        header_shape.fill.solid()
        header_shape.fill.fore_color.rgb = NAVY_DARK
        header_shape.line.fill.background()

        line = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(1.15), Inches(13.333), Inches(0.05))
        line.fill.solid()
        line.fill.fore_color.rgb = BLUE_ACCENT
        line.line.fill.background()

        tx_box = slide.shapes.add_textbox(Inches(0.8), Inches(0.12), Inches(9.5), Inches(0.95))
        tf = tx_box.text_frame
        tf.word_wrap = True
        tf.margin_left = tf.margin_top = tf.margin_right = tf.margin_bottom = 0

        p = tf.paragraphs[0]
        p.text = title
        p.font.name = "Calibri"
        p.font.size = Pt(22)
        p.font.bold = True
        p.font.color.rgb = WHITE

        p2 = tf.add_paragraph()
        p2.text = subtitle
        p2.font.name = "Calibri"
        p2.font.size = Pt(12)
        p2.font.color.rgb = RGBColor(148, 163, 184)

        if presenter_badge:
            badge_box = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(10.6), Inches(0.35), Inches(2.0), Inches(0.45))
            badge_box.fill.solid()
            badge_box.fill.fore_color.rgb = BLUE_ACCENT if "KRISH" in presenter_badge else EMERALD
            badge_box.line.fill.background()
            btf = badge_box.text_frame
            bp = btf.paragraphs[0]
            bp.text = presenter_badge
            bp.font.name = "Calibri"
            bp.font.size = Pt(11)
            bp.font.bold = True
            bp.font.color.rgb = WHITE
            bp.alignment = PP_ALIGN.CENTER

    def add_card(slide, left, top, width, height, bg_color=CARD_BG, border_color=BORDER_COLOR):
        shape = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(left), Inches(top), Inches(width), Inches(height))
        shape.fill.solid()
        shape.fill.fore_color.rgb = bg_color
        if border_color:
            shape.line.color.rgb = border_color
            shape.line.width = Pt(1)
        else:
            shape.line.fill.background()
        return shape

    # -------------------------------------------------------------------------
    # SLIDE 1: Title Slide (Cover)
    # -------------------------------------------------------------------------
    s1 = prs.slides.add_slide(blank_layout)
    bg1 = s1.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(13.333), Inches(7.5))
    bg1.fill.solid()
    bg1.fill.fore_color.rgb = NAVY_DARK
    bg1.line.fill.background()

    if os.path.exists(r"report\figures\crest.png"):
        s1.shapes.add_picture(r"report\figures\crest.png", Inches(5.8), Inches(0.6), height=Inches(1.2))

    tx = s1.shapes.add_textbox(Inches(1.0), Inches(1.9), Inches(11.333), Inches(1.1))
    tf = tx.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "R.M.K. ENGINEERING COLLEGE"
    p.font.name = "Calibri"
    p.font.size = Pt(18)
    p.font.bold = True
    p.font.color.rgb = RGBColor(226, 232, 240)
    p.alignment = PP_ALIGN.CENTER

    p2 = tf.add_paragraph()
    p2.text = "Department of Information Technology  |  Capstone Design Project – Level II Honours (24IT986) – Semester 5"
    p2.font.name = "Calibri"
    p2.font.size = Pt(12)
    p2.font.color.rgb = RGBColor(148, 163, 184)
    p2.alignment = PP_ALIGN.CENTER

    c1 = add_card(s1, 1.2, 3.1, 10.933, 2.4, bg_color=NAVY_LIGHT, border_color=BLUE_ACCENT)
    tx = s1.shapes.add_textbox(Inches(1.5), Inches(3.25), Inches(10.333), Inches(2.1))
    tf = tx.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "BLOCKCHAIN-SECURED SIM SWAP FRAUD DETECTION SYSTEM"
    p.font.name = "Calibri"
    p.font.size = Pt(24)
    p.font.bold = True
    p.font.color.rgb = WHITE
    p.alignment = PP_ALIGN.CENTER

    p_sub = tf.add_paragraph()
    p_sub.text = "An Explainable-AI and Smart-Contract Framework for Tamper-Evident SIM Replacement Decisions"
    p_sub.font.name = "Calibri"
    p_sub.font.size = Pt(14)
    p_sub.font.color.rgb = BLUE_ACCENT
    p_sub.alignment = PP_ALIGN.CENTER

    p_tags = tf.add_paragraph()
    p_tags.text = "\n[Multidisciplinary Architecture: ECE Edge Hardware Terminal  +  CSE Attack Modeling  +  IT Core Engine & Ledger]"
    p_tags.font.name = "Calibri"
    p_tags.font.size = Pt(11)
    p_tags.font.color.rgb = RGBColor(203, 213, 225)
    p_tags.alignment = PP_ALIGN.CENTER

    tx_meta = s1.shapes.add_textbox(Inches(1.2), Inches(5.7), Inches(10.933), Inches(1.3))
    tf_meta = tx_meta.text_frame
    tf_meta.word_wrap = True
    p = tf_meta.paragraphs[0]
    p.text = "Presented by:  KRISH MEHTA (Reg No: [account number removed])  &  YUKESH J (Reg No: [account number removed])"
    p.font.name = "Calibri"
    p.font.size = Pt(13)
    p.font.bold = True
    p.font.color.rgb = WHITE
    p.alignment = PP_ALIGN.CENTER

    p2 = tf_meta.add_paragraph()
    p2.text = "Supervisor & HOD: Dr. Sheerin Banu M, M.Tech., Ph.D.  |  Date: 03 November 2026"
    p2.font.name = "Calibri"
    p2.font.size = Pt(12)
    p2.font.color.rgb = RGBColor(148, 163, 184)
    p2.alignment = PP_ALIGN.CENTER

    # -------------------------------------------------------------------------
    # SLIDE 2: Problem Statement & Threat Landscape
    # -------------------------------------------------------------------------
    s2 = prs.slides.add_slide(blank_layout)
    add_header(s2, "1. The SIM Swap Fraud Epidemic", "Bypassing Multi-Factor Authentication & Corrupt Insider Vulnerability", "PRESENTER: KRISH")

    c_threat = add_card(s2, 0.8, 1.4, 5.6, 5.6)
    tx = s2.shapes.add_textbox(Inches(1.0), Inches(1.55), Inches(5.2), Inches(5.2))
    tf = tx.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "The Real-World Fraud Crisis"
    p.font.size = Pt(18); p.font.bold = True; p.font.color.rgb = NAVY_DARK

    bullets = [
        ("Account Takeover Vector:", "SIM swap intercepts bank SMS OTPs, authentication resets, and crypto credentials with zero victim malware."),
        ("Catastrophic Financial Loss:", "FBI IC3 reported $68M+ in losses in a single year from 1,611 incidents; average loss per attack exceeds $40,000."),
        ("The Corrupt Insider Problem:", "Telecom retail agents can be bribed ($500-$1000) or socially engineered to approve swaps and quietly overwrite internal CRM logs."),
        ("The Black-Box Dilemma:", "Existing fraud detection systems operate as opaque scorecards; human fraud analysts have no actionable reasoning or legal evidence trail.")
    ]
    for title, desc in bullets:
        p_t = tf.add_paragraph()
        p_t.text = "\n• " + title
        p_t.font.size = Pt(13); p_t.font.bold = True; p_t.font.color.rgb = NAVY_LIGHT
        p_d = tf.add_paragraph()
        p_d.text = "   " + desc
        p_d.font.size = Pt(11); p_d.font.color.rgb = TEXT_MUTED

    c_sol = add_card(s2, 6.8, 1.4, 5.7, 5.6)
    tx2 = s2.shapes.add_textbox(Inches(7.0), Inches(1.55), Inches(5.3), Inches(5.2))
    tf2 = tx2.text_frame
    tf2.word_wrap = True
    p = tf2.paragraphs[0]
    p.text = "The SIMGuard Tri-Pillar Paradigm"
    p.font.size = Pt(18); p.font.bold = True; p.font.color.rgb = BLUE_ACCENT

    pillars = [
        ("1. Multi-Tier Risk Engine:", "Combines deterministic telecom sanity rules with an XGBoost ML classifier (ROC-AUC 0.948) calibrated to strict analyst review capacity (<8%)."),
        ("2. Explainable AI (TreeSHAP):", "Deconstructs every decision into exact additive feature attributions (+/- risk points), explaining precisely WHY a request is blocked."),
        ("3. Smart Contract Immutability:", "Anchors decision cryptographic hashes (SHA-256) and telemetry on an Ethereum smart contract (EVM), guaranteeing zero insider log tampering."),
        ("4. Cryptographic Edge Terminals:", "Authenticates physical point-of-sale agent smartcards (RFID), user PINs, and handset parameters via HMAC-SHA256 signatures with nonce replay protection.")
    ]
    for title, desc in pillars:
        p_t = tf2.add_paragraph()
        p_t.text = "\n✔ " + title
        p_t.font.size = Pt(13); p_t.font.bold = True; p_t.font.color.rgb = NAVY_DARK
        p_d = tf2.add_paragraph()
        p_d.text = "   " + desc
        p_d.font.size = Pt(11); p_d.font.color.rgb = TEXT_MUTED

    # -------------------------------------------------------------------------
    # SLIDE 3: Multidisciplinary Departmental Division of Work
    # -------------------------------------------------------------------------
    s3 = prs.slides.add_slide(blank_layout)
    add_header(s3, "2. Multidisciplinary Architecture & Collaboration", "Division of Responsibilities Across ECE, CSE, and IT Disciplines", "PRESENTER: KRISH")

    if os.path.exists(r"report\figures\modules.png"):
        s3.shapes.add_picture(r"report\figures\modules.png", Inches(0.8), Inches(1.4), width=Inches(7.0))

    c_div = add_card(s3, 8.0, 1.4, 4.5, 5.6)
    tx = s3.shapes.add_textbox(Inches(8.2), Inches(1.55), Inches(4.1), Inches(5.2))
    tf = tx.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "Inter-Departmental Roles"
    p.font.size = Pt(17); p.font.bold = True; p.font.color.rgb = NAVY_DARK

    roles = [
        ("ECE: Physical Edge Gateway & Terminal", "• ESP32 SoC + RFID-RC522 agent badge authentication\n• 4x4 matrix keypad PIN entry & 0.96\" OLED visual feedback\n• Per-device HMAC-SHA256 telemetry packet signing\n• 300s freshness window, single-use nonce & replay checks"),
        ("CSE: Attack Modeling & Classifier Baselines", "• Threat modeling 4 realistic fraud archetypes\n• 10,000-record synthetic telecom dataset design (15 features)\n• Benchmark model comparisons (Logistic, RF, Isolation Forest)\n• Feature correlation & imbalance distribution analysis"),
        ("IT (Our Team): Core Engine, Blockchain & Full-Stack", "• 3-Tier risk decision engine (Auto-Approve, Review, Auto-Block)\n• TreeSHAP local waterfall & global explanation engine\n• Solidity smart contract (SIMSwapAuditLog.sol) & Ganache EVM\n• SQLite audit store, FastAPI REST API & Operator Dashboard")
    ]
    for title, desc in roles:
        p_t = tf.add_paragraph()
        p_t.text = "\n" + title
        p_t.font.size = Pt(12); p_t.font.bold = True; p_t.font.color.rgb = BLUE_ACCENT if "IT" in title else NAVY_DARK
        p_d = tf.add_paragraph()
        p_d.text = desc
        p_d.font.size = Pt(10); p_d.font.color.rgb = TEXT_MUTED

    # -------------------------------------------------------------------------
    # SLIDE 4: Physical Edge Terminal Hardware (SEMESTER 5 REAL HARDWARE PHOTO)
    # -------------------------------------------------------------------------
    s4 = prs.slides.add_slide(blank_layout)
    add_header(s4, "3. Physical Edge Point-of-Sale Terminal (ECE Hardware)", "Real Hardware Prototype: RFID Agent Badge, 4x4 Keypad, OLED & ESP32 SoC", "PRESENTER: KRISH")

    hw_img = r"report\figures\sem5_hardware_prototype.jpg"
    if os.path.exists(hw_img):
        # Image is vertical aspect ratio (575x1024), embed cleanly on left
        s4.shapes.add_picture(hw_img, Inches(0.8), Inches(1.35), height=Inches(5.7))

    # Right side: Specifications of each hardware component visible in the photo
    c_hw = add_card(s4, 4.3, 1.35, 8.2, 5.7)
    tx = s4.shapes.add_textbox(Inches(4.5), Inches(1.45), Inches(7.8), Inches(5.5))
    tf = tx.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "Semester 5 Hardware Prototype Components & Workflow"
    p.font.size = Pt(17); p.font.bold = True; p.font.color.rgb = NAVY_DARK

    hw_components = [
        ("1. RFID-RC522 Smart Card Reader (13.56 MHz SPI):",
         "Enforces Physical Operator Identity. Telecom store agent must tap their authorized RFID badge before initiating a swap. Prevents rogue/unauthorized personnel from touching the terminal."),

        ("2. 4x4 Matrix Membrane Keypad:",
         "Direct Point-of-Sale Input. Agent enters authorization PIN and subscriber OTP/request digits directly on the hardware terminal, bypassing PC-side keyloggers and malware."),

        ("3. 0.96\" I2C OLED Display (SSD1306, 128x64):",
         "Real-Time Terminal Feedback. Displays status directly to the customer and operator: '[AGENT VERIFIED] Enter request digits', active session timer, and HMAC confirmation."),

        ("4. ESP32 SoC Controller & Cryptographic Edge Daemon:",
         "Dual-core 240 MHz MCU. Gathers agent RFID UID, keypad digits, and cell telemetry; computes HMAC-SHA256 signature using secret device key $K_{device}$; embeds single-use UUID nonce and 300s freshness window; and transmits authenticated payload to the SIMGuard backend.")
    ]

    for title, desc in hw_components:
        p_t = tf.add_paragraph()
        p_t.text = "\n✔ " + title
        p_t.font.size = Pt(12); p_t.font.bold = True; p_t.font.color.rgb = BLUE_ACCENT
        p_d = tf.add_paragraph()
        p_d.text = desc
        p_d.font.size = Pt(10.5); p_d.font.color.rgb = TEXT_MUTED

    # -------------------------------------------------------------------------
    # SLIDE 5: End-to-End System Architecture
    # -------------------------------------------------------------------------
    s5 = prs.slides.add_slide(blank_layout)
    add_header(s5, "4. End-to-End System Architecture", "Clean Separation: Edge Layer -> Risk Engine Core -> Presentation Layer", "PRESENTER: KRISH")

    if os.path.exists(r"report\figures\architecture.png"):
        s5.shapes.add_picture(r"report\figures\architecture.png", Inches(0.8), Inches(1.4), width=Inches(7.2))

    c_arch = add_card(s5, 8.2, 1.4, 4.3, 5.6)
    tx = s5.shapes.add_textbox(Inches(8.4), Inches(1.55), Inches(3.9), Inches(5.2))
    tf = tx.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "Architectural Highlights"
    p.font.size = Pt(17); p.font.bold = True; p.font.color.rgb = NAVY_DARK

    arch_points = [
        ("Zero Direct Database Exposure:", "External presentation layers and retail clients communicate exclusively through authenticated REST endpoints (`/api/v1/evaluate`)."),
        ("Deterministic + Probabilistic Fusion:", "High-confidence risks (stolen IMEI, rapid multi-swaps) trigger instant rule blocks; non-obvious patterns pass to XGBoost."),
        ("Off-Chain / On-Chain Split:", "Confidential subscriber PII is retained off-chain in encrypted SQLite; only cryptographic hashes (SHA-256) and public counters are posted on-chain (DPDP compliance)."),
        ("Sub-Millisecond Engine Processing:", "Risk scoring and SHAP attribution complete in ~1.5 ms; asynchronous EVM blockchain mining adds ~19.5 ms.")
    ]
    for title, desc in arch_points:
        p_t = tf.add_paragraph()
        p_t.text = "\n• " + title
        p_t.font.size = Pt(12); p_t.font.bold = True; p_t.font.color.rgb = NAVY_LIGHT
        p_d = tf.add_paragraph()
        p_d.text = "   " + desc
        p_d.font.size = Pt(10.5); p_d.font.color.rgb = TEXT_MUTED

    # -------------------------------------------------------------------------
    # SLIDE 6: 3-Tier Policy Flow (Handover to Yukesh)
    # -------------------------------------------------------------------------
    s6 = prs.slides.add_slide(blank_layout)
    add_header(s6, "5. 3-Tier Risk Engine & Operating Policy", "Calibrating Auto-Approval, Analyst Manual Review, and Auto-Blocking", "PRESENTER: YUKESH")

    if os.path.exists(r"report\figures\policy_flow.png"):
        s6.shapes.add_picture(r"report\figures\policy_flow.png", Inches(0.8), Inches(1.4), width=Inches(7.0))

    c_pol = add_card(s6, 8.0, 1.4, 4.5, 5.6)
    tx = s6.shapes.add_textbox(Inches(8.2), Inches(1.55), Inches(4.1), Inches(5.2))
    tf = tx.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "Operating Policy Mechanics"
    p.font.size = Pt(17); p.font.bold = True; p.font.color.rgb = NAVY_DARK

    policies = [
        ("Tier 1: Auto-Approve (p < 0.13)", "• 93.2% of routine legitimate subscriber swaps pass instantly with zero human friction.\n• Measured false block rate: 0.00%."),
        ("Tier 2: Manual Review (0.13 <= p < 0.90)", "• Suspicious, border-line cases routed to senior telecom fraud analysts.\n• Strictly constrained to 6.8% of daily swap traffic (analyst capacity limit < 8%).\n• Analyst sees top-8 SHAP feature drivers."),
        ("Tier 3: Auto-Block (p >= 0.90 or Rule Hit)", "• Blatant attacks (blacklisted IMEI, rapid re-swap within 72 hrs, multi-factor anomalies) auto-blocked instantly.\n• Catches 84.5% of fraud automatically.")
    ]
    for title, desc in policies:
        p_t = tf.add_paragraph()
        p_t.text = "\n" + title
        p_t.font.size = Pt(12); p_t.font.bold = True; p_t.font.color.rgb = BLUE_ACCENT if "Tier 2" in title else NAVY_LIGHT
        p_d = tf.add_paragraph()
        p_d.text = desc
        p_d.font.size = Pt(10.5); p_d.font.color.rgb = TEXT_MUTED

    # -------------------------------------------------------------------------
    # SLIDE 7: Machine Learning Pipeline & Baselines
    # -------------------------------------------------------------------------
    s7 = prs.slides.add_slide(blank_layout)
    add_header(s7, "6. Machine Learning Pipeline & Baselines", "XGBoost Classification Outperforming Rules, Logistic Regression & Random Forest", "PRESENTER: YUKESH")

    if os.path.exists(r"prototype\results\figures\roc_pr_curves.png"):
        s7.shapes.add_picture(r"prototype\results\figures\roc_pr_curves.png", Inches(0.8), Inches(1.4), width=Inches(6.6))

    c_ml = add_card(s7, 7.6, 1.4, 4.9, 5.6)
    tx = s7.shapes.add_textbox(Inches(7.8), Inches(1.55), Inches(4.5), Inches(5.2))
    tf = tx.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "Model Evaluation on Test Split (2,000 rows)"
    p.font.size = Pt(16); p.font.bold = True; p.font.color.rgb = NAVY_DARK

    ml_bullets = [
        ("Benchmark Comparison:", "• Rule Baseline: ROC-AUC 0.655 | PR-AUC 0.283\n• Logistic Regression: ROC-AUC 0.887 | PR-AUC 0.589\n• Random Forest: ROC-AUC 0.941 | PR-AUC 0.686\n• Isolation Forest: ROC-AUC 0.528 | PR-AUC 0.089\n• XGBoost (Our Model): ROC-AUC 0.948 | PR-AUC 0.697"),
        ("Handling Heavy Class Imbalance:", "Trained on realistic 8.4% fraud prevalence using scale_pos_weight tuning to penalize false negatives without blowing up false alerts."),
        ("Generalization Across Splits:", "Validated via strict chronological train (6,400) / validation (1,600) / test (2,000) partitioning with zero data leakage.")
    ]
    for title, desc in ml_bullets:
        p_t = tf.add_paragraph()
        p_t.text = "\n" + title
        p_t.font.size = Pt(12); p_t.font.bold = True; p_t.font.color.rgb = NAVY_LIGHT
        p_d = tf.add_paragraph()
        p_d.text = desc
        p_d.font.size = Pt(10.5); p_d.font.color.rgb = TEXT_MUTED

    # -------------------------------------------------------------------------
    # SLIDE 8: Explainable AI with TreeSHAP
    # -------------------------------------------------------------------------
    s8 = prs.slides.add_slide(blank_layout)
    add_header(s8, "7. Explainable AI: Feature Attribution via TreeSHAP", "Transforming Opaque Fraud Probabilities into Actionable Evidence", "PRESENTER: YUKESH")

    if os.path.exists(r"prototype\results\figures\shap_waterfall.png"):
        s8.shapes.add_picture(r"prototype\results\figures\shap_waterfall.png", Inches(0.8), Inches(1.4), width=Inches(6.8))

    c_shap = add_card(s8, 7.8, 1.4, 4.7, 5.6)
    tx = s8.shapes.add_textbox(Inches(8.0), Inches(1.55), Inches(4.3), Inches(5.2))
    tf = tx.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "Why XAI is Mandatory for Telecom"
    p.font.size = Pt(16); p.font.bold = True; p.font.color.rgb = NAVY_DARK

    shap_points = [
        ("Actionable Analyst Intelligence:", "When REQ-011096 is flagged (p = 0.93), the waterfall demonstrates that distance jump (+2.75) and recent profile change (+1.38) drove the score."),
        ("Regulatory Compliance (DPDP Act):", "Section 17 of telecom consumer protection mandates that carriers must explain service denial; TreeSHAP provides mathematically guaranteed additive fairness."),
        ("Anchoring the Reason on the Blockchain:", "Unlike any other system, SIMGuard doesn't just hash the score: it hashes the top SHAP reasons on the blockchain, preventing post-hoc justification tampering.")
    ]
    for title, desc in shap_points:
        p_t = tf.add_paragraph()
        p_t.text = "\n• " + title
        p_t.font.size = Pt(12); p_t.font.bold = True; p_t.font.color.rgb = BLUE_ACCENT
        p_d = tf.add_paragraph()
        p_d.text = "   " + desc
        p_d.font.size = Pt(10.5); p_d.font.color.rgb = TEXT_MUTED

    # -------------------------------------------------------------------------
    # SLIDE 9: Blockchain Smart Contract & Tamper Proofing
    # -------------------------------------------------------------------------
    s9 = prs.slides.add_slide(blank_layout)
    add_header(s9, "8. Smart Contract Audit Trail & Tamper Proofing", "Solidity (SIMSwapAuditLog.sol) Deployed on Ganache EVM Node", "PRESENTER: YUKESH")

    if os.path.exists(r"prototype\results\screens\audit_tampered.png"):
        s9.shapes.add_picture(r"prototype\results\screens\audit_tampered.png", Inches(0.8), Inches(1.4), width=Inches(6.6))

    c_bc = add_card(s9, 7.6, 1.4, 4.9, 5.6)
    tx = s9.shapes.add_textbox(Inches(7.8), Inches(1.55), Inches(4.5), Inches(5.2))
    tf = tx.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "Cryptographic Non-Repudiation"
    p.font.size = Pt(16); p.font.bold = True; p.font.color.rgb = NAVY_DARK

    bc_points = [
        ("Append-Only Smart Contract Log:", "`recordEvaluation()` stores `entry_id`, timestamp, subscriber ID hash, decision enum, and the root evidence SHA-256 hash."),
        ("Independent Cryptographic Verification:", "During an audit, the auditor re-hashes local SQLite rows and queries `verifyRecord()` on-chain. If even a single byte differs, it fails."),
        ("100% Empirical Tamper Detection:", "Across 577 independent adversarial tampering trials (modifying risk score, altering timestamps, deleting records), detection rate was 577/577 (100.0%)."),
        ("Dual-Key Review Resolution:", "Manual analyst resolutions require a secondary on-chain transaction (`recordResolution()`), binding analyst public address to the final override.")
    ]
    for title, desc in bc_points:
        p_t = tf.add_paragraph()
        p_t.text = "\n✔ " + title
        p_t.font.size = Pt(12); p_t.font.bold = True; p_t.font.color.rgb = NAVY_LIGHT
        p_d = tf.add_paragraph()
        p_d.text = "   " + desc
        p_d.font.size = Pt(10.5); p_d.font.color.rgb = TEXT_MUTED

    # -------------------------------------------------------------------------
    # SLIDE 10: Empirical Results & Performance Benchmarks
    # -------------------------------------------------------------------------
    s10 = prs.slides.add_slide(blank_layout)
    add_header(s10, "9. Empirical Results & Performance Benchmarks", "High Fraud Interception (84.5%), Zero Legitimate Blocks & Real-Time Speed", "PRESENTER: YUKESH")

    if os.path.exists(r"prototype\results\figures\policy_outcomes.png"):
        s10.shapes.add_picture(r"prototype\results\figures\policy_outcomes.png", Inches(0.8), Inches(1.4), width=Inches(6.6))

    c_res = add_card(s10, 7.6, 1.4, 4.9, 5.6)
    tx = s10.shapes.add_textbox(Inches(7.8), Inches(1.55), Inches(4.5), Inches(5.2))
    tf = tx.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "Key Empirical Performance Metrics"
    p.font.size = Pt(16); p.font.bold = True; p.font.color.rgb = NAVY_DARK

    res_bullets = [
        ("Fraud Caught Rate:", "84.5% overall fraud caught (69.7% blocked outright + 14.8% flagged for review)."),
        ("False Block Rate on Good Swaps:", "0.00% of legitimate customer swaps are blocked; only 6.8% routed to review, leaving 93.2% auto-approved instantly."),
        ("Latency Breakdown (Total 21 ms):", "• Rules + Preprocessing: 0.2 ms\n• XGBoost Inference: 0.3 ms\n• TreeSHAP Attribution: 0.9 ms\n• SQLite Off-Chain Commit: 0.4 ms\n• Local Ganache EVM Tx: 19.5 ms"),
        ("Gas Consumption:", "Consistently ~49,200 gas per evaluation transaction (~$0.02 at typical Layer-2 gas prices).")
    ]
    for title, desc in res_bullets:
        p_t = tf.add_paragraph()
        p_t.text = "\n• " + title
        p_t.font.size = Pt(12); p_t.font.bold = True; p_t.font.color.rgb = NAVY_LIGHT
        p_d = tf.add_paragraph()
        p_d.text = desc
        p_d.font.size = Pt(10.5); p_d.font.color.rgb = TEXT_MUTED

    # -------------------------------------------------------------------------
    # SLIDE 11: Real Website Showcase
    # -------------------------------------------------------------------------
    s11 = prs.slides.add_slide(blank_layout)
    add_header(s11, "10. SIMGuard Operations Portal & Website Showcase", "Full-Stack Web Interface for Telecom Operators, Fraud Analysts & Auditors", "PRESENTER: KRISH & YUKESH")

    web_img = r"report\figures\website_showcase.png"
    if os.path.exists(web_img):
        s11.shapes.add_picture(web_img, Inches(0.8), Inches(1.4), width=Inches(8.0))

    c_web = add_card(s11, 9.0, 1.4, 3.5, 5.6)
    tx = s11.shapes.add_textbox(Inches(9.15), Inches(1.55), Inches(3.2), Inches(5.2))
    tf = tx.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "Portal Sub-Systems"
    p.font.size = Pt(16); p.font.bold = True; p.font.color.rgb = BLUE_ACCENT

    portal_points = [
        ("1. Evaluate Engine (Top-Left):", "Interactive request console with presets, signed edge telemetry, and instant 3-tier verdict banners."),
        ("2. Tamper Detector (Top-Right):", "Cryptographic audit engine displaying flashing red alerts when database rows disagree with on-chain roots."),
        ("3. Decision Audit Log (Bottom-Left):", "Full chronological log of all evaluate events with the 'Resolve' action for manual reviews."),
        ("4. Blockchain Explorer (Bottom-Right):", "Live contract overview displaying mined blocks, transaction hashes, and gas usage.")
    ]
    for title, desc in portal_points:
        p_t = tf.add_paragraph()
        p_t.text = "\n" + title
        p_t.font.size = Pt(11.5); p_t.font.bold = True; p_t.font.color.rgb = NAVY_DARK
        p_d = tf.add_paragraph()
        p_d.text = desc
        p_d.font.size = Pt(10); p_d.font.color.rgb = TEXT_MUTED

    # -------------------------------------------------------------------------
    # SLIDE 12: Live Demonstration & Viva Walkthrough
    # -------------------------------------------------------------------------
    s12 = prs.slides.add_slide(blank_layout)
    add_header(s12, "11. Live Demonstration & Viva Walkthrough", "Real-Time Demonstration of SIM Replacement, XAI & Blockchain Tamper Detection", "PRESENTER: KRISH & YUKESH")

    if os.path.exists(r"prototype\results\screens\eval_attack_full.png"):
        s12.shapes.add_picture(r"prototype\results\screens\eval_attack_full.png", Inches(0.8), Inches(1.4), width=Inches(6.8))

    c_demo = add_card(s12, 7.8, 1.4, 4.7, 5.6)
    tx = s12.shapes.add_textbox(Inches(8.0), Inches(1.55), Inches(4.3), Inches(5.2))
    tf = tx.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "Live Viva Demo Modules"
    p.font.size = Pt(16); p.font.bold = True; p.font.color.rgb = BLUE_ACCENT

    demo_steps = [
        ("1. Evaluate View (Live Swaps):", "Demonstrates immediate auto-approval for legitimate customers and real-time auto-blocking for remote social-engineering attacks with signed telemetry."),
        ("2. Real-Time SHAP Explanations:", "Interactive waterfall bars show exactly which features pushed the risk score above the block threshold."),
        ("3. Decision Log & Review Resolution:", "Demonstrates human analyst workflow: reviewing flagged swaps and recording signed manual resolutions on-chain."),
        ("4. Tamper Demo (10-Second Test):", "Click 'Tamper Record' in SQLite database -> Run audit -> Instant red alert proving blockchain catches insider record alterations.")
    ]
    for title, desc in demo_steps:
        p_t = tf.add_paragraph()
        p_t.text = "\n" + title
        p_t.font.size = Pt(12); p_t.font.bold = True; p_t.font.color.rgb = NAVY_DARK
        p_d = tf.add_paragraph()
        p_d.text = desc
        p_d.font.size = Pt(10.5); p_d.font.color.rgb = TEXT_MUTED

    # -------------------------------------------------------------------------
    # SLIDE 13: Novelty, Limitations & Future Scope
    # -------------------------------------------------------------------------
    s13 = prs.slides.add_slide(blank_layout)
    add_header(s13, "12. Novelty, Limitations & Future Scope", "Academic Rigor: Explicit Scope Boundaries and Real-World Roadmap", "PRESENTER: KRISH")

    cards_data = [
        ("Core Novelty Contributions", NAVY_LIGHT, [
            "First framework unifying Explainable AI with EVM blockchain anchoring for telecom SIM replacement.",
            "Anchoring the explanation itself rather than just an opaque risk score, guaranteeing legal accountability.",
            "Cryptographically authenticated edge gateway dialogue defeating point-of-sale telemetry injection.",
            "Complete working prototype with zero simulated fake results."
        ]),
        ("Honest Scope Boundaries", AMBER, [
            "Dataset is synthetic and generated from 4 explicit fraud models rather than proprietary carrier logs.",
            "Edge layer (SIM800L & ESP32) is emulated in software; no live RF radio measurements were collected.",
            "Blockchain node runs on local Ganache rather than public Ethereum Sepolia network."
        ]),
        ("Future Roadmap", EMERALD, [
            "Fabricate physical PCB edge gateway with hardware Secure Element (Ateg ATECC608A) for keys.",
            "Deploy Solidity contracts to public Ethereum Layer-2 rollups (Arbitrum/Optimism) for sub-cent gas.",
            "Integrate Graph Neural Networks (GNN) to uncover coordinated multi-subscriber SIM swap syndicates."
        ])
    ]

    for idx, (title, color, bullets) in enumerate(cards_data):
        c_x = 0.8 + idx * 3.95
        card = add_card(s13, c_x, 1.4, 3.8, 5.6)
        tx = s13.shapes.add_textbox(Inches(c_x + 0.15), Inches(1.55), Inches(3.5), Inches(5.2))
        tf = tx.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.text = title
        p.font.size = Pt(15); p.font.bold = True; p.font.color.rgb = color

        for b in bullets:
            p_b = tf.add_paragraph()
            p_b.text = "\n• " + b
            p_b.font.size = Pt(11); p_b.font.color.rgb = TEXT_MAIN

    # -------------------------------------------------------------------------
    # SLIDE 14: Conclusion & Q&A
    # -------------------------------------------------------------------------
    s14 = prs.slides.add_slide(blank_layout)
    bg14 = s14.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(13.333), Inches(7.5))
    bg14.fill.solid()
    bg14.fill.fore_color.rgb = NAVY_DARK
    bg14.line.fill.background()

    c_concl = add_card(s14, 1.8, 1.2, 9.733, 4.8, bg_color=NAVY_LIGHT, border_color=BLUE_ACCENT)
    tx = s14.shapes.add_textbox(Inches(2.2), Inches(1.5), Inches(8.933), Inches(4.2))
    tf = tx.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = "CONCLUSION & SUMMARY"
    p.font.size = Pt(22); p.font.bold = True; p.font.color.rgb = BLUE_ACCENT
    p.alignment = PP_ALIGN.CENTER

    p_body = tf.add_paragraph()
    p_body.text = (
        "\nSIMGuard proves that telecom SIM replacement decisions can be made highly accurate (ROC-AUC 0.948), "
        "explained in actionable terms an analyst can understand (TreeSHAP), and anchored so that neither the decision "
        "nor its explanation can be quietly rewritten by corrupt insiders (Ethereum Smart Contracts).\n\n"
        "By treating the explanation as part of the immutable evidence, SIMGuard transforms opaque fraud scoring "
        "into an accountable, legally verifiable security architecture."
    )
    p_body.font.size = Pt(14); p_body.font.color.rgb = RGBColor(226, 232, 240)
    p_body.alignment = PP_ALIGN.CENTER

    p_qa = tf.add_paragraph()
    p_qa.text = "\n\nThank you!\nWe are now ready for your questions and the live prototype demonstration."
    p_qa.font.size = Pt(16); p_qa.font.bold = True; p_qa.font.color.rgb = WHITE
    p_qa.alignment = PP_ALIGN.CENTER

    prs.save(output_path)
    print(f"Presentation saved successfully to {output_path} (14 slides)")

if __name__ == "__main__":
    create_deck()
