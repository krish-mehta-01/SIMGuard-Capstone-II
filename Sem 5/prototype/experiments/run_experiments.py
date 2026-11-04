"""
Experiments for the capstone report. Every number in the Testing / Results chapter comes from this script.

  E1  Three-tier policy on the held-out test split, with ablations
  E2  Detection by attack archetype
  E3  Review-threshold sweep (analyst workload vs fraud caught)
  E4  End-to-end latency, gas and throughput on a real (Ganache) chain
  E5  Online/offline consistency (API path vs vectorised evaluation)
  E6  Tamper detection: anchored on-chain vs hash chains an insider can recompute
  E7  Edge telemetry integrity attacks
  E8  Audit scalability

Run:  python experiments/run_experiments.py      (needs the local chain: npm run chain)
"""

import copy
import hashlib
import json
import random
import statistics as st
import sys
import tempfile
import time
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from blockchain.chain import AuditChain, canonical_json, compute_hashes  # noqa: E402
from config import FEATURE_COLS, FIGURES_DIR, MODEL_META_PATH, MODEL_PATH, RESULTS_DIR  # noqa: E402
from edge.gateway_sim import build_envelope  # noqa: E402
from edge.telemetry import sign_envelope  # noqa: E402
from ml import plots  # noqa: E402
from ml.train_model import static_rule_score  # noqa: E402
from risk_engine.engine import RiskEngine, TelemetryRejected  # noqa: E402
from risk_engine.rules import decide, evaluate_rules  # noqa: E402
from risk_engine.samples import build_request, load_test_frame  # noqa: E402
from risk_engine.store import Store  # noqa: E402

SEED = 2026
rng = random.Random(SEED)
OUT = {}


def pctl(xs, q):
    return float(np.percentile(xs, q))


# ───────────────────────── setup ─────────────────────────
meta = json.loads(MODEL_META_PATH.read_text())
T_REV, T_BLK = meta["policy"]["t_review"], meta["policy"]["t_block"]
test = load_test_frame()
booster = xgb.Booster()
booster.load_model(str(MODEL_PATH))
prob = booster.predict(xgb.DMatrix(test[FEATURE_COLS].to_numpy(float), feature_names=FEATURE_COLS))
y = test.is_fraud.to_numpy()
flags_per_row = [evaluate_rules(test.iloc[i][FEATURE_COLS].to_dict(), bool(test.iloc[i].imei_blacklisted))
                 for i in range(len(test))]


def tally(decisions):
    d = np.array(decisions)
    out = {"n": int(len(d)), "n_fraud": int(y.sum()), "n_legit": int((y == 0).sum())}
    for cls, name in ((1, "fraud"), (0, "legit")):
        for dec in ("AUTO_APPROVE", "MANUAL_REVIEW", "AUTO_BLOCK"):
            out[f"{name}_{dec}"] = int(((y == cls) & (d == dec)).sum())
    out["fraud_caught_pct"] = round(100 * (out["fraud_MANUAL_REVIEW"] + out["fraud_AUTO_BLOCK"]) / out["n_fraud"], 2)
    out["fraud_blocked_pct"] = round(100 * out["fraud_AUTO_BLOCK"] / out["n_fraud"], 2)
    out["fraud_missed"] = out["fraud_AUTO_APPROVE"]
    out["review_rate_pct"] = round(100 * (out["fraud_MANUAL_REVIEW"] + out["legit_MANUAL_REVIEW"]) / out["n"], 2)
    out["false_block_pct_of_legit"] = round(100 * out["legit_AUTO_BLOCK"] / out["n_legit"], 3)
    out["legit_frictionless_pct"] = round(100 * out["legit_AUTO_APPROVE"] / out["n_legit"], 2)
    flagged = out["fraud_MANUAL_REVIEW"] + out["fraud_AUTO_BLOCK"] + out["legit_MANUAL_REVIEW"] + out["legit_AUTO_BLOCK"]
    out["flag_precision_pct"] = round(100 * (out["fraud_MANUAL_REVIEW"] + out["fraud_AUTO_BLOCK"]) / max(flagged, 1), 2)
    return out


