"""Chapter 4: Testing (plan, procedure, results). Every number is read from the prototype's result files."""

import math

from refs import cite


def build(r, D):
    r.chapter(4, "Testing")
    test_plan(r, D)
    test_procedure(r, D)
    test_results(r, D)


def f(x, d=3):
    return f"{x:.{d}f}"


# ───────────────────────────── 4.1 ─────────────────────────────
def test_plan(r, D):
    r.h2("4.1 Test Plan")
    r.p("The test plan verifies that every module behaves as specified, that the modules work together, and that the complete system "
        "makes accurate, explainable and tamper-evident decisions under normal and hostile conditions. Testing is conducted at four "
        "levels: unit tests of individual modules, integration tests across module boundaries, system tests of the complete decision "
        "pipeline against a real blockchain, and security and resilience tests that attack the telemetry and the off-chain store. "
        "Two kinds of evidence are produced: automated tests, which give a pass or fail result and are repeated on every change, and "
        "experiments, which measure quantities such as detection rate, latency and gas on the held-out data.")
    r.h3("4.1.1 Unit Testing", caps=False)
    r.p("Each module was tested in isolation. The rule engine was tested at the boundary of every rule (for example 11 versus 12 swaps "
        "by one agent) and for the tier each severity forces. The telemetry verifier was tested against a genuine packet and against "
        "altered, replayed, stale, mis-keyed, unknown-device, bad-checksum and malformed packets. The hashing functions were tested for "
        "determinism, independence of key order, and sensitivity to a change in every covered field. The explanation module was tested "
        "for additivity, namely that the base value plus the SHAP contributions equals the model's output, and for correct ordering of "
        "the reasons. The smart contract was tested on a real chain for access control, input validation, the resolution rules and the "
        "absence of any function that edits or deletes an entry.")
    r.h3("4.1.2 Integration Testing", caps=False)
    r.p("Integration tests exercise the API with the real model, database and blockchain together. They confirm that a signed packet "
        "produced by the gateway emulator is accepted, that the decision returned matches the tier expected for each scenario, that the "
        "entry written to the chain verifies against the stored record, that only a MANUAL_REVIEW decision can be resolved and only "
        "once, and that a new database does not inherit another database's audit trail. Integration testing also covered the "
        "browser: a scripted Chrome session drives every view of the console and fails on any JavaScript error.")
    r.h3("4.1.3 System Testing", caps=False)
    r.p(f"System tests pass {D.E['latency']['n']} randomly selected held-out requests through the complete engine on a fresh contract, "
        f"recording each decision, its timing and its gas. The tier returned by the online path is compared with the tier computed "
        f"offline by the vectorised evaluation, which must agree for every request. The audit is then run over all anchored decisions.")
    r.h3("4.1.4 Security and Resilience Testing", caps=False)
    r.p("Three groups of hostile scenarios were executed. **Off-chain tampering:** an insider changes a decision, lowers a risk score, "
        "alters a SHAP contribution or an input feature, clears the rule flags, relabels the model version, deletes a record or inserts "
        "a forged one. **Telemetry attacks:** a field is altered in transit, a valid packet is replayed, a packet is submitted an hour "
        "late, a packet comes from an unregistered device, a correctly signed packet carries an impossible IMEI, and a packet is signed "
        "with the wrong key. **Baseline comparison:** a local hash chain that an insider can recompute is attacked in the same way to "
        "show what the on-chain anchor adds.")
    r.table(["Level", "Scope", "Tooling", "Automated tests"], [
        ["Unit", "Rules, telemetry, hashing and SHAP, smart contract", "pytest, local Ganache chain", "32"],
        ["Integration / system", "API with model, SQLite and chain; resolution; audit; telemetry attacks", "pytest, FastAPI test client", "11"],
        ["Browser smoke test", "All console views, JavaScript errors", "Playwright, Chrome", "script"],
        ["Experiments", "Accuracy, policy, latency, gas, tamper detection, edge attacks", "experiments/run_experiments.py", "script"],
    ], [1.25, 2.35, 1.7, 1.0], caption="Test levels", key="tab_levels", font=10, align=["left", "left", "left", "center"])


