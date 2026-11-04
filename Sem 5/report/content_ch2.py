"""Chapter 2: Overall description (specification, use cases, design, architecture)."""

from refs import cite


def build(r, D):
    r.chapter(2, "Overall Description")
    r.h2("2.1 Project Specification")
    system_study(r, D)
    existing(r, D)
    proposed(r, D)
    requirements(r, D)
    use_case(r, D)
    design(r, D)
    architecture(r, D)


# ───────────────────────────── 2.1.1 ─────────────────────────────
def system_study(r, D):
    r.h3("2.1.1 System Study")
    r.p("The system study examines how a SIM swap is carried out, what an operator can observe while the request is being made, and what "
        "earlier work has already done about it. Its conclusions fix the signals, the decision structure and the integrity requirements "
        "of the design.")
    r.h4("Anatomy of a SIM swap")
    r.numbered([
        "The attacker gathers personal details about the victim (name, date of birth, address, recent transactions) from data leaks, "
        "social media or phishing.",
        "The attacker, or a colluding agent, asks the operator to replace the SIM behind the victim's number: by telephone or chat "
        "posing as the victim, at a retail outlet with forged documents, or through an insider who simply processes the request.",
        "The operator's agent applies a verification step, typically security questions or a document check, and activates the new SIM.",
        "The victim's SIM is deactivated; calls and SMS now reach the attacker's SIM.",
        "The attacker triggers password resets and payment authorisations and reads the OTPs. The victim notices only when the handset "
        "shows no service.",
    ])
    r.p(f"The key observation is that steps 2 and 3 are the only point at which the swap can be stopped cheaply, and they are performed by "
        f"people working through a checklist. Lee et al. showed that the challenges used at that point could be subverted at every "
        f"carrier they tested {cite('lee')}, and the FBI notes that the schemes are growing and recommends that carriers verify customer "
        f"credentials before moving numbers {cite('fbi')}.")
    r.h4("Signals available at the time of the request")
    r.p("Although the attacker can imitate a customer's answers, the request itself leaves traces that the operator already holds. "
        "These fall into three groups that the design uses directly:")
    r.bullets([
        "**Subscriber and account history** (billing and CRM data): account age, current SIM age, number of recent swaps, recent "
        "authentication failures and profile changes.",
        "**Request context**: the channel (store, call centre, online, retailer), the hour and day, whether biometric KYC was "
        "completed, and how many swaps the handling agent has processed in the last day.",
        "**Radio and network observations** (edge gateway and network probes): whether the old SIM is still active on the network, "
        "whether the new handset has ever been seen before, how far the request is from the subscriber's home cell, and recent cell "
        "changes. These are the signals an attacker cannot forge by answering questions, and they are the signals the edge module "
        "authenticates.",
    ])
    r.h4("Related work")
    r.p(f"**SIM swap fraud detection.** Published work on detecting SIM swaps with machine learning is limited. Bhushan et al. propose an "
        f"AI/ML pipeline that processes telecom call records for unusual patterns and sets thresholds for normal behaviour "
        f"{cite('bhushan')}. Sotonye et al. propose combining machine-learning anomaly detection with multi-factor authentication and "
        f"report an 80% reduction in fraudulent attempts {cite('sotonye')}; the published record does not describe the dataset, "
        f"models or evaluation protocol behind that figure, so it cannot be used as a benchmark. Both works treat the output as a "
        f"detection score and do not address how decisions are explained or protected from later alteration.")
    r.p(f"**Gradient boosting and explanation.** Gradient-boosted trees, and XGBoost in particular {cite('chen')}, are a strong default for "
        f"tabular fraud data; random forests {cite('breiman')} and isolation forests {cite('liu')} are common supervised and "
        f"unsupervised baselines. SHAP assigns each feature a Shapley value {cite('shapley')}, the unique attribution satisfying "
        f"local accuracy, missingness and consistency {cite('lundberg17')}, and TreeSHAP computes it exactly for tree ensembles in "
        f"polynomial time {cite('lundberg20')}. These give the per-decision explanations that interpretable-ML research asks for "
        f"{cite('doshi')}.")
    r.p(f"**Blockchain for audit.** Blockchains provide an append-only ledger whose history cannot be rewritten without the agreement of "
        f"the network {cite('nakamoto')}. Ethereum adds programmable contracts that enforce rules on who may append and what may be stored "
        f"{cite('buterin', 'wood')}. Machine-learning fraud detection combined with a blockchain smart contract has been proposed for "
        f"transaction fraud {cite('sensors')}, where a smart contract deploys the model to predict the nature of new transactions.")
    r.table(["Work", "Focus", "Contribution", "Limitation for SIM swap decisions"], [
        [cite("fbi") + " FBI IC3", "Incident statistics", "Counts and losses of reported SIM swaps", "US complaints only; no detection method"],
        [cite("lee") + " Lee et al.", "Carrier authentication", "Showed SIM-change challenges are subvertible", "Measures the weakness; proposes no detector"],
        [cite("bhushan") + " Bhushan et al.", "ML on call records", "AI/ML pipeline with learned thresholds", "No explanation or integrity mechanism"],
        [cite("sotonye") + " Sotonye et al.", "ML + MFA", "Reports an 80% fewer fraud attempts", "Dataset and method not described in the record"],
        [cite("sensors") + " Sensors 2022", "ML + smart contract", "Smart contract deploys the ML model for new transactions", "Transaction fraud; no explanation hash; no risk layer"],
        [cite("lundberg20") + " Lundberg et al.", "Explainable trees", "Exact TreeSHAP for ensembles", "General method; not tied to an audit trail"],
    ], [1.35, 1.2, 1.9, 1.85], caption="Related work and the gap it leaves", key="tab_related", font=10)
    r.p("**Gap.** From the works we could examine (in several cases only their abstracts or published records), no system combines "
        "(i) authenticated radio-side telemetry, (ii) an explainable model, (iii) a deterministic rule layer that can override the model "
        "and produces an actionable three-tier outcome, and (iv) an immutable record of **both the decision and its explanation** for SIM "
        "replacement decisions. This project builds and measures exactly that combination.")