# ───────────────────────── E1 policy + ablations ─────────────────────────
hybrid = [decide(p, f, T_REV, T_BLK)[1] for p, f in zip(prob, flags_per_row)]
ml_only = [decide(p, [], T_REV, T_BLK)[1] for p in prob]
rules_only = [decide(0.0, f, T_REV, T_BLK)[1] for f in flags_per_row]
chk = static_rule_score(test)
static = ["AUTO_BLOCK" if s >= 3 else "MANUAL_REVIEW" if s >= 2 else "AUTO_APPROVE" for s in chk]
OUT["policy"] = {
    "Static checklist (today)": tally(static),
    "Rules only": tally(rules_only),
    "ML only (XGBoost)": tally(ml_only),
    "Hybrid risk engine (proposed)": tally(hybrid),
    "thresholds": {"review": T_REV, "block": T_BLK},
}

# ───────────────────────── E2 by attack type ─────────────────────────
by_attack = {}
atk = test.attack_type.to_numpy()
hy = np.array(hybrid)
for a in sorted(set(atk[y == 1])):
    m = atk == a
    by_attack[a] = {"n": int(m.sum()),
                    "caught_pct": round(100 * float(np.isin(hy[m], ["MANUAL_REVIEW", "AUTO_BLOCK"]).mean()), 1),
                    "blocked_pct": round(100 * float((hy[m] == "AUTO_BLOCK").mean()), 1),
                    "ml_only_caught_pct": round(100 * float(np.isin(np.array(ml_only)[m], ["MANUAL_REVIEW", "AUTO_BLOCK"]).mean()), 1)}
OUT["by_attack"] = by_attack

# ───────────────────────── E3 threshold sweep ─────────────────────────
sweep = []
for t in np.round(np.arange(0.02, 0.62, 0.02), 2):
    d = [decide(p, f, float(t), T_BLK)[1] for p, f in zip(prob, flags_per_row)]
    r = tally(d)
    sweep.append({"t_review": float(t), "review_rate_pct": r["review_rate_pct"], "fraud_caught_pct": r["fraud_caught_pct"],
                  "legit_frictionless_pct": r["legit_frictionless_pct"]})
OUT["sweep"] = sweep

# ───────────────────────── E4/E5 live engine on a fresh chain ─────────────────────────
tmp = Path(tempfile.mkdtemp())
engine = RiskEngine(store=Store(tmp / "exp.db"), chain=AuditChain(deployment_file=tmp / "deploy.json"))
N_LAT = 300
idx = rng.sample(range(len(test)), N_LAT)
rows, mismatch = [], 0
t_wall = time.perf_counter()
for i in idx:
    rec = engine.evaluate(build_request(test.iloc[i]))
    rows.append(rec)
    if rec["decision"] != hybrid[i]:
        mismatch += 1
wall = time.perf_counter() - t_wall
comp = ["telemetry_ms", "ml_shap_ms", "rules_ms", "hashing_ms", "chain_ms", "db_ms", "total_ms"]
lat = {c: {"median": round(pctl([r["latency_ms"][c] for r in rows], 50), 2),
           "p95": round(pctl([r["latency_ms"][c] for r in rows], 95), 2),
           "mean": round(st.mean(r["latency_ms"][c] for r in rows), 2)} for c in comp}
no_chain = [r["latency_ms"]["total_ms"] - r["latency_ms"]["chain_ms"] for r in rows]
gas = [r["gas_used"] for r in rows]
OUT["latency"] = {"n": N_LAT, "components": lat,
                  "decision_without_chain_ms": {"median": round(pctl(no_chain, 50), 2), "p95": round(pctl(no_chain, 95), 2)},
                  "throughput_per_s": round(N_LAT / wall, 2), "wall_s": round(wall, 1)}
