"""Title page, certificate, acknowledgement, abstract, contents lists and abbreviations."""

from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.shared import Inches, Pt

from docx_kit import set_font

TITLE = "BLOCKCHAIN-SECURED SIM SWAP FRAUD DETECTION SYSTEM"
SUBTITLE = "AN EXPLAINABLE-AI AND SMART-CONTRACT FRAMEWORK FOR TAMPER-EVIDENT SIM REPLACEMENT DECISIONS"
TITLE_MIXED = "Blockchain-Secured SIM Swap Fraud Detection System: An Explainable-AI and Smart-Contract Framework"


def centered(r, text, size=14, bold=True, italic=False, after=6, before=0, break_before=False):
    para = r.doc.add_paragraph()
    para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    pf = para.paragraph_format
    pf.line_spacing_rule = WD_LINE_SPACING.SINGLE
    pf.space_after, pf.space_before = Pt(after), Pt(before)
    pf.page_break_before = break_before
    r._runs(para, text, size=size, bold=bold, italic=italic)
    return para


def plain_table(r, rows, widths, size=13, bold_first_col=False, align=None, bold_all=False):
    t = r.doc.add_table(rows=len(rows), cols=len(widths))
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = False
    for ri, row in enumerate(rows):
        for ci, text in enumerate(row):
            cell = t.rows[ri].cells[ci]
            cell.width = Inches(widths[ci])
            para = cell.paragraphs[0]
            para.paragraph_format.line_spacing_rule = WD_LINE_SPACING.SINGLE
            para.paragraph_format.space_after = Pt(2)
            para.paragraph_format.first_line_indent = Inches(0)
            if align:
                para.alignment = align[ci]
            r._runs(para, text, size=size, bold=bold_all or (bold_first_col and ci == 0))
    return t


def title_page(r):
    centered(r, TITLE, 16, after=4, before=6)
    centered(r, SUBTITLE, 12, after=26)
    centered(r, "A PROJECT REPORT", 12, after=2)
    centered(r, "Submitted by", 11, bold=True, italic=True, after=14)
    plain_table(r, [["Krish Mehta", "111724203048"], ["Yukesh J", "111724203124"]], [2.2, 2.0], size=14, bold_all=True,
                align=[WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.LEFT])
    centered(r, "in partial fulfillment for the award of the degree of", 11, bold=True, italic=True, after=10, before=26)
    centered(r, "BACHELOR OF TECHNOLOGY (HONOURS)", 14, after=0)
    centered(r, "IN", 14, after=0)
    centered(r, "INFORMATION TECHNOLOGY", 14, after=14)
    pic = r.doc.add_paragraph()
    pic.alignment = WD_ALIGN_PARAGRAPH.CENTER
    pic.add_run().add_picture(str(r.crest), width=Inches(0.95))
    centered(r, "R.M.K. ENGINEERING COLLEGE", 13, after=0, before=8)
    centered(r, "(An Autonomous Institution)", 12, after=0)
    centered(r, "R.S.M. Nagar, Kavaraipettai-601 206", 12, after=12)
    centered(r, "NOVEMBER 2026", 12, after=0)


def certificate(r):
    centered(r, "R.M.K. ENGINEERING COLLEGE", 18, after=0, break_before=True)
    centered(r, "(An Autonomous Institution)", 14, after=0)
    centered(r, "R.S.M. Nagar, Kavaraipettai-601 206", 12, after=20)
    centered(r, "BONAFIDE CERTIFICATE", 16, after=18)
    r.p(f"Certified that this project report **“{TITLE_MIXED}”** is the bonafide work of **KRISH MEHTA (111724203048), "
        "YUKESH J (111724203124)** who carried out the **[COURSE CODE] – Capstone Design Project – [LEVEL] Honors** under my supervision.",
        size=12, spacing=1.5)
    left = ["**SIGNATURE**", "", "**[HOD NAME], M.Tech., Ph.D.,**", "**Professor and Head**", "Department of Information Technology",
            "R.M.K. Engineering College", "R.S.M. Nagar, Kavaraipettai,", "Tiruvallur District – 601206."]
    right = ["**SIGNATURE**", "", "**[SUPERVISOR NAME], [QUALIFICATIONS],**", "**Supervisor**", "Department of Information Technology",
             "R.M.K. Engineering College", "R.S.M. Nagar, Kavaraipettai,", "Tiruvallur District – 601206."]
    t = r.doc.add_table(rows=1, cols=2)
    t.autofit = False
    for ci, lines in enumerate((left, right)):
        cell = t.rows[0].cells[ci]
        cell.width = Inches(3.1)
        first = True
        for line in lines:
            para = cell.paragraphs[0] if first else cell.add_paragraph()
            first = False
            para.paragraph_format.line_spacing_rule = WD_LINE_SPACING.SINGLE
            para.paragraph_format.space_after = Pt(1)
            para.paragraph_format.first_line_indent = Inches(0)
            r._runs(para, line, size=12)
    r.p("Submitted for the Project Viva-Voce held on **[DD-MM-YYYY]** at R.M.K. Engineering College, Kavaraipettai, "
        "Tiruvallur District – 601206.", size=12, align="left", indent=False, spacing=1.2, after=60).paragraph_format.space_before = Pt(36)
    plain_table(r, [["INTERNAL EXAMINER", "EXTERNAL EXAMINER"]], [3.1, 3.1], size=12, bold_first_col=False,
                align=[WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.RIGHT])


