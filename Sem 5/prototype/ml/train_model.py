"""
XGBoost SIM-Swap Fraud Model: training, baselines, SHAP and policy calibration
==============================================================================
Protocol
  * Stratified 60 / 20 / 20 split (train / validation / test), seed 42.
  * Every model's decision threshold is chosen on the validation split
    (maximum F1); the test split is touched only for final reporting.
  * Baselines: static rule checklist (current practice), Logistic Regression,
    Random Forest, Isolation Forest (unsupervised).
  * Risk-engine thresholds (review / block) are chosen on the validation split
    by minimising an explicit operating cost, subject to a manual-review
    capacity of 8% of requests.

Outputs (results/)
  xgb_sim_swap.json, model_meta.json, model_comparison.json, splits.json,
  figures/roc_pr_curves.png, figures/confusion_matrix.png,
  figures/shap_importance.png, figures/shap_beeswarm.png, figures/shap_waterfall.png
"""

import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.ensemble import IsolationForest, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (accuracy_score, average_precision_score, confusion_matrix, f1_score,
                             precision_recall_curve, precision_score, recall_score, roc_auc_score,
                             roc_curve)
from sklearn.model_selection import StratifiedKFold, train_test_split
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import (DATASET_CSV, FEATURE_COLS, FEATURE_LABELS, FIGURES_DIR,  # noqa: E402
                    MODEL_META_PATH, MODEL_PATH, RESULTS_DIR)
from ml import plots  # noqa: E402
from risk_engine.rules import MEDIUM_BOOST, evaluate_rules  # noqa: E402

SEED = 42
MODEL_VERSION = "xgb-sim-swap-2026.10-v1"
# Operating cost weights used to place the review / block thresholds.
COST_MISSED_FRAUD = 100.0   # fraud auto-approved (account takeover)
COST_FALSE_BLOCK = 20.0     # genuine customer auto-blocked
COST_REVIEW = 1.0           # one manual review by a fraud analyst
REVIEW_CAPACITY = 0.08      # analysts can review at most 8% of daily requests


def load_splits():
    if not DATASET_CSV.exists():
        from data.generate_dataset import generate_dataset
        generate_dataset().to_csv(DATASET_CSV, index=False)
    df = pd.read_csv(DATASET_CSV, dtype={"msisdn": str, "new_imei": str})
    train_val, test = train_test_split(df, test_size=0.20, stratify=df.is_fraud, random_state=SEED)
    train, val = train_test_split(train_val, test_size=0.25, stratify=train_val.is_fraud, random_state=SEED)
    return df, train, val, test


def static_rule_score(frame: pd.DataFrame) -> np.ndarray:
    """Checklist used by verification desks today: one point per red flag."""
    return ((frame.auth_failures_7d >= 3).astype(int)
            + frame.profile_change_7d
            + (1 - frame.kyc_biometric_verified)
            + (frame.distance_from_home_km > 100).astype(int)
            + (frame.sim_age_days < 7).astype(int)
            + frame.imei_blacklisted).to_numpy(dtype=float)


def best_f1_threshold(y, scores):
    p, r, t = precision_recall_curve(y, scores)
    f1 = 2 * p * r / np.clip(p + r, 1e-12, None)
    i = int(np.nanargmax(f1[:-1]))
    return float(t[i])


def binary_metrics(y, scores, threshold):
    pred = (scores >= threshold).astype(int)
    return {
        "threshold": round(float(threshold), 4),
        "accuracy": round(accuracy_score(y, pred), 4),
        "precision": round(precision_score(y, pred, zero_division=0), 4),
        "recall": round(recall_score(y, pred), 4),
        "f1": round(f1_score(y, pred), 4),
        "roc_auc": round(roc_auc_score(y, scores), 4),
        "pr_auc": round(average_precision_score(y, scores), 4),
    }


def rule_arrays(frame: pd.DataFrame):
    """Vectorised rule severities for policy calibration."""
    crit, high, n_med = [], [], []
    for _, row in frame.iterrows():
        flags = evaluate_rules(row[FEATURE_COLS].to_dict(), bool(row.imei_blacklisted))
        sev = [f["severity"] for f in flags]
        crit.append("CRITICAL" in sev)
        high.append("HIGH" in sev)
        n_med.append(sev.count("MEDIUM"))
    return np.array(crit), np.array(high), np.array(n_med)