dep = engine.chain.deployment
resolved_gas = []
for r in [r for r in rows if r["decision"] == "MANUAL_REVIEW"][:10]:
    res = engine.resolve(r["request_id"], "AUTO_BLOCK", "ANL-EXP", "Experiment resolution note for gas measurement.")
    resolved_gas.append(res["gas_used"])
GWEI = 20
OUT["gas"] = {"deploy_gas": dep["deploy_gas_used"], "bytecode_bytes": dep["deployed_bytecode_bytes"],
              "log_min": min(gas), "log_median": int(st.median(gas)), "log_mean": round(st.mean(gas)), "log_max": max(gas),
              "resolve_median": int(st.median(resolved_gas)) if resolved_gas else None,
              "assumed_gas_price_gwei": GWEI,
              "log_cost_eth_at_assumed_price": round(st.mean(gas) * GWEI * 1e-9, 6),
              "n_logged": len(gas)}
OUT["consistency"] = {"n": N_LAT, "online_offline_mismatches": mismatch}

# ───────────────────────── E8 audit scalability (before tampering) ─────────────────────────
t = time.perf_counter()
a = engine.audit()
OUT["audit"] = {"entries": a["on_chain_entries"], "verified": a["verified"], "integrity_ok": a["integrity_ok"],
                "seconds": round(time.perf_counter() - t, 2),
                "ms_per_entry": round((time.perf_counter() - t) / max(a["on_chain_entries"], 1) * 1000, 2)}

# ───────────────────────── E6 tamper detection ─────────────────────────
store, chain = engine.store, engine.chain
all_rows = store.all_decisions()


def edit_attacks():
    def flip_decision(r):
        r["decision"] = "AUTO_APPROVE" if r["decision"] != "AUTO_APPROVE" else "AUTO_BLOCK"

    def lower_risk(r):
        r["risk_score"] = round(max(0.0, r["risk_score"] - 0.5), 4)

    def edit_shap(r):
        k = max(r["contributions"], key=lambda f: abs(r["contributions"][f]))
        r["contributions"][k] = round(r["contributions"][k] * 0.1, 6)

    def edit_feature(r):
        r["features"]["distance_from_home_km"] = round(r["features"]["distance_from_home_km"] * 0.1, 6) + 1.0

    def drop_flag(r):
        r["rule_flags"] = []

    def swap_model(r):
        r["model_version"] = "xgb-sim-swap-forged"

    return {"Change the decision": flip_decision, "Lower the risk score": lower_risk,
            "Alter the SHAP explanation": edit_shap, "Alter an input feature value": edit_feature,
            "Clear the rule flags": drop_flag, "Relabel the model version": swap_model}


N_TAMPER = 100
tamper = {}
for name, fn in edit_attacks().items():
    detected = trials = 0
    for r in rng.sample(all_rows, len(all_rows)):
        forged = copy.deepcopy(r)
        fn(forged)
        if json.dumps(forged, sort_keys=True) == json.dumps(r, sort_keys=True):
            continue                      # attack would not change this record: not a trial
        trials += 1
        res = chain.verify_record(RiskEngine.hashable(forged), r["entry_id"])
        detected += int(not res["ok"])
        if trials == N_TAMPER:
            break
    tamper[name] = {"trials": trials, "detected": detected}

# delete / insert use the full audit
del_det = ins_det = 0
N_FULL = 15
for r in rng.sample(all_rows, N_FULL):
    store.delete_decision(r["request_id"])
    del_det += int(not engine.audit()["integrity_ok"])
    store.insert_decision({k: v for k, v in r.items()})
for r in rng.sample(all_rows, N_FULL):
    fake = copy.deepcopy(r)
    fake["request_id"] = "REQ-FORGED-" + r["request_id"][-6:]
    fake["entry_id"] = None
    fake["decision"] = "AUTO_APPROVE"
    store.insert_decision(fake)
    ins_det += int(not engine.audit()["integrity_ok"])
    store.delete_decision(fake["request_id"])