# ───────────────────────────── 2.1.2 ─────────────────────────────
def existing(r, D):
    c = D.chk
    r.h3("2.1.2 Existing System")
    r.p("In current practice a SIM replacement is authorised by a human agent working through a verification script: security questions, "
        "an identity document, sometimes a one-time code sent to the very number being replaced. Fraud teams add static rules after the "
        "fact, such as flags for repeated swaps on one number or for a high-risk region. Where machine learning is used it produces a "
        "score, and the resulting decision is written to the operator's own database or log files.")
    r.p("The disadvantages follow directly from this arrangement:")
    r.bullets([
        "**A single point of failure.** One deceived or complicit agent is enough, and the checklist cannot see whether the old SIM is "
        "still live or the handset has ever been seen on the network.",
        f"**Blunt rules.** The six-signal checklist evaluated in Chapter 4 catches {c['fraud_caught_pct']:.1f}% of fraudulent requests while "
        f"leaving {c['fraud_missed']} of {D.split['test_fraud']} fraudulent test requests approved.",
        "**Opaque scores.** A score without reasons cannot guide an analyst's call to the customer and cannot be explained to a regulator "
        "or an aggrieved customer.",
        "**Mutable evidence.** Logs held by the operator can be altered by anyone with write access, so they cannot settle a dispute "
        "between operator, customer and bank.",
        "**Unauthenticated inputs.** Network and handset data reach the decision logic without proof that they were not altered on the way.",
    ])


