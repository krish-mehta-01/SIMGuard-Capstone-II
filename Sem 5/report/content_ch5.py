"""Chapters 5 (Future Enhancements) and 6 (Conclusion)."""

from refs import cite


def label_para(r, title, text):
    r.h4(title)
    r.p(text)


def build(r, D):
    r.chapter(5, "Future Enhancements")
    r.p("Although SIMGuard provides a working and measured solution for explainable, tamper-evident SIM replacement decisions, several "
        "enhancements would move it from a prototype towards an operator deployment.")
    label_para(r, "Asynchronous Anchoring with Merkle Batching",
               "Return the decision to the agent immediately and anchor it through a queue. Decisions would be collected for a short "
               "interval and a single Merkle root of their hashes written in one transaction, with an inclusion proof stored beside each "
               "record. This removes the blockchain from the decision's critical path, which Section 4.3 shows dominates latency, and "
               "reduces the gas cost per decision to a small fraction of the current figure.")
    label_para(r, "Public Testnet and Consortium Deployment",
               "Deploy the contract to a public test network such as Sepolia, then to a permissioned or consortium chain in which several "
               "operators, and the regulator, run nodes. A multi-signature owner and several authorised engine keys would remove the "
               "single signing account of the prototype and make an operator's own insiders unable to stop anchoring unnoticed.")
    label_para(r, "Pilot on Real Operator Data",
               "Replace the synthetic dataset with anonymised historical SIM replacement records that carry confirmed fraud labels, "
               "using a time-based split and the operator's own cost of a missed fraud, a false block and a review. This is the only "
               "way to establish real detection performance and to recalibrate the thresholds, and it should be accompanied by drift "
               "monitoring on the feature distributions.")
    label_para(r, "Physical Edge Gateway with a Secure Element",
               "Build the SIM800L and microcontroller gateway described in Chapter 3, measure real signal and cell observations, and "
               "move the device key into a hardware secure element so that it cannot be extracted from a stolen gateway. Remote "
               "attestation would let the engine check the gateway's firmware as well as its packets.")
    label_para(r, "Behavioural and Graph Features",
               "Add signals observed after the swap, such as sudden changes in data usage or the first login from a new device, and "
               "graph features that link agents, handsets, IMEIs and accounts, so that rings of related requests are visible even when "
               "each request looks ordinary. Sequence models could use the customer's history directly.")
    label_para(r, "Analyst Feedback Loop",
               "Use analysts' resolutions, already recorded as separate on-chain entries, as labels for periodic retraining, and use "
               "active learning to route the most informative borderline requests to analysts first.")
    label_para(r, "Adversarial Robustness",
               "Simulate an attacker who learns the rules and the model and shapes requests to stay below the thresholds, then harden the "
               "model with adversarial training and monotonic constraints on signals that should only ever increase risk.")
    label_para(r, "Privacy-Preserving Verification",
               "Allow a regulator to confirm that a decision followed the stated policy without seeing the explanation, using selective "
               "disclosure or zero-knowledge proofs, and rotate the subscriber pseudonym key periodically to limit long-term linkage.")
    label_para(r, "Coverage of eSIM Provisioning and Number Porting",
               "Extend the same decision, explanation and anchoring path to eSIM profile downloads and port-out requests, which are "
               "exploited in the same way as physical SIM replacement.")

    r.chapter(6, "Conclusion")
    h, c, x = D.hyb, D.chk, D.xgb
    tt, td = D.tamper_trials
    r.p("This project has designed, implemented and evaluated SIMGuard, an explainable and tamper-evident decision system for SIM "
        "replacement requests. It makes three contributions: an authenticated edge-telemetry path that lets the engine trust the "
        "radio-side signals an attacker cannot talk its way around; a hybrid risk engine that combines an XGBoost classifier, exact "
        "TreeSHAP explanations, deterministic rules and an IMEI blacklist into a calibrated three-tier decision; and a Solidity audit "
        "contract that anchors fingerprints of both the decision and its explanation while keeping personal data off the chain.")
    r.p(f"On a held-out set of {D.split['test']:,} synthetic requests, XGBoost reached ROC-AUC {x['roc_auc']:.3f} against {D.models['Static rule checklist']['roc_auc']:.3f} "
        f"for a static checklist, and the risk engine sent {h['fraud_caught_pct']:.1f}% of fraudulent requests to review or block against "
        f"{c['fraud_caught_pct']:.1f}%, with {h['review_rate_pct']:.1f}% of requests reviewed by analysts. The audit detected {td} of {tt} tampering "
        f"attempts on the off-chain store, whereas a hash chain that an insider can recompute detected none, and every doctored telemetry "
        f"packet was rejected. A decision is returned in a median of {D.lat['decision_without_chain_ms']['median']:.0f} ms and anchored for about "
        f"{D.gas['log_median']:,} gas. Forty-three automated tests pass.")
    r.p("The results also mark the limits of the approach. The data are synthetic, so the accuracy figures describe the prototype and "
        "not an operator's traffic; fraud that leaves no trace in the inputs cannot be detected; the rules improve recall only modestly "
        "and cost extra reviews and a few false blocks, so their value is mainly the policy guarantees they give; and anchoring proves "
        "what was decided, not that the inputs were true. These limits shape the enhancements proposed in Chapter 5, chiefly a pilot "
        "on real data, a physical edge gateway and asynchronous, batched anchoring.")
    r.p("In conclusion, the project shows that a SIM replacement decision can be made accurate, explained in terms an analyst can act "
        "on, and recorded so that neither the decision nor its reasoning can be quietly rewritten, using commodity hardware and open "
        "software. Treating the explanation as part of the evidence, and anchoring it alongside the decision, is the step that turns an "
        "opaque fraud score into an accountable one.")
