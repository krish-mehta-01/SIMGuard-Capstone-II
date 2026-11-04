"""
SIMGuard pipeline runner.

  python run_pipeline.py --chain         start the local Ethereum node (Ganache) in the foreground
  python run_pipeline.py --all           data -> model -> contract -> experiments -> tests
  python run_pipeline.py --step data     generate the synthetic dataset
  python run_pipeline.py --step ml       train XGBoost, baselines, SHAP, calibrate policy
  python run_pipeline.py --step contract compile the Solidity contract
  python run_pipeline.py --step exp      run the experiments (needs the chain)
  python run_pipeline.py --step test     run the automated test suite (needs the chain)
  python run_pipeline.py --serve         start the risk engine API and console (default http://127.0.0.1:8051)
"""

import argparse
import subprocess
import sys
from pathlib import Path

BASE = Path(__file__).resolve().parent


def run(desc, args, cwd=BASE):
    print(f"\n{'=' * 64}\n  {desc}\n{'=' * 64}", flush=True)
    r = subprocess.run(args, cwd=str(cwd))
    if r.returncode != 0:
        print(f"[FAILED] {desc} (exit code {r.returncode})")
        sys.exit(r.returncode)


def chain_up() -> bool:
    sys.path.insert(0, str(BASE))
    from web3 import Web3
    from config import RPC_URL
    try:
        return Web3(Web3.HTTPProvider(RPC_URL, request_kwargs={"timeout": 3})).is_connected()
    except Exception:
        return False


def need_chain():
    if not chain_up():
        print("\nThe local Ethereum node is not running. In another terminal run:\n"
              "    python run_pipeline.py --chain\n")
        sys.exit(2)


STEPS = {
    "data": ("Generating the synthetic SIM-swap dataset", [sys.executable, "data/generate_dataset.py"]),
    "ml": ("Training XGBoost, baselines and SHAP; calibrating the policy", [sys.executable, "ml/train_model.py"]),
    "contract": ("Compiling SIMSwapAuditLog.sol", ["node", "compile.js"]),
    "exp": ("Running experiments", [sys.executable, "experiments/run_experiments.py"]),
    "test": ("Running the test suite", [sys.executable, "-m", "pytest", "tests", "-q", "-p", "no:cacheprovider"]),
}


def main():
    ap = argparse.ArgumentParser(description="SIMGuard pipeline runner")
    ap.add_argument("--step", choices=list(STEPS))
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--chain", action="store_true")
    ap.add_argument("--serve", action="store_true")
    a = ap.parse_args()

    if a.chain:
        run("Local Ethereum node (Ganache, chain id 1337) on http://127.0.0.1:8545",
            ["node", "node_modules/ganache/dist/node/cli.js", "--port", "8545", "--chain.chainId", "1337",
             "--wallet.deterministic", "--logging.quiet"], cwd=BASE / "blockchain")
    elif a.serve:
        need_chain()
        run("SIMGuard risk engine and console", [sys.executable, "risk_engine/api.py"])
    elif a.step:
        if a.step in ("exp", "test"):
            need_chain()
        desc, cmd = STEPS[a.step]
        run(desc, cmd, cwd=BASE / "blockchain" if a.step == "contract" else BASE)
    elif a.all:
        for key in ("data", "ml", "contract"):
            run(STEPS[key][0], STEPS[key][1], cwd=BASE / "blockchain" if key == "contract" else BASE)
        need_chain()
        for key in ("exp", "test"):
            run(*STEPS[key])
        print("\nAll stages completed. Artifacts are in results/.")
    else:
        ap.print_help()


if __name__ == "__main__":
    main()