tamper["Delete a record"] = {"trials": N_FULL, "detected": del_det}
tamper["Insert a forged record"] = {"trials": N_FULL, "detected": ins_det}
tamper["clean_audit_after_restore"] = engine.audit()["integrity_ok"]

# baselines an insider can defeat
def local_chain(records):
    prev, blocks = "0" * 64, []
    for i, rec in enumerate(records):
        h = hashlib.sha256(f"{i}|{canonical_json(rec).decode()}|{prev}".encode()).hexdigest()
        blocks.append({"rec": rec, "prev": prev, "hash": h})
        prev = h
    return blocks


def verify_local(blocks):
    prev = "0" * 64
    for i, b in enumerate(blocks):
        if b["prev"] != prev or hashlib.sha256(f"{i}|{canonical_json(b['rec']).decode()}|{prev}".encode()).hexdigest() != b["hash"]:
            return False
        prev = b["hash"]
    return True


recs = [RiskEngine.hashable(r) for r in all_rows[:100]]
base_detected = 0
for _ in range(100):
    blocks = local_chain(recs)
    k = rng.randrange(len(blocks))
    blocks[k]["rec"] = dict(blocks[k]["rec"], decision="AUTO_APPROVE")
    # an insider with write access recomputes every hash from the edited block onward
    prev = blocks[k]["prev"]
    for i in range(k, len(blocks)):
        blocks[i]["prev"] = prev
        blocks[i]["hash"] = hashlib.sha256(f"{i}|{canonical_json(blocks[i]['rec']).decode()}|{prev}".encode()).hexdigest()
        prev = blocks[i]["hash"]
    base_detected += int(not verify_local(blocks))
tamper["baselines"] = {"Local hash chain, insider recomputes hashes": {"trials": 100, "detected": base_detected}}
OUT["tamper"] = tamper

# ───────────────────────── E7 edge attacks ─────────────────────────
legit_rows = test[test.is_fraud == 0]
N_EDGE = 100
edge = {}


def try_req(req):
    try:
        engine.evaluate(req)
        return True
    except TelemetryRejected:
        return False


acc = 0
for i in rng.sample(range(len(legit_rows)), N_EDGE):
    row = legit_rows.iloc[i]
    acc += int(try_req(build_request(row, request_id=row.request_id + "-E" + str(i))))
edge["Genuine telemetry (should be accepted)"] = {"trials": N_EDGE, "accepted": acc}


def attack(kind):
    caught = 0
    for i in rng.sample(range(len(legit_rows)), N_EDGE):
        row = legit_rows.iloc[i]
        req = build_request(row, request_id=row.request_id + f"-{kind[:3]}{i}")
        env = req["telemetry"]
        if kind == "Payload field altered":
            f = rng.choice(["old_sim_last_seen_min", "distance_from_home_km", "cell_changes_24h", "device_age_days"])
            env["payload"][f] = float(env["payload"][f]) + rng.uniform(1, 500)
        elif kind == "Packet replayed":
            first = build_request(row, request_id=row.request_id + f"-rp{i}")
            engine.store.remember_nonce(first["telemetry"]["nonce"], first["telemetry"]["device_id"], time.time())
            req["telemetry"] = first["telemetry"]
        elif kind == "Stale packet (1 h old)":
            req["telemetry"] = build_envelope(row, ts=time.time() - 3600)
        elif kind == "Unregistered device":
            env["device_id"] = "EDGE-ROGUE-" + str(i)
        elif kind == "Invalid IMEI checksum":
            payload = dict(env["payload"])
            payload["imei"] = payload["imei"][:-1] + str((int(payload["imei"][-1]) + 1) % 10)
            req["telemetry"] = sign_envelope(env["device_id"], payload)       # correctly signed, implausible content
        elif kind == "Wrong signing key":
            req["telemetry"] = sign_envelope(env["device_id"], env["payload"], key=b"stolen-or-guessed-key")
        caught += int(not try_req(req))
    return {"trials": N_EDGE, "rejected": caught}