def calibrate_policy(y, prob, crit, high, n_med):
    risk = np.minimum(1.0, prob + MEDIUM_BOOST * n_med)
    best = None
    for t_review in np.round(np.arange(0.02, 0.61, 0.01), 2):
        for t_block in np.round(np.arange(t_review + 0.05, 0.99, 0.01), 2):
            block = crit | (risk >= t_block)
            review = ~block & (high | (risk >= t_review))
            approve = ~block & ~review
            if review.mean() > REVIEW_CAPACITY:
                continue
            cost = (COST_MISSED_FRAUD * np.sum(approve & (y == 1))
                    + COST_FALSE_BLOCK * np.sum(block & (y == 0))
                    + COST_REVIEW * np.sum(review))
            if best is None or cost < best[0]:
                best = (cost, float(t_review), float(t_block))
    return {"t_review": best[1], "t_block": best[2], "validation_cost": float(best[0])}


# ─────────────────────────────── figures ───────────────────────────────

def fig_roc_pr(y, model_scores):
    import matplotlib.pyplot as plt
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(11, 4.6))
    for (name, s), color in zip(model_scores.items(), plots.SERIES):
        fpr, tpr, _ = roc_curve(y, s)
        a1.plot(fpr, tpr, color=color, lw=2, label=f"{name} (AUC {roc_auc_score(y, s):.3f})")
        p, r, _ = precision_recall_curve(y, s)
        a2.plot(r, p, color=color, lw=2, label=f"{name} (AP {average_precision_score(y, s):.3f})")
    a1.plot([0, 1], [0, 1], color=plots.TEXT_2, lw=1, ls="--")
    a1.set(xlabel="False positive rate", ylabel="True positive rate", title="(a) ROC curves (test set)")
    a2.axhline(y.mean(), color=plots.TEXT_2, lw=1, ls="--")
    a2.set(xlabel="Recall", ylabel="Precision", title="(b) Precision-Recall curves (test set)")
    a1.legend(loc="lower right", fontsize=9)
    a2.legend(loc="lower left", fontsize=9)
    plots.save(fig, FIGURES_DIR / "roc_pr_curves.png")


def fig_confusion(y, pred):
    import matplotlib.pyplot as plt
    cm = confusion_matrix(y, pred)
    fig, ax = plt.subplots(figsize=(5.2, 4.4))
    ax.grid(False)
    rates = cm / cm.sum(axis=1, keepdims=True)
    ax.imshow(rates, cmap=matplotlib_cmap(), vmin=0, vmax=1)
    labels = ["Legitimate", "Fraud"]
    ax.set_xticks([0, 1], labels)
    ax.set_yticks([0, 1], labels)
    ax.set(xlabel="Predicted class", ylabel="Actual class", title="XGBoost confusion matrix (test set)\ncolour = share of each actual class")
    for i in range(2):
        for j in range(2):
            ax.text(j, i, f"{cm[i, j]:,}\n({rates[i, j]:.1%})", ha="center", va="center", fontsize=14,
                    color="white" if rates[i, j] > 0.5 else plots.TEXT)
    for s in ax.spines.values():
        s.set_visible(False)
    plots.save(fig, FIGURES_DIR / "confusion_matrix.png")
    return cm


def matplotlib_cmap(low=0):
    from matplotlib.colors import LinearSegmentedColormap
    ramp = (["#f4f8fd"] + plots.BLUE_RAMP)[low:]
    return LinearSegmentedColormap.from_list("blue_seq", ramp)


def fig_shap_importance(mean_abs):
    import matplotlib.pyplot as plt
    order = mean_abs.sort_values()
    fig, ax = plt.subplots(figsize=(8, 5.6))
    ax.barh([FEATURE_LABELS[f] for f in order.index], order.values, color=plots.SERIES[0], height=0.62)
    for i, v in enumerate(order.values):
        ax.text(v + order.max() * 0.01, i, f"{v:.3f}", va="center", fontsize=9, color=plots.TEXT_2)
    ax.set(xlabel="Mean |SHAP value| (log-odds)", title="Global feature importance (TreeSHAP, test set)")
    ax.grid(axis="y", visible=False)
    plots.save(fig, FIGURES_DIR / "shap_importance.png")