# ───────────────────────────── 2.1.3 ─────────────────────────────
def proposed(r, D):
    r.h3("2.1.3 Proposed System")
    r.p("**SIMGuard** treats a SIM replacement request as a decision that must be accurate, explained and permanently attributable. The "
        "work is divided across the three departments so that each layer can be built and validated independently "
        f"({r.ref('fig_modules')}).")
    r.figure(r.figdir / "modules.png", "Division of work across the ECE, CSE and IT modules", "fig_modules", width=6.4)
    r.p("The proposed system has five parts:")
    r.numbered([
        "**Authenticated edge telemetry (ECE).** A gateway built around a SIM800L GSM modem reads the handset IMEI, serving cell and "
        "signal strength through AT commands, adds the network-side observations, and signs the packet with a per-device HMAC-SHA256 key.",
        "**Explainable detection (CSE).** An XGBoost classifier turns the 16-element feature vector into a fraud probability; TreeSHAP "
        "attributes the probability to the features.",
        "**Hybrid risk engine (IT).** Deterministic rules and an IMEI blacklist are combined with the probability under a calibrated "
        "policy to give one of three outcomes: auto-approve, manual review or auto-block. Critical rules override the model.",
        "**Tamper-evident anchoring (IT).** The decision record and the SHAP explanation are canonicalised and hashed with SHA-256; the "
        "hashes, a pseudonymous subscriber reference, the tier and the risk score are appended to a Solidity smart contract. The full "
        "record stays off-chain.",
        "**Verification and operations (IT).** An audit recomputes the hashes of every stored record and compares them with the chain; a "
        "REST API and an operations console serve analysts, administrators and auditors.",
    ])
    r.table(["Aspect", "Current practice", "ML-only detectors (literature)", "SIMGuard"], [
        ["Decision basis", "Agent judgement and checklist", "Model score", "Model + deterministic rules + blacklist"],
        ["Output", "Approve or reject", "Fraud / not fraud", "Auto-approve, manual review or auto-block"],
        ["Explanation", "Agent's note", "Usually none", "TreeSHAP reasons for every decision"],
        ["Audit record", "Operator database", "Operator database", "Hashes of decision and explanation on a smart contract"],
        ["Insider edits", "Undetectable", "Undetectable", "Detected by the audit"],
        ["Input integrity", "None", "None", "HMAC-signed, fresh, single-use telemetry"],
        ["Privacy of the record", "Full data in the operator's system", "As current practice", "Pseudonymous reference; no personal data on-chain"],
    ], [1.2, 1.5, 1.6, 2.0], caption="Existing practice compared with the proposed system", key="tab_compare", font=10)


# ───────────────────────────── 2.1.4 ─────────────────────────────
def requirements(r, D):
    lat, g = D.lat, D.gas
    r.h4("Functional and non-functional requirements")
    r.table(["ID", "Functional requirement", "Verified by"], [
        ["FR1", "Accept a SIM replacement request with signed edge telemetry and return a decision with reasons.", "API tests, system test"],
        ["FR2", "Reject telemetry that is altered, replayed, stale, from an unknown device or implausible.", "Telemetry tests, edge experiment"],
        ["FR3", "Score each request with the trained model and compute exact SHAP contributions.", "Explanation tests (additivity)"],
        ["FR4", "Apply deterministic rules and the IMEI blacklist; critical rules force auto-block, high rules force at least review.", "Rule tests"],
        ["FR5", "Return one of three tiers using thresholds calibrated on validation data.", "Policy experiment"],
        ["FR6", "Anchor hashes of the decision and explanation on the smart contract; store no personal data on-chain.", "Contract and API tests"],
        ["FR7", "Let an analyst resolve a manual review; record the outcome on-chain as a separate, append-only entry.", "Contract and API tests"],
        ["FR8", "Verify every stored record against the chain and report any mismatch, deletion or unanchored record.", "Tamper experiment"],
        ["FR9", "Provide an operations console showing request, decision, explanation, anchor and audit results.", "Console screenshots"],
    ], [0.55, 4.25, 1.5], caption="Functional requirements", key="tab_fr", font=10)
    r.table(["ID", "Non-functional requirement", "Target", "Measured"], [
        ["NFR1", "Decision latency excluding the blockchain write", "< 100 ms median", f"{lat['decision_without_chain_ms']['median']:.0f} ms median, {lat['decision_without_chain_ms']['p95']:.0f} ms p95"],
        ["NFR2", "End-to-end latency including the chain write (local chain)", "< 1 s median", f"{lat['components']['total_ms']['median']:.0f} ms median, {lat['components']['total_ms']['p95']:.0f} ms p95"],
        ["NFR3", "Detection of tampering with off-chain records", "100%", f"{D.tamper_trials[1]} of {D.tamper_trials[0]} trials"],
        ["NFR4", "Rejection of doctored telemetry", "100%, no false rejections", "100% rejected; 100 of 100 genuine accepted"],
        ["NFR5", "Gas to anchor one decision", "< 250,000", f"{g['log_median']:,} median"],
        ["NFR6", "Privacy: no MSISDN or IMEI on-chain", "None stored", "Pseudonymous reference only (test)"],
        ["NFR7", "Reproducibility", "Fixed seeds, scripted pipeline", "One command reproduces all results"],
        ["NFR8", "Consistency of the online and offline decision paths", "Identical", f"{D.E['consistency']['online_offline_mismatches']} mismatches in {D.E['consistency']['n']}"],
    ], [0.55, 2.7, 1.3, 1.75], caption="Non-functional requirements and measured values", key="tab_nfr", font=10)


