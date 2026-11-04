"""References, sample coding and screenshots."""

import ast
from pathlib import Path

import refs


def func_source(path, names):
    """Source of the named functions / methods, taken from the actual files so the listings never drift."""
    text = Path(path).read_text(encoding="utf-8")
    tree = ast.parse(text)
    wanted = {n: None for n in names}
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in wanted and wanted[node.name] is None:
            lines = text.splitlines()
            start = node.lineno - 1
            while start > 0 and lines[start - 1].lstrip().startswith("@"):
                start -= 1
            wanted[node.name] = "\n".join(_dedent(lines[start:node.end_lineno]))
    return "\n\n".join(wanted[n] for n in names if wanted[n])


def _dedent(lines):
    indent = min((len(l) - len(l.lstrip()) for l in lines if l.strip()), default=0)
    return [l[indent:] for l in lines]


def listing(r, title, intro, code, size=10):
    r.h4(title)
    r.p(intro)
    r.code(code, size=size)


def build(r, D):
    proto = r.protodir

    # ───────────────────────── REFERENCES ─────────────────────────
    r.unnumbered("References", align="left")
    for n, text in refs.entries():
        para = r.p(f"[{n}] {text}", indent=False, align="justify", size=14, after=6)

    # ───────────────────────── SAMPLE CODING ─────────────────────────
    r.unnumbered("Sample Coding", align="left")
    listing(r, "Audit Smart Contract (Solidity) - SIMSwapAuditLog.sol",
            "The contract appends one entry per decision and one optional resolution per manual review. It has no function that edits or "
            "deletes an entry; only addresses authorised by the owner can write; tier counters are updated on write so statistics are read "
            "in constant time.",
            (proto / "blockchain" / "SIMSwapAuditLog.sol").read_text(encoding="utf-8").strip("\n"))
    listing(r, "Deterministic Rules and Decision Policy (Python) - rules.py",
            "Six rules with severities, and the function that combines the model probability with the flags into the three-tier "
            "decision. A CRITICAL flag forces auto-block, a HIGH flag forces at least manual review, and each MEDIUM flag adds 0.10.",
            (proto / "risk_engine" / "rules.py").read_text(encoding="utf-8").split('"""', 2)[2].strip("\n"))
    listing(r, "Canonical Hashing and Pseudonymisation (Python) - chain.py",
            "Records are serialised as canonical JSON (sorted keys, no whitespace, fixed rounding) and hashed with SHA-256. The SHAP "
            "hash covers the contributions and the feature values they explain. The subscriber reference is an HMAC of the mobile number.",
            func_source(proto / "blockchain" / "chain.py",
                        ["canonical_json", "sha256_hex", "pseudonymise", "decision_record", "shap_record", "compute_hashes"]))
    listing(r, "Edge Telemetry Signing and Verification (Python) - telemetry.py",
            "The gateway signs the packet with HMAC-SHA256 over a language-neutral canonical encoding. The engine checks the device, "
            "signature, freshness, nonce and plausibility before any model inference.",
            func_source(proto / "edge" / "telemetry.py", ["_normalise", "_canonical", "luhn_valid", "sign_envelope", "verify_envelope"]))
    listing(r, "Risk Engine Evaluation Pipeline (Python) - engine.py",
            "One request from signed telemetry to anchored decision: verify, build features, score and explain, apply rules and policy, "
            "hash, anchor on the blockchain and store.",
            func_source(proto / "risk_engine" / "engine.py", ["evaluate"]))
    listing(r, "Integrity Audit (Python) - engine.py",
            "The audit reads every on-chain entry, recomputes the hashes of the matching off-chain record and reports edits, "
            "deletions and records that were never anchored.",
            func_source(proto / "risk_engine" / "engine.py", ["audit"]))
    listing(r, "Policy Calibration (Python) - train_model.py",
            "The review and block thresholds are chosen on the validation set by minimising an explicit operating cost under an analyst "
            "capacity limit.",
            func_source(proto / "ml" / "train_model.py", ["calibrate_policy"]))

    # ───────────────────────── SCREENSHOTS ─────────────────────────
    r.unnumbered("Screenshots", prefix="A")
    scr = proto / "results" / "screens"
    # request panel and anchor panel side by side, as one figure
    from PIL import Image
    left, right = Image.open(scr / "eval_attack_request.png").convert("RGB"), Image.open(scr / "eval_attack_chain.png").convert("RGB")
    gap = 40
    comp = Image.new("RGB", (left.width + gap + right.width, max(left.height, right.height)), "white")
    comp.paste(left, (0, 0))
    comp.paste(right, (left.width + gap, 0))
    comp_path = r.figdir / "shots_request_anchor.png"
    comp.save(comp_path)
    shots = [
        (scr / "eval_attack_full.png", "Operations console, Evaluate request view: a remote social-engineering attack is auto-blocked", "shot_overview", 6.3),
        (comp_path, "Request with signed edge telemetry (left) and blockchain anchor with processing time (right)", "shot_request", 6.1),
        (scr / "eval_legitimate_decision.png", "Decision panel: genuine upgrade, auto-approved", "shot_legit", 4.0),
        (scr / "eval_suspicious_decision.png", "Decision panel: suspicious request routed to manual review", "shot_suspicious", 4.0),
        (scr / "eval_attack_decision.png", "Decision panel: remote social-engineering attack, auto-blocked", "shot_attack", 4.0),
        (scr / "eval_blacklisted_decision.png", "Decision panel: blacklisted handset forces auto-block", "shot_black", 4.0),
        (scr / "decision_log.png", "Decision log with the Resolve action for manual reviews", "shot_log", 6.3),
        (scr / "resolve_dialog.png", "Analyst resolves a manual review; the outcome is recorded on-chain", "shot_dialog", 3.9),
        (scr / "ledger.png", "Blockchain ledger: contract details, counters and latest entries", "shot_ledger", 6.3),
        (scr / "audit_clean.png", "Integrity audit passed; four telemetry attacks rejected", "shot_audit_ok", 6.3),
        (scr / "audit_tampered.png", "Integrity audit exposes an insider's edit of a stored decision", "shot_audit_bad", 6.3),
        (scr / "model.png", "Model comparison and operating policy", "shot_model", 6.3),
    ]
    for path, cap, key, width in shots:
        r.figure(path, cap, key, width=width, max_height=4.4, center_caption=True)