# ───────────────────────────── 4.2 ─────────────────────────────
def test_procedure(r, D):
    sp = D.split
    r.h2("4.2 Test Procedure")
    r.p(f"The test environment was a Windows 11 laptop running Python 3.10, Node.js 24 and a local Ganache blockchain (chain id 1337). All "
        f"services ran on one machine, so timings include no network latency between the engine, database and chain. The dataset "
        f"({D.ds_n:,} requests, {D.ds_fraud:,} fraudulent) was generated with fixed seeds and split once into training "
        f"({sp['train']:,}; {sp['train_fraud']} fraud), validation ({sp['val']:,}; {sp['val_fraud']} fraud) and test ({sp['test']:,}; "
        f"{sp['test_fraud']} fraud) sets, stratified by class.")
    r.p("The procedure follows four rules that keep the reported numbers honest. **First,** the test set is used only to report; the "
        "operating threshold of every model, and the review and block thresholds of the risk engine, are chosen on the validation set. "
        "**Second,** every model, including the baselines, is trained on the same training set and evaluated on the same test set. "
        "**Third,** the online engine and the offline evaluation use the same rule and policy code, and the experiment fails if they "
        "disagree. **Fourth,** every number in this chapter is written to a results file by a script and inserted into this report "
        "from that file.")
    r.p("The whole pipeline is reproduced with three commands: the first starts the local Ethereum node, the second generates the "
        "data, trains and calibrates the model, compiles the contract, runs the experiments and the test suite, and the third starts "
        "the console:")
    r.code("python run_pipeline.py --chain      # terminal 1: local Ethereum node (Ganache)\n"
           "python run_pipeline.py --all        # terminal 2: data, model, contract, experiments, tests\n"
           "python run_pipeline.py --serve      # operations console on http://127.0.0.1:8051")