# ───────────────────────────── 2.2 ─────────────────────────────
def use_case(r, D):
    r.h2("2.2 Use Case Diagram")
    r.p(f"{r.ref('fig_usecase')} shows how the actors interact with the system. The retail agent or call-centre staff member submits "
        "the request; the edge gateway supplies the signed telemetry that accompanies it; the risk engine evaluates, explains and anchors "
        "the decision; the fraud analyst resolves requests routed to manual review; the network administrator configures thresholds and "
        "monitors the engine; and the auditor or regulator independently verifies the audit trail.")
    r.figure(r.figdir / "use_case.png", "Use case diagram", "fig_usecase", width=5.8)
    r.table(["Actor", "Responsibility", "Main use cases"], [
        ["Retail agent / call-centre staff", "Initiates a SIM replacement on behalf of a customer", "Submit request; receive decision and reasons"],
        ["Edge gateway", "Reads handset and radio parameters; signs the packet", "Sign and forward telemetry"],
        ["Fraud analyst", "Handles requests the engine routes to review", "Resolve manual review (decision, justification)"],
        ["Network administrator", "Operates the engine and the blacklist", "Monitor decisions; manage thresholds and keys"],
        ["Auditor / regulator", "Checks that decisions were not altered", "Verify audit trail; inspect ledger"],
    ], [1.7, 2.5, 2.1], caption="Actors and their responsibilities", key="tab_actors", font=10)
    r.p(f"The data flow is shown in {r.ref('fig_dfd')}. Telemetry and request fields enter the engine (P1, P2); the model returns a "
        f"probability and SHAP vector (P3); rules and the blacklist produce the decision (P4); the decision is hashed, anchored and stored "
        f"(P5) and returned to the agent with its reasons; review outcomes and audit reads (P6) use the stored records and the ledger.")
    r.figure(r.figdir / "dfd.png", "Data flow diagram", "fig_dfd", width=6.4)


# ───────────────────────────── 2.3 ─────────────────────────────
def design(r, D):
    r.h2("2.3 Design")
    r.p("SIMGuard follows a layered, modular design so that each concern (acquisition, scoring, governance, integrity, presentation) can "
        "be developed, tested and replaced independently. Four principles guided the decisions below.")
    r.bullets([
        "**Never trust a single component for integrity.** The model can be wrong, the database can be edited and the network can be "
        "tampered with, so each is checked by a mechanism that does not depend on it: rules for the model, the chain for the database, "
        "signatures for the network.",
        "**Explain every decision.** An explanation is produced and recorded for each request, not only for those that are challenged.",
        "**Keep personal data off the chain.** The chain stores pseudonyms and hashes. Data that must be erasable stays in an operator "
        "database that can be erased.",
        "**Make measurements reproducible.** Every threshold is chosen on validation data, every random process is seeded and every "
        "reported number is generated by a script.",
    ])
    dataset(r, D)
    model(r, D)
    explanation(r, D)
    policy(r, D)
    chain(r, D)
    telemetry(r, D)
    data_design(r, D)


