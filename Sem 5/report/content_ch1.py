"""Chapter 1: Introduction."""

from refs import cite


def build(r, D):
    c = D.chk
    r.chapter(1, "Introduction")
    r.p("The mobile phone number has quietly become the root of a person's digital identity. It is the address to which banks send "
        "transaction alerts, the channel through which one-time passwords (OTPs) are delivered for payments and logins, and the "
        "recovery route for e-mail, messaging and crypto-asset accounts. Whoever controls the number can therefore, in practice, "
        "become the account holder.")
    r.p("A **SIM swap** is the fraudulent transfer of a subscriber's number to a new Subscriber Identity Module (SIM) held by an attacker. "
        "Three routes dominate: social engineering of a call-centre or online-support agent, collusion with an insider at an operator "
        "or retailer, and forged identity documents presented at a store. Once the swap succeeds, calls and text messages reach the "
        "attacker, the victim's handset loses service, and every account protected only by an SMS code is exposed, usually within "
        "minutes and before the victim understands why the signal has gone.")
    r.p(f"The scale is documented even though consolidated statistics are scarce. The FBI's Internet Crime Complaint Center received 320 SIM "
        f"swapping complaints with adjusted losses of about $12 million between January 2018 and December 2020, and 1,611 complaints with "
        f"adjusted losses above $68 million in 2021 alone {cite('fbi')}. These are United States complaints only and understate the problem, "
        f"because many victims never report. An empirical study of the authentication used for SIM changes at five prepaid carriers found "
        f"that every one of them relied on challenges an attacker could subvert {cite('lee')}.")
    r.p(f"The defences in use are weak in a specific way. Manual verification places a single human in the path of every request, so one "
        f"deceived or complicit agent defeats it. Static checklists are cheap but blunt: in the evaluation reported in Chapter 4, a "
        f"six-signal checklist of the kind a verification desk applies catches only {c['fraud_caught_pct']:.1f}% of fraudulent requests. "
        f"Machine-learning detectors catch more, but they reduce a request to a score, give an analyst no reason to trust or overrule it, and "
        f"write the outcome to a database that insiders with write access can later alter. The same people who can collude in a swap can "
        f"quietly edit the record of it.")
    r.p("This project addresses the whole chain rather than one link. **SIMGuard** is a multidisciplinary framework in which the Electronics "
        "and Communication (ECE) module produces authenticated handset and radio telemetry at the edge, the Computer Science (CSE) module "
        "scores each SIM replacement request with an explainable model, and the Information Technology (IT) module turns the score into a "
        "three-tier decision (auto-approve, manual review or auto-block), explains it in plain language, and anchors a cryptographic "
        "fingerprint of both the decision and its explanation in an Ethereum smart contract so that neither can be changed afterwards "
        "without detection.")
    r.p("This report documents the design, implementation and measured behaviour of the prototype. Real SIM-swap records are confidential, so "
        "the model is trained on a synthetic dataset; the edge gateway is a software emulation of a SIM800L modem; and the blockchain is a "
        "local Ethereum node. Each result in Chapter 4 is stated together with what it does and does not demonstrate.")

    r.h2("1.1 Problem Statement")
    r.p("Telecommunication operators cannot currently verify, quickly and defensibly, that a request to replace the SIM behind a phone number "
        "comes from the genuine subscriber. The problem has four connected parts.")
    r.p("**First, the detection problem.** Fraudulent requests look like legitimate ones in most respects. They differ in subtle, combined "
        "signals: the old SIM is still active on the network, the new handset has never been seen before, the request comes from a remote "
        "channel without biometric verification, or one retail agent is suddenly processing far more swaps than usual. No single signal is "
        "decisive, and a rule written for one signal produces either missed fraud or customer friction.")
    r.p("**Second, the decision problem.** A binary fraud flag is not an operational outcome. An operator must be able to approve routine "
        "requests without friction, escalate ambiguous ones to a human analyst within a finite review capacity, and stop clear attacks "
        "automatically. Some conditions, such as a handset on the stolen-device register, must override any model output.")
    r.p(f"**Third, the explanation problem.** An analyst who is told only that a request scored 0.87 cannot decide whether to call the "
        f"customer, and an operator who blocks a customer must be able to say why. Data-protection law is moving in the same direction: "
        f"the EU General Data Protection Regulation restricts decisions based solely on automated processing and requires safeguards "
        f"around them {cite('gdpr')}, and India's Digital Personal Data Protection Act, 2023 obliges data fiduciaries to protect personal "
        f"data with reasonable security safeguards {cite('dpdp')}. Explanations are most useful when they are generated for every "
        f"decision, in terms an analyst can read.")
    r.p("**Fourth, the integrity problem.** Decision logs held in the operator's own database are only as trustworthy as everyone who can "
        "write to that database. An insider who helped an attacker can delete the record, flip a blocked decision to approved, or rewrite "
        "the explanation to hide the signals that should have raised an alarm. Hash chains stored in the same system do not help, because "
        "the insider can recompute every hash after the edit. Integrity needs an anchor that the operator cannot rewrite.")

    r.h2("1.2 Project Scope and Objectives")
    r.h3("1.2.1 Project Scope")
    r.p("The project covers the design, implementation and evaluation of an end-to-end prototype for SIM replacement decisions: the "
        "acquisition and authentication of edge telemetry; feature construction; model training with baselines; explanation of every "
        "decision; the rule-and-policy layer that produces the three-tier outcome; the smart contract and the client that anchors "
        "decisions; the off-chain store; an audit procedure that verifies stored records against the chain; a REST interface; and an "
        "operations console for analysts and auditors.")
    r.p("The scope is deliberately bounded. The dataset is synthetic and generated from an explicit attack model, so absolute accuracy "
        "figures describe the prototype and not a live operator's traffic. The edge gateway is emulated in software with the same "
        "AT-command dialogue, signing and verification code that a hardware gateway would run; no physical radio measurements are "
        "reported. The blockchain is a local Ganache chain, so gas figures are measured but confirmation times are not representative of a "
        "public network. Integration with a real operator's billing, CRM or SIM-provisioning systems is outside the scope.")
    r.h3("1.2.2 Project Objectives")
    r.p("The primary objective is to build and evaluate a decentralised-audit, explainable decision system for SIM replacement requests. "
        "The specific objectives are:")
    r.numbered([
        "**Realistic synthetic data.** To generate a labelled dataset of SIM replacement requests from an explicit attack model with four "
        "attack archetypes, legitimate hard cases such as eSIM upgrades and travellers, and a share of fraud that is undetectable from the "
        "available signals, so that results are not inflated by trivially separable classes.",
        "**Authenticated edge telemetry.** To define and verify a signed packet format for handset and radio parameters that rejects "
        "altered, replayed, stale, mis-keyed and implausible packets.",
        "**Accurate, calibrated detection.** To train an XGBoost classifier and compare it with a static checklist, logistic regression, a "
        "random forest and an isolation forest on a strictly held-out test set, with every threshold chosen on a separate validation set.",
        "**Explanation of every decision.** To compute exact TreeSHAP contributions for each request and render the leading ones as "
        "plain-language reasons.",
        "**Hybrid, governed decisions.** To combine the model probability with deterministic rules and an IMEI blacklist into three tiers, "
        "calibrating the review and block thresholds against an explicit cost and analyst-capacity model.",
        "**Tamper-evident anchoring with privacy.** To implement a Solidity contract that records a pseudonymous subscriber reference, the "
        "tier, the risk score, and SHA-256 hashes of the decision record and its SHAP explanation, with no personal data on-chain and no "
        "function that can modify or delete an entry.",
        "**Verifiable audit.** To provide an audit that recomputes every stored record's hashes and compares them with the chain, and to "
        "measure how reliably it detects edits, deletions and forged insertions compared with a hash chain an insider can recompute.",
        "**Operability and evidence.** To expose the system through a REST API and an operations console, to measure latency, throughput "
        "and gas, and to back the implementation with automated tests.",
    ])
