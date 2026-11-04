"""Loads every number the report quotes from the prototype's result files, so no figure is typed by hand."""

import json
from importlib import metadata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROTO = ROOT / "prototype"
RES = PROTO / "results"


def load(name):
    return json.loads((RES / name).read_text(encoding="utf-8"))


class Data:
    def __init__(self):
        self.E = load("experiments.json")
        self.M = load("model_comparison.json")
        self.META = load("model_meta.json")
        self.DEP = load("chain_deployment.json")
        self.models = self.M["models"]
        self.xgb = self.models["XGBoost (proposed)"]
        self.pol = {k: v for k, v in self.E["policy"].items() if k != "thresholds"}
        self.hyb = self.pol["Hybrid risk engine (proposed)"]
        self.mlo = self.pol["ML only (XGBoost)"]
        self.chk = self.pol["Static checklist (today)"]
        self.rul = self.pol["Rules only"]
        self.lat = self.E["latency"]
        self.gas = self.E["gas"]
        self.tamper = self.E["tamper"]
        self.edge = self.E["edge"]
        self.split = self.M["split"]
        self.cv = self.M["xgboost_cv"]
        self.shap = self.M["shap"]
        self.pc = self.META["policy"]
        import pandas as pd
        ds = pd.read_csv(PROTO / "data" / "sim_swap_dataset.csv", usecols=["is_fraud", "attack_type", "imei_blacklisted"])
        self.ds_n = len(ds)
        self.ds_fraud = int(ds.is_fraud.sum())
        self.ds_attack = ds[ds.is_fraud == 1].attack_type.value_counts().to_dict()
        self.ds_black = {"fraud": int(ds[ds.is_fraud == 1].imei_blacklisted.sum()),
                         "legit": int(ds[ds.is_fraud == 0].imei_blacklisted.sum())}

    # ---- helpers -------------------------------------------------------
    @staticmethod
    def cost(p, w=(100, 20, 1)):
        """Operating cost under the calibration weights: missed fraud, false block, one manual review."""
        reviews = p["fraud_MANUAL_REVIEW"] + p["legit_MANUAL_REVIEW"]
        return w[0] * p["fraud_AUTO_APPROVE"] + w[1] * p["legit_AUTO_BLOCK"] + w[2] * reviews

    @property
    def tamper_trials(self):
        keys = [k for k in self.tamper if k not in ("baselines", "clean_audit_after_restore")]
        return sum(self.tamper[k]["trials"] for k in keys), sum(self.tamper[k]["detected"] for k in keys)

    @staticmethod
    def ver(pkg):
        try:
            return metadata.version(pkg)
        except Exception:
            return "n/a"