def dataset(r, D):
    ds = D.ds_attack
    r.h4("Dataset design")
    r.p(f"Real SIM-swap records are confidential under telecom licence conditions and under data-protection law {cite('dpdp')}, so the "
        f"prototype is trained and evaluated on a synthetic dataset generated from an explicit attack model. The generator is designed to "
        f"avoid the most common flaw of synthetic fraud data, in which fraud and legitimate records occupy disjoint regions so that any "
        f"model scores near-perfectly. Three measures prevent this. Legitimate and fraudulent requests share the same base distributions "
        f"and fraud only shifts the probability of particular signals. Legitimate **hard cases** exist: customers who upgrade to an "
        f"eSIM keep the old SIM live, travellers request swaps far from home, and one request in eight is made at an unusual hour. And a "
        f"fraction of fraud, about 6%, is drawn from the legitimate distribution, so it is **undetectable from these features by design**.")
    r.p(f"The dataset contains {D.ds_n:,} requests of which {D.ds_fraud:,} ({D.ds_fraud / D.ds_n:.0%}) are fraudulent, a rate chosen to make "
        f"class imbalance realistic. {D.ds_black['fraud']} fraudulent and {D.ds_black['legit']} legitimate requests target a blacklisted handset, "
        f"the latter representing second-hand devices that were reported stolen after sale. Each row carries a 16-element feature vector "
        f"({r.ref('tab_features')}) plus identifiers that are used only by the engine, never by the model.")
    r.table(["Feature", "Meaning", "Source"], [
        ["account_age_days", "Age of the subscriber account", "BSS"],
        ["sim_age_days", "Age of the SIM currently in service", "BSS"],
        ["swaps_last_180d", "SIM replacements in the previous 180 days", "BSS"],
        ["hour_of_request", "Hour of day of the request (0-23)", "BSS"],
        ["is_weekend", "Request made on a weekend", "BSS"],
        ["channel_code", "Store, call centre, online or retailer", "BSS"],
        ["kyc_biometric_verified", "Biometric KYC completed for this request", "BSS"],
        ["auth_failures_7d", "Failed authentication attempts in 7 days", "BSS"],
        ["profile_change_7d", "Profile details changed in the last 7 days", "BSS"],
        ["agent_swaps_24h", "Swaps processed by the handling agent in 24 hours", "BSS"],
        ["imei_changed", "New handset differs from the previous one", "Edge (signed)"],
        ["device_age_days", "Days the new handset has been on the network (0 = never seen)", "Edge (signed)"],
        ["old_sim_last_seen_min", "Minutes since the old SIM was last active", "Edge (signed)"],
        ["distance_from_home_km", "Distance between request location and home cell", "Edge (signed)"],
        ["cell_changes_24h", "Serving-cell changes in the last 24 hours", "Edge (signed)"],
        ["roaming_flag", "Subscriber is roaming", "Edge (signed)"],
    ], [1.9, 3.35, 1.05], caption="The 16 model features and where they come from", key="tab_features", font=10)
    r.p(f"Fraud is generated from four archetypes drawn from the attack routes in Section 2.1.1 ({r.ref('tab_attacks')}). Each starts from "
        f"legitimate behaviour and then shifts the signals that attack characteristically changes.")
    r.table(["Archetype", "Mechanism", "Signals shifted", "Test requests"], [
        ["Social engineering", "Remote support is deceived into swapping", "Call-centre or online channel, no biometric KYC, auth failures, profile change", str(D.E["by_attack"]["SOCIAL_ENGINEERING"]["n"])],
        ["Insider (retailer)", "A colluding retailer processes many swaps", "Retailer channel, agent swaps in 24 h far above normal, evening hours", str(D.E["by_attack"]["INSIDER_RETAILER"]["n"])],
        ["Forged ID (store)", "Forged documents presented in a store", "Store channel, large distance from home, profile change", str(D.E["by_attack"]["FORGED_ID_STORE"]["n"])],
        ["Rapid re-swap", "A compromised number is swapped again", "SIM age under 3 weeks, repeated swaps", str(D.E["by_attack"]["RAPID_RESWAP"]["n"])],
        ["Stealth", "Indistinguishable from a genuine request", "None (drawn from the legitimate distribution)", str(D.E["by_attack"]["STEALTH"]["n"])],
    ], [1.3, 1.75, 2.55, 0.7], caption="Fraud archetypes in the synthetic dataset", key="tab_attacks", font=10, align=["left", "left", "left", "center"])
    r.p("All archetypes share two traits that reflect how attacks actually run: the victim's old SIM is usually still active when the "
        "request is made, and the attacker usually presents a handset that has not been seen on the network before. Both are visible only "
        "to the radio-side telemetry, which is why that data is authenticated.")


def model(r, D):
    m = D.META
    r.h4("Model design")
    r.p(f"The data are split once, stratified by class and seeded, into training ({D.split['train']:,} requests), validation ({D.split['val']:,}) "
        f"and test ({D.split['test']:,}) sets, each containing the same fraud rate. The test set is used only for the final report. "
        f"Every decision threshold in the system, including each baseline's operating point and the risk-engine thresholds, is chosen on the "
        f"validation set. Because fraud is {D.ds_fraud / D.ds_n:.0%} of requests, the precision-recall curve is reported alongside ROC, "
        f"which can look optimistic under imbalance {cite('saito')}.")
    r.p(f"The proposed classifier is XGBoost {cite('chen')} with {m['hyperparameters']['max_depth']}-level trees, learning rate "
        f"{m['hyperparameters']['learning_rate']}, row and column subsampling of {m['hyperparameters']['subsample']} and a minimum child weight of "
        f"{m['hyperparameters']['min_child_weight']}. Training stops early when validation precision-recall AUC no longer improves for 50 rounds, which "
        f"selected {m['n_trees']} trees. Four baselines are trained on the same split: the static six-signal checklist used by "
        f"verification desks, logistic regression on standardised features, a random forest {cite('breiman')} and an isolation forest "
        f"{cite('liu')} as an unsupervised detector.")