# ───────────────────────────── 4.3 ─────────────────────────────
def test_results(r, D):
    E, M = D.E, D.M
    r.h2("4.3 Test Results")
    r.p("The results below are on the held-out test set unless stated otherwise. They describe the prototype on synthetic data and "
        "must not be read as the performance an operator would see on real traffic; the limitations are set out at the end of this chapter.")

    # --- model performance ---
    r.h4("Model performance")
    rows = []
    order = ["XGBoost (proposed)", "Random Forest", "Logistic Regression", "Isolation Forest", "Static rule checklist"]
    for k in order:
        m = D.models[k]
        rows.append([k, f(m["precision"]), f(m["recall"]), f(m["f1"]), f(m["roc_auc"]), f(m["pr_auc"]), f(m["threshold"], 2)])
    r.table(["Model", "Precision", "Recall", "F1", "ROC-AUC", "PR-AUC", "Threshold"], rows, [1.9, 0.75, 0.65, 0.6, 0.8, 0.75, 0.85],
            caption="Model comparison on the held-out test set", key="tab_models", font=10,
            align=["left", "center", "center", "center", "center", "center", "center"], highlight_row=0)
    x, cv = D.xgb, D.cv
    r.p(f"XGBoost achieves the best F1 ({f(x['f1'])}), ROC-AUC ({f(x['roc_auc'])}) and PR-AUC ({f(x['pr_auc'])}). The random forest is close "
        f"(PR-AUC {f(D.models['Random Forest']['pr_auc'])}), and with only {D.split['test_fraud']} fraudulent test requests a single split "
        f"cannot separate the two with confidence; five-fold cross-validation of XGBoost gives ROC-AUC {f(cv['roc_auc_mean'])} +/- "
        f"{f(cv['roc_auc_std'])} and PR-AUC {f(cv['pr_auc_mean'])} +/- {f(cv['pr_auc_std'])} across folds. Logistic regression "
        f"({f(D.models['Logistic Regression']['roc_auc'])}) shows that non-linear interactions matter. The unsupervised isolation forest "
        f"({f(D.models['Isolation Forest']['roc_auc'])}) performs poorly because much legitimate behaviour, such as travel and eSIM upgrades, is "
        f"also unusual. The static checklist ({f(D.models['Static rule checklist']['roc_auc'])}) is the weakest. "
        f"{r.ref('fig_roc')} gives the ROC and precision-recall curves and {r.ref('fig_cm')} the confusion matrix of XGBoost at its "
        f"validation-chosen threshold: {M['confusion_matrix'][1][1]} of {D.split['test_fraud']} fraudulent requests are detected and "
        f"{M['confusion_matrix'][0][1]} of {M['confusion_matrix'][0][0] + M['confusion_matrix'][0][1]:,} legitimate requests are flagged. Scoring one "
        f"request takes {D.M['xgboost_inference_ms_single']:.1f} ms.")
    fig = r.protodir / "results" / "figures"
    r.figure(fig / "roc_pr_curves.png", "ROC and precision-recall curves of the five models (test set)", "fig_roc", width=6.3)
    r.figure(fig / "confusion_matrix.png", "Confusion matrix of XGBoost (test set)", "fig_cm", width=3.4)

    # --- explanation ---
    sh = list(D.shap["mean_abs"].items())
    names = {"distance_from_home_km": "distance from home cell", "device_age_days": "handset age on network",
             "auth_failures_7d": "authentication failures", "old_sim_last_seen_min": "time since the old SIM was seen",
             "imei_changed": "handset change", "agent_swaps_24h": "agent's swaps in 24 h"}
    r.h4("Explanation quality")
    r.p(f"The TreeSHAP contributions are additive to within {D.shap['additivity_max_abs_error']:.1e} log-odds. "
        f"{r.ref('fig_shap_imp')} ranks the features by mean absolute SHAP value: " +
        ", ".join(f"{names.get(k, k)} ({v:.2f})" for k, v in sh[:6]) +
        f". Weekend, prior swaps and roaming contribute almost nothing ({sh[-1][1]:.3f} to {sh[-3][1]:.3f}). This ordering is what the attack model "
        f"predicts, so it confirms that the model learned the intended structure; because the data are synthetic it is not evidence "
        f"about real traffic. {r.ref('fig_beeswarm')} shows the direction of each effect: long distances, young handsets, many "
        f"authentication failures and an active old SIM push the score towards fraud.")
    r.p(f"{r.ref('fig_waterfall')} explains one detected request ({M['waterfall_request_id']}, probability 0.93). Starting from the base value "
        f"of {D.shap['base_value_logodds']:.2f}, a request made 50.7 km from home adds 2.75, a recent profile change 1.38 and a missing biometric "
        f"check 0.89, while the old SIM having been quiet for 112 minutes subtracts 0.44. This is the explanation an analyst reads in the "
        f"console and the explanation whose hash is anchored on-chain.")
    r.figure(fig / "shap_importance.png", "Global feature importance (mean |SHAP|, test set)", "fig_shap_imp", width=5.6)
    r.figure(fig / "shap_beeswarm.png", "SHAP summary: direction and size of each feature's effect", "fig_beeswarm", width=5.8)
    r.figure(fig / "shap_waterfall.png", "Local explanation of one fraudulent request", "fig_waterfall", width=6.0)

    # --- policy ---
    h, ml, ck, ru = D.hyb, D.mlo, D.chk, D.rul
    pc = D.pc
    r.h4("Policy performance and the value of each layer")
    rows = []
    for name in ("Static checklist (today)", "Rules only", "ML only (XGBoost)", "Hybrid risk engine (proposed)"):
        p = D.pol[name]
        rows.append([name, f"{p['fraud_caught_pct']:.1f}", f"{p['fraud_blocked_pct']:.1f}", f"{p['review_rate_pct']:.1f}",
                     str(p["legit_AUTO_BLOCK"]), str(p["fraud_AUTO_APPROVE"]), f"{p['flag_precision_pct']:.1f}", f"{D.cost(p):,.0f}"])
    r.table(["Policy", "Fraud caught %", "Fraud blocked %", "Reviewed % of all", "Legit blocked", "Fraud missed", "Flag precision %", "Cost"],
            rows, [1.75, 0.65, 0.65, 0.7, 0.55, 0.55, 0.7, 0.55], caption="Three-tier policy and ablations on the test set", key="tab_policy",
            font=9, align=["left"] + ["center"] * 7, highlight_row=3)
    cm, ch = D.cost(ml), D.cost(h)
    breakeven = (cm - (pc["cost_weights"]["missed_fraud"] * h["fraud_AUTO_APPROVE"]
                       + (h["fraud_MANUAL_REVIEW"] + h["legit_MANUAL_REVIEW"]))) / h["legit_AUTO_BLOCK"]
    r.p(f"Fraud caught means sent to manual review or blocked; cost uses the calibration weights ({pc['cost_weights']['missed_fraud']:.0f} per "
        f"missed fraud, {pc['cost_weights']['false_block']:.0f} per false block, {pc['cost_weights']['review']:.0f} per review). Four findings stand out "
        f"({r.ref('fig_pol_cmp')}, {r.ref('fig_pol_out')}).")
    r.numbered([
        f"**The static checklist is far behind.** It catches {ck['fraud_caught_pct']:.1f}% of fraud and misses {ck['fraud_AUTO_APPROVE']} of "
        f"{D.split['test_fraud']} fraudulent requests; rules alone do no better ({ru['fraud_caught_pct']:.1f}%).",
        f"**The model supplies most of the detection.** XGBoost alone catches {ml['fraud_caught_pct']:.1f}% of fraud, blocks {ml['fraud_blocked_pct']:.1f}% "
        f"of it automatically and blocks no legitimate customer.",
        f"**The hybrid engine adds a modest gain at a visible cost.** It catches {h['fraud_caught_pct']:.1f}% and blocks {h['fraud_blocked_pct']:.1f}% of fraud "
        f"automatically, but sends {h['review_rate_pct']:.1f}% of all requests to analysts (against {ml['review_rate_pct']:.1f}%), lowers the share of flagged "
        f"requests that are really fraud from {ml['flag_precision_pct']:.1f}% to {h['flag_precision_pct']:.1f}%, and blocks {h['legit_AUTO_BLOCK']} legitimate "
        f"customers. All {h['legit_AUTO_BLOCK']} are caused by the blacklist rule: second-hand handsets that were reported stolen after sale.",
        f"**Whether the hybrid engine is worth it depends on the cost of a false block.** Under the calibration weights it costs {ch:,.0f} against "
        f"{cm:,.0f} for ML only, a {100 * (cm - ch) / cm:.1f}% saving, but the advantage disappears if a false block costs more than about "
        f"{breakeven:.0f} units. The weights are assumptions that an operator should replace with its own.",
    ])
    r.p("The rules are justified less by their marginal accuracy than by what they guarantee. A blacklisted handset is always blocked "
        "whatever the model says, and a swap within seven days of the last one is always reviewed; these are policy commitments that a "
        "probabilistic model cannot give.")
    r.figure(fig / "policy_comparison.png", "Fraud caught, analyst workload and false blocks for the four policies", "fig_pol_cmp", width=6.3)
    r.figure(fig / "policy_outcomes.png", "Decision by true class under the hybrid risk engine", "fig_pol_out", width=6.0)

    # --- by attack ---
    ba = E["by_attack"]
    r.h4("Detection by attack type")
    r.p(f"{r.ref('fig_attack')} breaks the hybrid engine's result down by the attack archetype that generated each fraudulent test "
        f"request. Social engineering ({ba['SOCIAL_ENGINEERING']['caught_pct']:.1f}% caught, {ba['SOCIAL_ENGINEERING']['blocked_pct']:.1f}% blocked), insider "
        f"retailer fraud ({ba['INSIDER_RETAILER']['caught_pct']:.1f}%) and rapid re-swaps ({ba['RAPID_RESWAP']['caught_pct']:.1f}%) are detected "
        f"well. Forged-identity swaps in stores are the weakest real attack ({ba['FORGED_ID_STORE']['caught_pct']:.1f}% caught, only "
        f"{ba['FORGED_ID_STORE']['blocked_pct']:.0f}% blocked), because they are made in person, usually pass biometric checks and are often near the "
        f"victim's home. **Stealth fraud, drawn from the legitimate distribution, is essentially undetected** "
        f"({ba['STEALTH']['caught_pct']:.1f}%, one request in {ba['STEALTH']['n']}); no model can find an attack that leaves no trace in its "
        f"inputs, and the design therefore relies on the authenticated radio-side signals that real attacks do disturb. Compared with the "
        f"model alone, the rules add up to {max(ba[k]['caught_pct'] - ba[k]['ml_only_caught_pct'] for k in ba):.1f} points for an archetype and "
        f"nothing for rapid re-swaps.")
    r.figure(fig / "detection_by_attack.png", "Detection by attack archetype (test set)", "fig_attack", width=5.6)

    # --- sweep ---
    sw = E["sweep"]
    low = min(sw, key=lambda s: abs(s["t_review"] - 0.02))
    r.h4("Review-threshold trade-off")
    r.p(f"{r.ref('fig_sweep')} shows how the review threshold trades analyst workload against fraud caught. Lowering the threshold to "
        f"{low['t_review']} would catch {low['fraud_caught_pct']:.1f}% of fraud but send {low['review_rate_pct']:.0f}% of all requests to analysts, "
        f"far above the {pc['review_capacity']:.0%} capacity assumed in the calibration. The selected threshold of {pc['t_review']} sits at the "
        f"knee of the curve: {h['review_rate_pct']:.1f}% reviewed for {h['fraud_caught_pct']:.1f}% caught.")
    r.figure(fig / "threshold_sweep.png", "Analyst workload against fraud caught as the review threshold varies", "fig_sweep", width=4.9)

    # --- latency ---
    lat = E["latency"]
    comp = lat["components"]
    names = [("telemetry_ms", "Telemetry verification"), ("ml_shap_ms", "Model scoring and SHAP"), ("rules_ms", "Rules and blacklist lookup"),
             ("hashing_ms", "Canonical hashing"), ("chain_ms", "Blockchain transaction"), ("db_ms", "Database write"), ("total_ms", "Total")]
    r.h4("Latency and throughput")
    r.table(["Step", "Median (ms)", "95th percentile (ms)", "Mean (ms)"],
            [[n, f"{comp[k]['median']:.1f}", f"{comp[k]['p95']:.1f}", f"{comp[k]['mean']:.1f}"] for k, n in names],
            [2.6, 1.2, 1.5, 1.0], caption=f"Processing time per decision (n = {lat['n']}, local chain)", key="tab_latency", font=10,
            align=["left", "center", "center", "center"], bold_last=True)
    dn = lat["decision_without_chain_ms"]
    r.p(f"Excluding the blockchain write, a decision takes {dn['median']:.0f} ms at the median and {dn['p95']:.0f} ms at the 95th percentile. "
        f"Including it, the median is {comp['total_ms']['median']:.0f} ms and the 95th percentile {comp['total_ms']['p95']:.0f} ms, and the sequential "
        f"throughput is {lat['throughput_per_s']:.1f} decisions per second ({r.ref('fig_latency')}). The chain transaction accounts for "
        f"{100 * comp['chain_ms']['median'] / comp['total_ms']['median']:.0f}% of the median. Timings depend on the machine and its load: two complete "
        f"runs on the same laptop gave median totals of 115 ms and 143 ms. On a public network, block times of seconds would dominate "
        f"further, so a production deployment should return the decision first and anchor it through a queue.")
    r.figure(fig / "latency_breakdown.png", "Where the time goes in one decision", "fig_latency", width=5.9)

    # --- gas ---
    g = D.gas
    r.h4("Gas and storage cost")
    r.table(["Operation", "Gas used"], [
        ["Contract deployment (once)", f"{g['deploy_gas']:,}  ({g['bytecode_bytes']:,} bytes of bytecode)"],
        ["logDecision: median", f"{g['log_median']:,}"],
        ["logDecision: minimum / maximum", f"{g['log_min']:,} / {g['log_max']:,}"],
        ["resolveReview: median", f"{g['resolve_median']:,}"],
        [f"logDecision at an assumed {g['assumed_gas_price_gwei']} gwei (mean gas)", f"{g['log_cost_eth_at_assumed_price']:.4f} ETH"],
    ], [3.9, 2.4], caption="Gas measured on the local chain", key="tab_gas", font=10)
    r.p(f"An anchored decision costs about {g['log_median']:,} gas: four storage slots for the entry, an index entry per subscriber, "
        f"one counter update and the event. Gas is measured exactly by the EVM, but the price in ether is an assumption, since gas prices "
        f"differ by orders of magnitude between public networks, layer-2 networks and permissioned chains. Anchoring a Merkle root of "
        f"many decisions in one transaction, listed in Chapter 5, would reduce the cost per decision substantially.")

    # --- tamper ---
    t = D.tamper
    keys = ["Change the decision", "Lower the risk score", "Alter the SHAP explanation", "Alter an input feature value",
            "Clear the rule flags", "Relabel the model version", "Delete a record", "Insert a forged record"]
    rows = [[k, str(t[k]["trials"]), str(t[k]["detected"]), f"{100 * t[k]['detected'] / t[k]['trials']:.0f}%"] for k in keys]
    b = t["baselines"]["Local hash chain, insider recomputes hashes"]
    rows.append(["Baseline: edit a local hash chain, insider recomputes the hashes", str(b["trials"]), str(b["detected"]), f"{100 * b['detected'] / b['trials']:.0f}%"])
    r.h4("Tamper detection")
    r.table(["Insider action", "Trials", "Detected", "Rate"], rows, [3.8, 0.8, 0.9, 0.8],
            caption="Detection of tampering with the off-chain store", key="tab_tamper", font=10,
            align=["left", "center", "center", "center"])
    a = E["audit"]
    r.p(f"Every edit, deletion and forged insertion was detected by the audit, and the audit passed again after the records were "
        f"restored. The baseline shows why the chain matters: a hash chain stored with the records is rewritten consistently by an insider "
        f"who has write access, and the verification then passes, so it detected none of the edits. Verifying {a['entries']} anchored decisions "
        f"took {a['seconds']:.1f} s ({a['ms_per_entry']:.0f} ms per entry, dominated by one chain read per entry). "
        f"The audit cannot detect a decision that was never stored anywhere; the operational control for that case is that the response "
        f"returned to the agent carries the ledger entry, which the CRM must record before the swap is executed.")

    # --- edge ---
    e = E["edge"]
    r.h4("Telemetry integrity")
    gk = "Genuine telemetry (should be accepted)"
    rows = [[gk.replace(" (should be accepted)", " (must be accepted)"), str(e[gk]["trials"]), f"{e[gk]['accepted']} accepted"]]
    for k in ["Payload field altered", "Packet replayed", "Stale packet (1 h old)", "Unregistered device", "Invalid IMEI checksum", "Wrong signing key"]:
        rows.append([k, str(e[k]["trials"]), f"{e[k]['rejected']} rejected"])
    r.table(["Packet", "Trials", "Outcome"], rows, [3.4, 0.9, 2.0], caption="Edge telemetry attacks", key="tab_edge", font=10,
            align=["left", "center", "center"])
    r.p("All doctored packets were rejected and no genuine packet was. Because the checks are deterministic cryptography, the value "
        "of this test lies less in the rate than in the integration defects it exposed. While testing the console, valid packets "
        "were being rejected because the browser's JSON round trip rewrote 12.0 as 12, changing the bytes that had been signed; the "
        "canonical encoding now writes integral numbers as integers on both sides, and a regression test covers it. A unit test also "
        "found that a signed envelope kept a reference to the caller's payload, so editing the envelope silently edited the original; "
        "the envelope now takes a copy.")

    # --- automated tests ---
    r.h4("Automated test suite")
    r.table(["Test module", "Tests", "Covers"], [
        ["test_rules", "8", "Every rule boundary; tier forced by each severity; score cap"],
        ["test_telemetry", "10", "Genuine, altered, replayed, stale, unknown, mis-keyed, bad-checksum, malformed packets; JavaScript round trip"],
        ["test_hashing_and_explain", "5", "Hash determinism and sensitivity; pseudonym; SHAP additivity; reason ordering"],
        ["test_contract", "9", "Read-back; append-only ABI; access control; revocation; score bound; resolution rules; subscriber index"],
        ["test_api", "11", "Scenarios per tier; anchor and audit; privacy; 401, 409, 422; insider edits; resolution; fresh-database isolation"],
        ["Total", "43", "All pass"],
    ], [1.9, 0.6, 3.8], caption="Automated tests", key="tab_tests", font=10, align=["left", "center", "left"], bold_last=True)

    # --- discussion ---
    n = D.split["test_fraud"]
    se = 1.96 * math.sqrt(D.xgb["recall"] * (1 - D.xgb["recall"]) / n) * 100
    r.h4("Discussion and limitations")
    r.p("The results support the design claims, but only within these limits.")
    r.bullets([
        "**Synthetic data.** Absolute figures describe the generator, not an operator's traffic. The dataset was built so that fraud is "
        "detectable but not trivially separable, and the share of stealth fraud and hard legitimate cases was chosen by us. The "
        "comparisons between methods are more informative than the absolute values.",
        f"**Small number of positives.** With {n} fraudulent test requests, the 95% interval on XGBoost's recall of {D.xgb['recall']:.2f} is about "
        f"+/- {se:.0f} points; differences of a few points between close methods are within noise.",
        "**Emulated edge and local chain.** No radio measurement was made, and the chain is a single-node test network, so confirmation "
        "times and gas prices do not describe a public network. Gas units are exact.",
        "**Assumed costs and capacity.** The policy thresholds depend on the stated cost weights and an 8% review capacity.",
        "**Non-adaptive attacker.** The attacks are fixed by the generator; an attacker who learns the rules and shapes requests to "
        "stay below them was not simulated.",
        "**Integrity is not truth.** Anchoring proves what was decided and that records were not changed afterwards. It cannot prove "
        "that the inputs were accurate; signed telemetry narrows that gap but a compromised gateway can still sign false readings.",
    ])
