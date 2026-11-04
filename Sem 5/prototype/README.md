# SIMGuard: Blockchain-Secured SIM Swap Fraud Detection with Explainable AI

Capstone prototype, RMK Engineering College (IT / CSE / ECE). A SIM replacement request is scored by an
XGBoost model, checked against deterministic security rules, explained with TreeSHAP, decided in three tiers
(auto-approve / manual review / auto-block) and anchored on an Ethereum smart contract so the decision *and the
reasoning behind it* cannot be rewritten afterwards.

## Layout

```
prototype/
├── config.py                  shared paths, feature order, keys
├── data/generate_dataset.py   synthetic requests: 4 attack archetypes, hard negatives, undetectable "stealth" fraud
├── ml/                        train_model.py (XGBoost + 4 baselines), explain.py (TreeSHAP), plots.py
├── edge/                      telemetry.py (HMAC-signed packets), gateway_sim.py (SIM800L AT-command emulator)
├── risk_engine/               rules.py, engine.py (orchestration), store.py (SQLite), api.py (FastAPI), samples.py
├── blockchain/                SIMSwapAuditLog.sol, compile.js, chain.py (web3 client)
├── dashboard/                 operations console (served by the API; all values come from the API)
├── experiments/run_experiments.py   every number in the report's results chapter
├── tests/                     43 automated tests
├── tools/                     seed_console.py, capture_screens.py
└── results/                   metrics, figures, screenshots, experiments.json, chain_deployment.json
```

## Run it

```bash
pip install -r requirements.txt
cd blockchain && npm install && cd ..

python run_pipeline.py --chain        # terminal 1: local Ethereum node (leave running)
python run_pipeline.py --all          # terminal 2: data -> model -> contract -> experiments -> tests
python run_pipeline.py --serve        # console at http://127.0.0.1:8051 , API docs at /docs
python tools/seed_console.py          # optional: fill the console with 38 real decisions
```

## What is real and what is simulated

| Part | Status |
|---|---|
| Dataset | **Synthetic.** Real SIM-swap records are confidential. Classes overlap and ~6% of fraud is undetectable by design, so results are far below 100%. |
| Model, SHAP, rules, policy calibration | Real. Thresholds are chosen on a validation split; all reported numbers are on a held-out test split. |
| Smart contract | Real Solidity 0.8.24, deployed and called through web3 on a **local Ganache chain**. Gas figures are measured. Public Sepolia needs a funded wallet and only changes `SIMGUARD_RPC_URL` and the signing account. |
| Edge gateway | **Software emulation** of a SIM800L modem (AT commands) with real HMAC signing, replay and freshness checks. No physical hardware was measured. |
| Latency | Dominated by the chain write. Ganache confirms in ~100 ms; a public network's block time (seconds) would dominate instead. |

## Key results (held-out test set: 4,000 requests, 200 fraudulent)

| Policy | Fraud caught | Sent to analysts | Legit blocked |
|---|---|---|---|
| Static checklist (today) | 39.5% | 3.5% | 2 |
| ML only | 82.0% | 4.0% | 0 |
| **Hybrid risk engine** | **84.5%** | 6.8% | 7 |

XGBoost ROC-AUC 0.948 (Random Forest 0.944, Logistic Regression 0.907, Isolation Forest 0.795, rule checklist 0.750).
Tamper detection: 100% of edits, deletions and forged insertions detected; a local hash chain that an insider can
recompute detects 0%. See `results/experiments.json` for all numbers.

## Limitations

* Synthetic data: absolute accuracy will not transfer to a real operator's traffic.
* The model cannot see "stealth" fraud that looks exactly like genuine behaviour (6.7% recall on that class).
* Anchoring proves *what was decided*; it cannot prove the inputs were true. Edge signing narrows that gap, it does not close it.
* One signing account writes to the contract. A production deployment would use several operator keys or a consortium chain.