def fig_shap_beeswarm(contrib, X, order):
    import matplotlib.pyplot as plt
    rng = np.random.default_rng(SEED)
    fig, ax = plt.subplots(figsize=(8.5, 6.4))
    cmap = matplotlib_cmap(low=2)
    feats = list(order)[::-1]
    for row, f in enumerate(feats):
        j = FEATURE_COLS.index(f)
        vals = X[:, j]
        rank = pd.Series(vals).rank(pct=True).to_numpy()
        jitter = rng.uniform(-0.28, 0.28, len(vals))
        ax.scatter(contrib[:, j], row + jitter, c=rank, cmap=cmap, s=7, alpha=0.75,
                   linewidths=0, rasterized=True)
    ax.axvline(0, color=plots.TEXT_2, lw=1)
    ax.set_yticks(range(len(feats)), [FEATURE_LABELS[f] for f in feats])
    ax.set(xlabel="SHAP value (impact on log-odds of fraud)", title="SHAP summary (test set)")
    ax.grid(axis="y", visible=False)
    sm = plt.cm.ScalarMappable(cmap=cmap)
    cb = fig.colorbar(sm, ax=ax, fraction=0.03, pad=0.02)
    cb.set_ticks([0, 1], labels=["Low", "High"])
    cb.set_label("Feature value (percentile)", color=plots.TEXT_2)
    cb.outline.set_visible(False)
    plots.save(fig, FIGURES_DIR / "shap_beeswarm.png")


def fig_shap_waterfall(row_feats, contrib_row, base, prob, request_id):
    import matplotlib.pyplot as plt
    s = pd.Series(contrib_row, index=FEATURE_COLS)
    top = s.reindex(s.abs().sort_values(ascending=False).index)[:8]
    rest = s.drop(top.index).sum()
    items = list(top.items()) + [("other", rest)]
    fig, ax = plt.subplots(figsize=(9, 5.4))
    cursor = base
    labels = []
    for i, (f, v) in enumerate(items):
        color = plots.DIVERGING_POS if v > 0 else plots.DIVERGING_NEG
        ax.barh(i, v, left=cursor, color=color, height=0.6)
        ax.text(cursor + v + (0.05 if v >= 0 else -0.05), i, f"{v:+.2f}", va="center",
                ha="left" if v >= 0 else "right", fontsize=9, color=plots.TEXT)
        cursor += v
        if f == "other":
            labels.append(f"{len(FEATURE_COLS) - 8} other features")
        else:
            val = row_feats[f]
            labels.append(f"{FEATURE_LABELS[f]} = {val:g}")
    ax.axvline(base, color=plots.TEXT_2, lw=1, ls="--")
    ax.axvline(cursor, color=plots.TEXT, lw=1)
    ax.set_yticks(range(len(items)), labels)
    ax.invert_yaxis()
    ax.grid(axis="y", visible=False)
    lo, hi = ax.get_xlim()
    ax.set_xlim(lo - 0.3, hi + 0.4)
    ax.set(xlabel="Log-odds of fraud",
           title=f"Local explanation for {request_id}: base {base:.2f} -> f(x) {cursor:.2f} (p = {prob:.3f})")
    plots.save(fig, FIGURES_DIR / "shap_waterfall.png")


# ─────────────────────────────── main ───────────────────────────────