def explanation(r, D):
    r.h4("Explanation design")
    r.p(f"For every request, TreeSHAP {cite('lundberg20')} computes one contribution per feature, expressed in log-odds so that the base value "
        f"plus the sum of the contributions equals the model's raw output exactly. XGBoost computes these values natively. The prototype "
        f"verifies the identity on the held-out set: the largest absolute discrepancy is {D.shap['additivity_max_abs_error']:.1e}, which is float "
        f"rounding. The base value is {D.shap['base_value_logodds']:.2f} log-odds, corresponding to the 5% prevalence.")
    r.p("The numeric vector is turned into reasons an analyst can read. The eight contributions largest in magnitude are kept, and each "
        "is paired with a sentence describing the feature value, for example “Request made 94 km from the home cell (+3.38)” or "
        "“Biometric KYC not completed (+0.80)”. A summary sentence assembles the leading four reasons and any rules that fired. The "
        "numeric vector and the feature values it explains are what is hashed on-chain, so the readable text can always be regenerated "
        "and checked.")


def policy(r, D):
    pc = D.pc
    r.h4("Risk engine and policy design")
    r.p("The probability alone is not an operational decision. The risk engine adds deterministic rules, each with a severity that fixes "
        f"its effect ({r.ref('tab_rules')}). A CRITICAL rule forces auto-block whatever the model says; a HIGH rule forces at least "
        "manual review; each MEDIUM rule adds 0.10 to the risk score.")
    r.table(["Rule", "Severity", "Condition", "Rationale"], [
        ["IMEI_BLACKLISTED", "CRITICAL", "New handset is on the stolen / blocked register", "A reported device must never receive a swapped number"],
        ["SWAP_COOLDOWN", "HIGH", "Current SIM issued less than 7 days ago", "Back-to-back swaps are a hallmark of a compromised number"],
        ["AGENT_VELOCITY", "HIGH", "Agent processed 12 or more swaps in 24 hours", "Insider collusion processes unusual volume"],
        ["ACTIVE_SIM_REMOTE_REQUEST", "HIGH", "Old SIM active in the last 15 min and request more than 50 km from home", "A live SIM and a distant request cannot both be the owner"],
        ["WEAK_KYC_REMOTE_CHANNEL", "MEDIUM", "Call-centre or online request without biometric KYC", "The channel most exposed to social engineering"],
        ["AUTH_FAILURE_SPIKE", "MEDIUM", "5 or more failed authentications in 7 days", "Credential guessing before the request"],
    ], [1.75, 0.85, 2.05, 1.65], caption="Deterministic security rules", key="tab_rules", font=10)
    r.p(f"The risk score is min(1, p + 0.10 x m), where p is the model probability and m the number of MEDIUM rules that fired. "
        f"{r.ref('fig_policy')} gives the decision logic. A request is auto-blocked if any CRITICAL rule fired or the risk reaches the block "
        f"threshold; otherwise it goes to manual review if any HIGH rule fired or the risk reaches the review threshold; otherwise it is "
        f"auto-approved.")
    r.figure(r.figdir / "policy_flow.png", "Three-tier decision logic of the risk engine", "fig_policy", width=5.0)
    r.p(f"The two thresholds are not guessed. They are chosen on the validation set by minimising an explicit operating cost: "
        f"{pc['cost_weights']['missed_fraud']:.0f} for each fraudulent request that is auto-approved, {pc['cost_weights']['false_block']:.0f} for each "
        f"legitimate customer auto-blocked, and {pc['cost_weights']['review']:.0f} for each manual review, subject to a capacity limit that analysts can "
        f"review at most {pc['review_capacity']:.0%} of requests. A grid search over both thresholds selected a review threshold of {pc['t_review']} and a "
        f"block threshold of {pc['t_block']}. The cost weights are assumptions that an operator should replace with its own figures; the method "
        f"stays the same.")


