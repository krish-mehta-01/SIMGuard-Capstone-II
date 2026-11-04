"""
Synthetic SIM-Swap Request Dataset Generator
============================================
Real subscriber-level SIM swap records are confidential under telecom
licence conditions and the Digital Personal Data Protection Act, 2023, so the
prototype is trained on a synthetic dataset generated from an explicit
attack model.

Design goals (so that results are meaningful, not trivially separable):
  * Legitimate and fraudulent requests share the same base distributions.
    Fraud only *shifts* the probability of certain signals.
  * Legitimate "hard negatives" exist: a genuine customer upgrading to an
    eSIM keeps the old SIM active; travellers request swaps far from home.
  * "Stealth" fraud exists: ~6% of attacks are drawn from the legitimate
    distribution and are undetectable from these features.
  * Four attack archetypes reported in the literature are mixed:
      A. Social engineering of call-centre / online support
      B. Insider collusion at a retailer (one agent, many swaps)
      C. Forged identity documents presented in a store
      D. Rapid repeat swaps on an already-compromised number

Each row is one SIM replacement request. Columns:
  request_id, request_timestamp, msisdn, new_imei, imei_blacklisted,
  channel, agent_id, <16 model features>, attack_type, is_fraud
"""

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import CHANNELS, DATASET_CSV, FEATURE_COLS  # noqa: E402

SEED = 42
N_SAMPLES = 20_000
FRAUD_RATE = 0.05
STEALTH_SHARE = 0.06


def luhn_check_digit(body: str) -> str:
    """IMEI check digit (Luhn algorithm, 3GPP TS 23.003)."""
    total = 0
    for i, ch in enumerate(reversed(body)):
        d = int(ch)
        if i % 2 == 0:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return str((10 - total % 10) % 10)


def random_imei(rng) -> str:
    tac = rng.choice(["35467890", "86753091", "35209211", "49015420", "86450912", "35332411"])
    serial = "".join(str(d) for d in rng.integers(0, 10, 6))
    body = tac + serial
    return body + luhn_check_digit(body)


def legit_block(rng, n):
    """Baseline behaviour of genuine SIM replacement requests."""
    account_age = np.clip(rng.lognormal(np.log(1100), 0.8, n), 15, 6000)
    sim_age = np.minimum(account_age, np.clip(rng.lognormal(np.log(480), 0.9, n), 1, 6000))
    channel = rng.choice(4, n, p=[0.45, 0.15, 0.25, 0.15])

    # Reason for a genuine swap drives the old-SIM / handset signals.
    reason = rng.choice(3, n, p=[0.30, 0.25, 0.45])  # 0 lost/stolen, 1 damaged SIM, 2 upgrade/eSIM
    old_sim_seen = np.where(
        reason == 0, rng.exponential(600, n),
        np.where(reason == 1, rng.exponential(1500, n), rng.exponential(30, n)))
    imei_changed = np.where(reason == 1, rng.random(n) < 0.15, rng.random(n) < 0.60).astype(int)
    device_age = np.where(
        imei_changed == 1,
        np.where(rng.random(n) < 0.6, 0, rng.exponential(200, n)),
        rng.exponential(400, n) + 30)

    travelling = rng.random(n) < 0.08
    distance = np.where(travelling, rng.uniform(50, 1500, n), rng.exponential(6, n))

    hour = np.where(rng.random(n) < 0.12, rng.integers(0, 24, n),
                    np.clip(np.round(rng.normal(14, 3, n)), 0, 23))
    kyc_p = np.array([0.96, 0.55, 0.85, 0.93])[channel]

    return pd.DataFrame({
        "account_age_days": np.round(account_age),
        "sim_age_days": np.round(sim_age),
        "swaps_last_180d": rng.poisson(0.15, n),
        "imei_changed": imei_changed,
        "device_age_days": np.round(device_age),
        "old_sim_last_seen_min": np.round(old_sim_seen, 1),
        "distance_from_home_km": np.round(distance, 1),
        "cell_changes_24h": rng.poisson(np.where(travelling, 9, 3)),
        "hour_of_request": hour.astype(int),
        "channel_code": channel,
        "kyc_biometric_verified": (rng.random(n) < kyc_p).astype(int),
        "auth_failures_7d": rng.poisson(0.3, n),
        "profile_change_7d": (rng.random(n) < 0.05).astype(int),
        "agent_swaps_24h": rng.poisson(5, n),
        "roaming_flag": (rng.random(n) < np.where(travelling, 0.45, 0.03)).astype(int),
        "attack_type": "NONE",
    })