def main():
    plots.apply_style()
    df, train, val, test = load_splits()
    Xtr, ytr = train[FEATURE_COLS].to_numpy(float), train.is_fraud.to_numpy()
    Xva, yva = val[FEATURE_COLS].to_numpy(float), val.is_fraud.to_numpy()
    Xte, yte = test[FEATURE_COLS].to_numpy(float), test.is_fraud.to_numpy()
    print(f"Split sizes  train={len(train)}  val={len(val)}  test={len(test)}  "
          f"(fraud {ytr.sum()}/{yva.sum()}/{yte.sum()})")

    comparison, test_scores = {}, {}

    # XGBoost with early stopping on the validation split
    t0 = time.perf_counter()
    model = xgb.XGBClassifier(n_estimators=1000, max_depth=4, learning_rate=0.05, subsample=0.8,
                              colsample_bytree=0.8, min_child_weight=2, eval_metric="aucpr",
                              early_stopping_rounds=50, random_state=SEED, n_jobs=-1)
    model.fit(pd.DataFrame(Xtr, columns=FEATURE_COLS), ytr,
              eval_set=[(pd.DataFrame(Xva, columns=FEATURE_COLS), yva)], verbose=False)
    xgb_train_s = time.perf_counter() - t0
    booster = model.get_booster()
    best_iter = int(model.best_iteration)

    def xgb_scores(X):
        return model.predict_proba(pd.DataFrame(X, columns=FEATURE_COLS))[:, 1]

    baselines = {
        "Static rule checklist": (None, lambda f: static_rule_score(f)),
        "Logistic Regression": (make_pipeline(StandardScaler(), LogisticRegression(
            class_weight="balanced", max_iter=2000)), None),
        "Random Forest": (RandomForestClassifier(n_estimators=400, min_samples_leaf=3,
                                                 class_weight="balanced_subsample", n_jobs=-1,
                                                 random_state=SEED), None),
        "Isolation Forest": (IsolationForest(n_estimators=300, random_state=SEED), None),
    }

    for name, (est, fn) in baselines.items():
        t0 = time.perf_counter()
        if fn is not None:
            s_val, s_test = fn(val), fn(test)
        elif name == "Isolation Forest":
            est.fit(Xtr)
            s_val, s_test = -est.score_samples(Xva), -est.score_samples(Xte)
        else:
            est.fit(Xtr, ytr)
            s_val, s_test = est.predict_proba(Xva)[:, 1], est.predict_proba(Xte)[:, 1]
        elapsed = time.perf_counter() - t0
        thr = best_f1_threshold(yva, s_val)
        comparison[name] = binary_metrics(yte, s_test, thr) | {"fit_seconds": round(elapsed, 2)}
        test_scores[name] = s_test

    s_val_xgb, s_test_xgb = xgb_scores(Xva), xgb_scores(Xte)
    thr = best_f1_threshold(yva, s_val_xgb)
    comparison["XGBoost (proposed)"] = binary_metrics(yte, s_test_xgb, thr) | {
        "fit_seconds": round(xgb_train_s, 2)}
    test_scores = {"XGBoost (proposed)": s_test_xgb} | test_scores

    # 5-fold cross-validation on train+val (fixed number of trees)
    tv = pd.concat([train, val])
    Xtv, ytv = tv[FEATURE_COLS].to_numpy(float), tv.is_fraud.to_numpy()
    cv_auc, cv_ap = [], []
    for k, (a, b) in enumerate(StratifiedKFold(5, shuffle=True, random_state=SEED).split(Xtv, ytv)):
        m = xgb.XGBClassifier(n_estimators=best_iter + 1, max_depth=4, learning_rate=0.05,
                              subsample=0.8, colsample_bytree=0.8, min_child_weight=2,
                              random_state=SEED, n_jobs=-1)
        m.fit(Xtv[a], ytv[a])
        p = m.predict_proba(Xtv[b])[:, 1]
        cv_auc.append(roc_auc_score(ytv[b], p))
        cv_ap.append(average_precision_score(ytv[b], p))

    # Inference latency (single request, warm)
    one = pd.DataFrame(Xte[:1], columns=FEATURE_COLS)
    for _ in range(20):
        model.predict_proba(one)
    t0 = time.perf_counter()
    for i in range(500):
        model.predict_proba(pd.DataFrame(Xte[i:i + 1], columns=FEATURE_COLS))
    single_ms = (time.perf_counter() - t0) / 500 * 1000

    # SHAP (TreeSHAP via XGBoost) on the test split
    dte = xgb.DMatrix(Xte, feature_names=FEATURE_COLS)
    contrib = booster.predict(dte, pred_contribs=True, iteration_range=(0, best_iter + 1))
    margin = booster.predict(dte, output_margin=True, iteration_range=(0, best_iter + 1))
    additivity_err = float(np.max(np.abs(contrib.sum(axis=1) - margin)))
    base_value = float(contrib[0, -1])
    mean_abs = pd.Series(np.abs(contrib[:, :-1]).mean(axis=0), index=FEATURE_COLS)

    # Policy calibration on validation split
    crit, high, n_med = rule_arrays(val)
    policy = calibrate_policy(yva, s_val_xgb, crit, high, n_med)

    # Persist model: keep only the early-stopped trees
    booster_final = booster[: best_iter + 1]
    booster_final.save_model(str(MODEL_PATH))

    meta = {
        "model_version": MODEL_VERSION,
        "features": FEATURE_COLS,
        "best_iteration": best_iter,
        "n_trees": best_iter + 1,
        "hyperparameters": {"max_depth": 4, "learning_rate": 0.05, "subsample": 0.8,
                            "colsample_bytree": 0.8, "min_child_weight": 2},
        "classification_threshold": comparison["XGBoost (proposed)"]["threshold"],
        "policy": policy | {"cost_weights": {"missed_fraud": COST_MISSED_FRAUD,
                                             "false_block": COST_FALSE_BLOCK,
                                             "review": COST_REVIEW},
                            "review_capacity": REVIEW_CAPACITY},
        "base_value_logodds": base_value,
        "train_size": len(train), "val_size": len(val), "test_size": len(test),
        "dataset_size": len(df), "fraud_rate": round(float(df.is_fraud.mean()), 4),
    }
    with open(MODEL_META_PATH, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)

    summary = {
        "models": comparison,
        "xgboost_cv": {"roc_auc_mean": round(float(np.mean(cv_auc)), 4),
                       "roc_auc_std": round(float(np.std(cv_auc)), 4),
                       "pr_auc_mean": round(float(np.mean(cv_ap)), 4),
                       "pr_auc_std": round(float(np.std(cv_ap)), 4)},
        "xgboost_inference_ms_single": round(single_ms, 3),
        "shap": {"additivity_max_abs_error": additivity_err, "base_value_logodds": base_value,
                 "mean_abs": {k: round(float(v), 4) for k, v in mean_abs.sort_values(ascending=False).items()}},
        "policy": policy,
        "split": {"train": len(train), "val": len(val), "test": len(test),
                  "train_fraud": int(ytr.sum()), "val_fraud": int(yva.sum()), "test_fraud": int(yte.sum())},
    }
    with open(RESULTS_DIR / "model_comparison.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    with open(RESULTS_DIR / "splits.json", "w", encoding="utf-8") as f:
        json.dump({"train": train.request_id.tolist(), "val": val.request_id.tolist(),
                   "test": test.request_id.tolist()}, f)

    # Figures
    fig_roc_pr(yte, test_scores)
    cm = fig_confusion(yte, (s_test_xgb >= thr).astype(int))
    fig_shap_importance(mean_abs)
    fig_shap_beeswarm(contrib[:, :-1], Xte, mean_abs.sort_values(ascending=False).index)
    probs = 1 / (1 + np.exp(-margin))
    candidates = np.where((yte == 1) & (probs > 0.9) & (test.imei_blacklisted.to_numpy() == 0))[0]
    k = int(candidates[0]) if len(candidates) else int(np.argmax(probs))
    fig_shap_waterfall(test.iloc[k][FEATURE_COLS].to_dict(), contrib[k, :-1], base_value,
                       float(probs[k]), test.iloc[k].request_id)
    summary["waterfall_request_id"] = test.iloc[k].request_id
    summary["confusion_matrix"] = cm.tolist()
    with open(RESULTS_DIR / "model_comparison.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)

    print("\nTest-set comparison (threshold chosen on validation):")
    print(pd.DataFrame(comparison).T[["precision", "recall", "f1", "roc_auc", "pr_auc"]].to_string())
    print(f"\nXGBoost 5-fold CV ROC-AUC {np.mean(cv_auc):.4f} +/- {np.std(cv_auc):.4f}, "
          f"PR-AUC {np.mean(cv_ap):.4f} +/- {np.std(cv_ap):.4f}")
    print(f"Best iteration {best_iter}, single-request inference {single_ms:.2f} ms")
    print(f"SHAP additivity max error {additivity_err:.2e}")
    print(f"Policy thresholds: review >= {policy['t_review']}, block >= {policy['t_block']}")


if __name__ == "__main__":
    main()