def chain(r, D):
    r.h4("Blockchain design")
    r.p("The design question is what to put on-chain. Storing whole records would expose personal data and cost far more gas; storing "
        "nothing would leave the audit trail mutable. SIMGuard stores **fingerprints**: the chain holds SHA-256 hashes "
        f"{cite('fips')} of the decision record and of the SHAP explanation, together with the tier, the risk score in basis points, a "
        f"timestamp, and a pseudonymous subscriber reference. The full record and the readable explanation stay in the operator's database. "
        f"At audit time the hashes are recomputed from the stored records and compared with the chain ({r.ref('fig_anchor')}); any "
        f"difference proves that the stored record changed after the decision.")
    r.figure(r.figdir / "anchoring.png", "What is hashed, what is anchored, and how the audit compares them", "fig_anchor", width=6.4)
    r.p("Three details make the fingerprints reliable. **Canonical encoding:** records are serialised as JSON with sorted keys, no "
        "whitespace and fixed rounding, so the same record always yields the same hash. **Explanation coverage:** the SHAP hash covers "
        "the numeric contributions and the feature values they explain, so neither can be edited independently. **Pseudonymisation:** "
        "the subscriber reference is an HMAC-SHA256 of the mobile number under an operator-held key "
        f"{cite('hmac')}, so the number cannot be recovered from the chain and the references of one subscriber remain linkable only by "
        "the key holder.")
    r.p(f"The contract, **SIMSwapAuditLog**, is written in Solidity {cite('solidity')} and compiled with solc 0.8.24. Its interface is "
        f"summarised in {r.ref('tab_contract')}. It has no function that updates or deletes an entry; a manual-review outcome is recorded as "
        f"a separate resolution and the original entry is never touched. Only addresses authorised by the owner may append, which "
        f"prevents outsiders from filling the ledger with false entries. Counters per tier are maintained on write, so reading the "
        f"statistics costs constant time, unlike a loop over all entries.")
    r.table(["Function", "Access", "Purpose"], [
        ["logDecision(ref, tier, riskBps, decisionHash, shapHash)", "Authorised engine", "Append an audit entry; emits DecisionLogged"],
        ["resolveReview(entryId, finalTier, analystRef, noteHash)", "Authorised engine", "Record the analyst's outcome for a MANUAL_REVIEW entry, once"],
        ["getEntry(id), getResolution(id)", "Public (view)", "Read an entry or its resolution"],
        ["verifyEntry(id, decisionHash, shapHash)", "Public (view)", "Compare supplied hashes with the anchored ones"],
        ["getSubscriberEntries(ref), getStats()", "Public (view)", "Entries of one pseudonym; counts per tier"],
        ["authorizeEngine, revokeEngine, transferOwnership", "Owner only", "Manage which addresses may write"],
    ], [2.85, 1.2, 2.25], caption="Smart contract interface", key="tab_contract", font=10)


def telemetry(r, D):
    r.h4("Edge telemetry design")
    r.p(f"The edge gateway is built around a SIM800L GSM modem controlled with AT commands {cite('sim800')}. It reads the handset IMEI "
        f"(AT+GSN), the signal quality (AT+CSQ), the registration status (AT+CREG?) and the serving cell (AT+CENG?). Observations that a modem "
        f"cannot produce alone, such as how long ago the old SIM was last active, come from a network probe and are added by the gateway. "
        f"The resulting payload is signed with HMAC-SHA256 {cite('hmac')} using a key held only by that device, over a canonical encoding "
        f"that is independent of programming language.")
    r.p("The engine accepts a packet only if every check in the following table passes. The checks are cheap, so they run before any model "
        "inference.")
    r.table(["Check", "Attack it stops", "Implementation"], [
        ["Registered device and valid HMAC-SHA256", "Forged or altered payload; unknown device", "Per-device key; constant-time comparison over the canonical packet"],
        ["Freshness window", "Stale captured packet", "Timestamp within 120 s of the engine clock"],
        ["Single-use nonce", "Replay of a valid packet", "Nonce stored after processing; second use rejected"],
        ["IMEI checksum", "Corrupted or invented handset identity", "Luhn check digit of the IMEI (3GPP TS 23.003 numbering)"],
        ["Plausibility", "Out-of-range readings", "RSSI between -120 and -30 dBm; counters not negative"],
    ], [1.9, 1.9, 2.5], caption="Telemetry integrity checks", key="tab_telemetry", font=10)
    r.p("The engine overrides any handset or radio value stated by the caller with the signed values, so a compromised front-end cannot "
        "feed the model false radio observations without breaking the signature.")