def acknowledgement(r):
    para = r.front_heading("Acknowledgement", size=16)
    para.paragraph_format.page_break_before = True
    paras = [
        "We earnestly portray our sincere gratitude and regard to our beloved Chairperson **Smt. Manjula Munirathinam,** Chairman "
        "**Shri. R. S. Munirathinam,** our Vice Chairman, **Shri. R. M. Kishore** and our Director, **Shri. R. Jothi Naidu,** for the "
        "interest and affection shown towards us throughout the course.",
        "We convey our sincere thanks to our Principal, **Dr. K. A. Mohamed Junaid,** for being the source of inspiration in this college.",
        "We reveal our sincere thanks to our Professor and Head of the Department, Information Technology, **[HOD NAME],** for the "
        "commendable support and encouragement for the completion of our project.",
        "We would like to express our sincere gratitude to our Project Coordinator **[PROJECT COORDINATOR NAME],** and our project guide "
        "**[GUIDE NAME],** Department of Information Technology, for their valuable suggestions towards the successful completion of this "
        "project in a global manner.",
        "We are thankful to the faculty of the Departments of Computer Science and Engineering and of Electronics and Communication "
        "Engineering for their guidance on the data-science and edge-hardware parts of this multidisciplinary project.",
        "We take this opportunity to extend our thanks to all faculty members of the Department of Information Technology, parents and "
        "friends for all that they meant to us during the crucial times of the completion of our project.",
    ]
    for t in paras:
        r.p(t, size=14, spacing=1.5, after=8)


def abstract(r, D):
    r.unnumbered("Abstract")
    h, x, c = D.hyb, D.xgb, D.chk
    tt, td = D.tamper_trials
    r.p("SIM swap fraud moves a victim's mobile number to an attacker's SIM, giving the attacker the one-time passwords that protect "
        "banking and e-mail accounts. Operator checklists fail against social engineering and insider collusion, and machine-learning "
        "detectors return unexplained scores that insiders can later edit out of the log.")
    r.p("**SIMGuard** combines three layers. At the edge (ECE), a SIM800L-based gateway signs handset and radio telemetry with "
        "HMAC-SHA256. In the data-science layer (CSE), XGBoost scores each request and TreeSHAP explains the score. In the governance "
        "layer (IT), a FastAPI risk engine merges the probability with deterministic rules and an IMEI blacklist into three tiers "
        "(auto-approve, manual review, auto-block) and anchors SHA-256 hashes of the decision and of its explanation in a Solidity "
        "smart contract.")
    r.p(f"On {D.split['test']:,} held-out synthetic requests XGBoost reaches ROC-AUC {x['roc_auc']:.3f} (static checklist "
        f"{D.models['Static rule checklist']['roc_auc']:.3f}); the engine sends {h['fraud_caught_pct']:.1f}% of fraud to review or block against "
        f"{c['fraud_caught_pct']:.1f}% for the checklist, reviewing {h['review_rate_pct']:.1f}% of requests. The audit detected {td} of {tt} "
        f"tampering attempts, whereas a hash chain an insider can recompute detected none. A decision takes a median of "
        f"{D.lat['decision_without_chain_ms']['median']:.0f} ms ({D.lat['components']['total_ms']['median']:.0f} ms with the blockchain write on a "
        f"local chain) and about {D.gas['log_median']:,} gas to anchor.")
    r.p("**KEYWORDS:** SIM swap fraud, XGBoost, TreeSHAP, Explainable AI, Ethereum smart contract, Solidity, risk engine, HMAC, "
        "edge telemetry, tamper-evident audit trail.", indent=False)


def contents(r):
    r.front_heading("Table of Contents", page_break=True)
    r.contents_table()


def figure_list(r):
    r.unnumbered("List of Figures")
    r.figures_table()


def build(r, D):
    title_page(r)
    certificate(r)
    acknowledgement(r)
    r.new_section("lowerRoman", 1, footer=True)
    abstract(r, D)
    contents(r)
    figure_list(r)
    r.new_section("decimal", 1, footer=True)