for kind in ["Payload field altered", "Packet replayed", "Stale packet (1 h old)", "Unregistered device",
             "Invalid IMEI checksum", "Wrong signing key"]:
    edge[kind] = attack(kind)
OUT["edge"] = edge
OUT["model_version"] = meta["model_version"]

(RESULTS_DIR / "experiments.json").write_text(json.dumps(OUT, indent=2), encoding="utf-8")

# ───────────────────────── figures ─────────────────────────
import matplotlib.pyplot as plt  # noqa: E402

plots.apply_style()
ST = plots.STATUS
labels = {"AUTO_APPROVE": "Auto-approve", "MANUAL_REVIEW": "Manual review", "AUTO_BLOCK": "Auto-block"}

# policy outcome by class
P = OUT["policy"]["Hybrid risk engine (proposed)"]
fig, ax = plt.subplots(figsize=(8.6, 3.0))
for row, (name, key) in enumerate((("Fraudulent requests", "fraud"), ("Legitimate requests", "legit"))):
    tot = P["n_fraud"] if key == "fraud" else P["n_legit"]
    left = 0
    for dec in ("AUTO_APPROVE", "MANUAL_REVIEW", "AUTO_BLOCK"):
        v = P[f"{key}_{dec}"]
        w = 100 * v / tot
        ax.barh(row, w, left=left, color=ST[dec], height=0.52, edgecolor="white", linewidth=2,
                label=labels[dec] if row == 0 else None)
        if w > 4:
            ax.text(left + w / 2, row, f"{w:.1f}%\n({v:,})", ha="center", va="center", fontsize=9,
                    color="white" if dec != "MANUAL_REVIEW" else "#3a2a00")
        left += w
ax.set_yticks([0, 1], ["Fraudulent requests", "Legitimate requests"])
ax.invert_yaxis()
ax.set(xlim=(0, 100), xlabel="Share of requests in class (%)", title="Hybrid risk engine: decision by true class (test set)")
ax.grid(axis="y", visible=False)
ax.legend(ncol=3, loc="upper center", bbox_to_anchor=(0.5, -0.28))
plots.save(fig, FIGURES_DIR / "policy_outcomes.png")

# policy comparison
names = ["Static checklist (today)", "Rules only", "ML only (XGBoost)", "Hybrid risk engine (proposed)"]
short_names = ["Static\nchecklist", "Rules\nonly", "ML only", "Hybrid\n(proposed)"]
fig, axes = plt.subplots(1, 3, figsize=(11.5, 3.9))
for ax, key, title, col in zip(axes, ["fraud_caught_pct", "review_rate_pct", "false_block_pct_of_legit"],
                               ["(a) Fraud caught (review + block), %", "(b) Requests sent to analysts, %",
                                "(c) Legitimate requests blocked, %"], [plots.SERIES[0], plots.SERIES[3], plots.SERIES[7]]):
    vals = [OUT["policy"][n][key] for n in names]
    bars = ax.bar(short_names, vals, color=col, width=0.6)
    bars[3].set_edgecolor(plots.TEXT)
    bars[3].set_linewidth(1.6)
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v, f"{v:.1f}" if v >= 1 else f"{v:.2f}", ha="center", va="bottom", fontsize=9)
    ax.set_title(title, fontsize=10.5)
    ax.grid(axis="x", visible=False)
    ax.tick_params(axis="x", labelsize=8.5)
    ax.set_ylim(0, max(vals) * 1.18)
plots.save(fig, FIGURES_DIR / "policy_comparison.png")