def fraud_block(rng, n):
    """Start from legitimate behaviour, then apply an attack archetype."""
    df = legit_block(rng, n)
    archetype = rng.choice(4, n, p=[0.45, 0.25, 0.20, 0.10])
    stealth = rng.random(n) < STEALTH_SHARE

    for i in range(n):
        if stealth[i]:
            df.at[i, "attack_type"] = "STEALTH"
            continue
        a = archetype[i]
        # Common to every attack: the victim's phone is usually still live.
        if rng.random() < 0.80:
            df.at[i, "old_sim_last_seen_min"] = round(rng.exponential(25), 1)
        if rng.random() < 0.88:
            df.at[i, "imei_changed"] = 1
            df.at[i, "device_age_days"] = 0 if rng.random() < 0.55 else round(rng.exponential(40))

        if a == 0:  # Social engineering of remote support
            df.at[i, "attack_type"] = "SOCIAL_ENGINEERING"
            df.at[i, "channel_code"] = 1 if rng.random() < 0.55 else 2
            df.at[i, "kyc_biometric_verified"] = int(rng.random() < 0.35)
            df.at[i, "auth_failures_7d"] = rng.poisson(2.5)
            df.at[i, "profile_change_7d"] = int(rng.random() < 0.45)
            if rng.random() < 0.30:
                df.at[i, "hour_of_request"] = rng.integers(0, 24)
            df.at[i, "distance_from_home_km"] = round(rng.exponential(40), 1)
        elif a == 1:  # Insider collusion at a retailer
            df.at[i, "attack_type"] = "INSIDER_RETAILER"
            df.at[i, "channel_code"] = 3 if rng.random() < 0.70 else 0
            df.at[i, "kyc_biometric_verified"] = int(rng.random() < 0.90)
            df.at[i, "agent_swaps_24h"] = rng.poisson(13)
            df.at[i, "hour_of_request"] = int(np.clip(round(rng.normal(18, 3)), 0, 23))
            df.at[i, "distance_from_home_km"] = round(rng.exponential(25), 1)
        elif a == 2:  # Forged documents in a store
            df.at[i, "attack_type"] = "FORGED_ID_STORE"
            df.at[i, "channel_code"] = 0
            df.at[i, "kyc_biometric_verified"] = int(rng.random() < 0.75)
            df.at[i, "distance_from_home_km"] = round(
                rng.uniform(20, 600) if rng.random() < 0.6 else rng.exponential(8), 1)
            df.at[i, "profile_change_7d"] = int(rng.random() < 0.25)
            df.at[i, "auth_failures_7d"] = rng.poisson(0.8)
        else:  # Rapid repeat swap on a compromised number
            df.at[i, "attack_type"] = "RAPID_RESWAP"
            df.at[i, "sim_age_days"] = int(rng.integers(1, 21))
            df.at[i, "swaps_last_180d"] = rng.poisson(1.8) + 1
            df.at[i, "auth_failures_7d"] = rng.poisson(1.5)
        df.at[i, "cell_changes_24h"] = rng.poisson(4)
        df.at[i, "roaming_flag"] = int(rng.random() < 0.08)
    return df


def generate_dataset(n=N_SAMPLES, fraud_rate=FRAUD_RATE, seed=SEED) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    n_fraud = int(n * fraud_rate)
    legit = legit_block(rng, n - n_fraud)
    legit["is_fraud"] = 0
    fraud = fraud_block(rng, n_fraud)
    fraud["is_fraud"] = 1
    df = pd.concat([legit, fraud], ignore_index=True)
    df = df.sample(frac=1, random_state=seed).reset_index(drop=True)

    # Timestamps: Jan-Jun 2026, hour taken from the behavioural feature.
    days = rng.integers(0, 181, len(df))
    ts = pd.Timestamp("2026-01-01") + pd.to_timedelta(days, unit="D") \
        + pd.to_timedelta(df["hour_of_request"], unit="h") \
        + pd.to_timedelta(rng.integers(0, 3600, len(df)), unit="s")
    df.insert(0, "request_timestamp", ts.dt.strftime("%Y-%m-%dT%H:%M:%S"))
    df["is_weekend"] = (ts.dt.dayofweek >= 5).astype(int)
    df.insert(0, "request_id", [f"REQ-{i:06d}" for i in range(len(df))])
    df.insert(2, "msisdn", ["+91" + str(m) for m in rng.integers(7_000_000_000, 9_999_999_999, len(df))])
    df.insert(3, "new_imei", [random_imei(rng) for _ in range(len(df))])

    # IMEI blacklist hits (stolen / reported handsets): rare for genuine users.
    p_black = np.where(df["is_fraud"] == 1, np.where(df["attack_type"] == "STEALTH", 0.0, 0.12), 0.002)
    df.insert(4, "imei_blacklisted", (rng.random(len(df)) < p_black).astype(int))
    df.insert(5, "channel", [CHANNELS[c] for c in df["channel_code"]])
    df.insert(6, "agent_id", [f"AGT-{a:03d}" for a in rng.integers(1, 120, len(df))])

    ordered = ["request_id", "request_timestamp", "msisdn", "new_imei", "imei_blacklisted",
               "channel", "agent_id"] + FEATURE_COLS + ["attack_type", "is_fraud"]
    return df[ordered]


if __name__ == "__main__":
    df = generate_dataset()
    DATASET_CSV.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(DATASET_CSV, index=False)
    print(f"Dataset generated: {len(df)} requests -> {DATASET_CSV}")
    print(f"  Legitimate: {(df.is_fraud == 0).sum()}   Fraud: {(df.is_fraud == 1).sum()}"
          f"   Fraud rate: {df.is_fraud.mean():.2%}")
    print("  Attack mix:", df[df.is_fraud == 1].attack_type.value_counts().to_dict())
    print("  IMEI blacklist hits:", df.groupby("is_fraud").imei_blacklisted.sum().to_dict())