def data_design(r, D):
    r.h4("Data design")
    r.p(f"The operator database is SQLite. The **decisions** table holds one row per request: a pseudonymous subscriber reference, a masked "
        f"number, the channel, a hashed agent reference, the tier, risk and probability, the rules that fired, the feature vector, the "
        f"SHAP contributions, the readable reasons, both hashes, the transaction hash, block and gas, the latency breakdown and, "
        f"when applicable, the analyst's resolution. The **imei_blacklist** table holds the stolen-device register and **used_nonces** "
        f"holds the nonces of processed telemetry packets. {r.ref('fig_er')} shows the tables and how a row corresponds to exactly one "
        f"on-chain entry.")
    r.figure(r.figdir / "er_diagram.png", "Entity-relationship diagram of the off-chain store and the on-chain structures", "fig_er", width=6.3)


# ───────────────────────────── 2.4 ─────────────────────────────
def architecture(r, D):
    r.h2("2.4 System Architecture")
    r.p(f"{r.ref('fig_arch')} shows the layers of SIMGuard. Signed packets flow from the edge layer into the risk engine, which is the "
        f"only component that talks to the model, the database and the blockchain. The presentation layer reaches the engine only through "
        f"its REST API.")
    r.figure(r.figdir / "architecture.png", "System architecture of SIMGuard", "fig_arch", width=6.4)
    r.lead("**Edge layer (ECE).** The handset and SIM slot, the SIM800L modem and a microcontroller that signs the packet. It is the "
           "only source of radio-side observations and the only holder of the device keys.")
    r.lead("**Risk engine (IT).** Eight modules run in sequence: telemetry verification, feature construction, model and SHAP scoring, "
           "rules and policy, canonical hashing and record storage, the anchoring client, audit and the REST interface. The CSE model is "
           "loaded once and scores a request in a few milliseconds.")
    r.lead("**Blockchain layer.** An Ethereum node hosting the audit contract. The prototype uses a local Ganache node; replacing it with a "
           "public testnet or a permissioned network changes only the node address and the signing account.")
    r.lead("**Data layer.** SQLite for decision records, the IMEI blacklist and the used nonces.")
    r.lead("**Presentation layer.** The operations console for analysts, administrators and auditors.")
    r.p(f"{r.ref('fig_seq')} follows one request through the system, including the review path. Steps 4 to 10 take place in memory and "
        f"complete within a few milliseconds; step 11, the blockchain transaction, is the slowest step and dominates the end-to-end time "
        f"(Section 4.3).")
    r.figure(r.figdir / "sequence.png", "Sequence of one SIM replacement evaluation, including manual review", "fig_seq", width=6.4)
    r.p(f"**Threat model.** {r.ref('tab_threats')} lists the threats considered, the control that addresses each and the risk that remains. "
        f"Stating the residual risk is as important as the control: anchoring proves what was decided, not that the inputs were true.")
    r.table(["Threat", "Control", "Residual risk"], [
        ["Agent deceived by social engineering", "Model, rules and manual-review tier reduce reliance on the agent", "Stealth fraud that looks genuine is not detected"],
        ["Insider edits or deletes a stored decision", "Hash anchoring and audit expose any change to a record", "An engine that never anchors a decision at all must be caught by the missing-anchor check"],
        ["Telemetry altered in transit", "HMAC over canonical packet", "Compromise of the gateway itself"],
        ["Captured packet replayed or delayed", "Single-use nonce and 120 s freshness window", "None beyond clock accuracy"],
        ["Device key stolen", "Per-device keys limit the damage to one gateway", "A stolen key can forge telemetry until revoked; a secure element would help"],
        ["Engine signing key stolen", "Owner can revoke an engine address", "Single signing account in the prototype; multi-signature advisable"],
        ["Attacker mimics legitimate behaviour", "Rules do not depend on the model; critical rules always block", "Cannot be excluded; recall on stealth fraud is low"],
        ["Personal data exposed through the chain", "Pseudonymous reference, hashes only, nothing else on-chain", "Linkage by the key holder; hashes of records with personal data"],
        ["Chain unavailable", "Decision is computed before anchoring", "Prototype anchors synchronously, so the request fails; a retry queue is future work"],
    ], [1.9, 2.35, 2.05], caption="Threat model", key="tab_threats", font=10)
