"""Populates a running console with a realistic mix of held-out requests and two analyst resolutions."""

import random
import sys
from collections import Counter
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from risk_engine.samples import build_request, load_test_frame  # noqa: E402

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8051"


def main(n_legit=24, n_fraud=14):
    c = httpx.Client(base_url=BASE, timeout=30)
    print("engine:", c.get("/api/v1/health").json()["model_version"])
    test = load_test_frame()
    rng = random.Random(7)
    idx = (rng.sample(list(test[test.is_fraud == 0].index), n_legit)
           + rng.sample(list(test[test.is_fraud == 1].index), n_fraud))
    rng.shuffle(idx)
    cnt = Counter()
    for i in idx:
        r = c.post("/api/v1/evaluate", json=build_request(test.loc[i]))
        cnt[r.json().get("decision", r.status_code)] += 1
    print("decisions:", dict(cnt))
    reviews = c.get("/api/v1/decisions", params={"decision": "MANUAL_REVIEW", "limit": 5}).json()["decisions"]
    outcomes = [("AUTO_BLOCK", "Called the registered number; customer denied requesting a SIM swap."),
                ("AUTO_APPROVE", "Customer visited the branch with original ID; biometric match confirmed.")]
    for d, (final, note) in zip(reviews[1:3], outcomes):   # leave the newest review open for the demo
        r = c.post(f"/api/v1/decisions/{d['request_id']}/resolve",
                   json={"final_decision": final, "analyst_id": "ANL-007", "note": note})
        print("resolved", d["request_id"], "->", final, r.status_code)
    print("integrity ok:", c.get("/api/v1/audit/verify").json()["integrity_ok"])


if __name__ == "__main__":
    main()