# detection by attack type
fig, ax = plt.subplots(figsize=(8.6, 3.9))
types = list(by_attack)
xs = np.arange(len(types))
ax.bar(xs - 0.2, [by_attack[t]["caught_pct"] for t in types], 0.38, color=plots.SERIES[0], label="Sent to review or blocked")
ax.bar(xs + 0.2, [by_attack[t]["blocked_pct"] for t in types], 0.38, color=plots.SERIES[7], label="Auto-blocked")
for x, t in zip(xs, types):
    ax.text(x - 0.2, by_attack[t]["caught_pct"] + 1, f"{by_attack[t]['caught_pct']:.0f}", ha="center", fontsize=9)
    ax.text(x + 0.2, by_attack[t]["blocked_pct"] + 1, f"{by_attack[t]['blocked_pct']:.0f}", ha="center", fontsize=9)
ax.set_xticks(xs, [f"{t.replace('_', ' ').title()}\n(n={by_attack[t]['n']})" for t in types], fontsize=8.5)
ax.set(ylabel="Fraud requests (%)", ylim=(0, 112), title="Detection by attack archetype (test set)")
ax.grid(axis="x", visible=False)
ax.legend(loc="upper right", ncol=1)
plots.save(fig, FIGURES_DIR / "detection_by_attack.png")

# sweep
fig, ax = plt.subplots(figsize=(7.2, 4.4))
ax.plot([s["review_rate_pct"] for s in sweep], [s["fraud_caught_pct"] for s in sweep], color=plots.SERIES[0], lw=2, marker="o", ms=4)
op = OUT["policy"]["Hybrid risk engine (proposed)"]
ax.scatter([op["review_rate_pct"]], [op["fraud_caught_pct"]], s=90, color=plots.SERIES[7], zorder=5)
ax.annotate(f"chosen: review ≥ {T_REV}\n{op['review_rate_pct']:.1f}% reviewed, {op['fraud_caught_pct']:.1f}% caught",
            (op["review_rate_pct"], op["fraud_caught_pct"]), xytext=(10.5, 78.5),
            fontsize=9, arrowprops={"arrowstyle": "-", "color": plots.TEXT_2})
ax.set(xlabel="Requests sent to manual review (%)", ylabel="Fraud caught (%)", title="Analyst workload vs fraud caught (review-threshold sweep)")
plots.save(fig, FIGURES_DIR / "threshold_sweep.png")

# latency
fig, ax = plt.subplots(figsize=(8.6, 2.9))
parts = [("telemetry_ms", "Telemetry check", plots.SERIES[2]), ("ml_shap_ms", "Model + SHAP", plots.SERIES[0]),
         ("rules_ms", "Rules + blacklist", plots.SERIES[3]), ("hashing_ms", "Hashing", plots.SERIES[6]),
         ("chain_ms", "Blockchain transaction", plots.SERIES[7]), ("db_ms", "Database write", "#7b8190")]
left = 0
for key, name, col in parts:
    v = lat[key]["median"]
    ax.barh(0, v, left=left, color=col, height=0.5, edgecolor="white", linewidth=2, label=f"{name} ({v:.1f} ms)")
    left += v
ax.set(xlabel="Median time per decision (ms)", title=f"Where the time goes (n = {N_LAT}, median total {lat['total_ms']['median']:.0f} ms)")
ax.set_yticks([])
ax.grid(axis="y", visible=False)
ax.legend(ncol=3, loc="upper center", bbox_to_anchor=(0.5, -0.4), fontsize=8.5)
plots.save(fig, FIGURES_DIR / "latency_breakdown.png")

print(json.dumps({k: OUT[k] for k in ("latency", "gas", "consistency", "audit", "tamper", "edge")}, indent=1)[:4500])
print("\nPOLICY")
for n in names:
    p = OUT["policy"][n]
    print(f"  {n:34s} caught {p['fraud_caught_pct']:6.2f}%  blocked {p['fraud_blocked_pct']:6.2f}%  "
          f"review {p['review_rate_pct']:5.2f}%  false-block {p['legit_AUTO_BLOCK']:3d}  missed {p['fraud_missed']}")
print("BY ATTACK", json.dumps(by_attack))
