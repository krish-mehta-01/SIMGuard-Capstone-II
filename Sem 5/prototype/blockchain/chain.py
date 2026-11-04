"""
On-chain audit service: deploys SIMSwapAuditLog and appends / reads / verifies
entries through web3.py against an Ethereum JSON-RPC node (Ganache locally,
Sepolia or a permissioned network in production - only RPC_URL and the signing
account change).

Canonical hashing
  decision_hash = SHA-256 of canonical JSON (sorted keys, no spaces) of the decision record
  shap_hash     = SHA-256 of canonical JSON of the SHAP explanation
Both are recomputed from the off-chain record during verification.
"""

import hashlib
import hmac
import json
import sys
import time
from pathlib import Path
from typing import Dict, Optional

from web3 import Web3

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from config import CONTRACT_BUILD, DEPLOYMENT_FILE, OPERATOR_HMAC_KEY, RPC_URL  # noqa: E402

DECISION_CODE = {"AUTO_APPROVE": 0, "MANUAL_REVIEW": 1, "AUTO_BLOCK": 2}
DECISION_NAME = {v: k for k, v in DECISION_CODE.items()}


# ───────────────────────── canonical hashing ─────────────────────────

def canonical_json(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def pseudonymise(identifier: str) -> str:
    """HMAC-SHA256 pseudonym (hex). The MSISDN itself never leaves the operator."""
    return hmac.new(OPERATOR_HMAC_KEY, identifier.encode(), hashlib.sha256).hexdigest()


def decision_record(r: Dict) -> Dict:
    """Subset of a stored decision that is covered by the on-chain decision hash."""
    return {
        "request_id": r["request_id"],
        "subscriber_ref": r["subscriber_ref"],
        "decision": r["decision"],
        "risk_score": round(float(r["risk_score"]), 4),
        "ml_probability": round(float(r["ml_probability"]), 6),
        "rule_flags": sorted(r["rule_flags"]),
        "model_version": r["model_version"],
        "timestamp": r["timestamp"],
    }


def shap_record(r: Dict) -> Dict:
    """Explanation covered by the on-chain SHAP hash: the numeric SHAP vector plus
    the feature values it explains, so the readable reasons can be regenerated."""
    return {
        "base_value": round(float(r["base_value"]), 6),
        "contributions": {k: round(float(v), 6) for k, v in sorted(r["contributions"].items())},
        "features": {k: round(float(v), 6) for k, v in sorted(r["features"].items())},
    }


def compute_hashes(r: Dict) -> Dict:
    return {
        "decision_hash": sha256_hex(canonical_json(decision_record(r))),
        "shap_hash": sha256_hex(canonical_json(shap_record(r))),
    }


def b32(hex_str: str) -> bytes:
    return bytes.fromhex(hex_str)


# ───────────────────────────── chain client ─────────────────────────────

class ChainError(RuntimeError):
    pass


class AuditChain:
    def __init__(self, rpc_url: str = RPC_URL, deployment_file: Path = DEPLOYMENT_FILE):
        self.w3 = Web3(Web3.HTTPProvider(rpc_url, request_kwargs={"timeout": 20}))
        if not self.w3.is_connected():
            raise ChainError(f"Cannot reach Ethereum node at {rpc_url}. Start it with: npm run chain")
        with open(CONTRACT_BUILD, encoding="utf-8") as f:
            self.build = json.load(f)
        self.deployment_file = deployment_file
        self.engine_account = self.w3.eth.accounts[0]
        self.contract = self._attach_or_deploy()

    # --- deployment -------------------------------------------------------
    def _attach_or_deploy(self):
        if self.deployment_file.exists():
            info = json.loads(self.deployment_file.read_text(encoding="utf-8"))
            same_chain = info.get("chain_id") == self.w3.eth.chain_id
            if same_chain and self.w3.eth.get_code(info["address"]) not in (b"", b"\x00"):
                return self.w3.eth.contract(address=info["address"], abi=self.build["abi"])
        return self.deploy()

    def deploy(self):
        factory = self.w3.eth.contract(abi=self.build["abi"], bytecode=self.build["bytecode"])
        tx_hash = factory.constructor().transact({"from": self.engine_account})
        receipt = self.w3.eth.wait_for_transaction_receipt(tx_hash)
        info = {
            "address": receipt["contractAddress"],
            "deploy_tx": tx_hash.hex(),
            "deploy_gas_used": receipt["gasUsed"],
            "deployer": self.engine_account,
            "chain_id": self.w3.eth.chain_id,
            "block_number": receipt["blockNumber"],
            "compiler": self.build["compiler"],
            "deployed_bytecode_bytes": self.build["deployedBytecodeSize"],
        }
        self.deployment_file.parent.mkdir(parents=True, exist_ok=True)
        self.deployment_file.write_text(json.dumps(info, indent=2), encoding="utf-8")
        return self.w3.eth.contract(address=receipt["contractAddress"], abi=self.build["abi"])

    @property
    def deployment(self) -> Dict:
        return json.loads(self.deployment_file.read_text(encoding="utf-8"))

    # --- writes -----------------------------------------------------------
    def log_decision(self, subscriber_ref: str, decision: str, risk_score: float,
                     decision_hash: str, shap_hash: str) -> Dict:
        t0 = time.perf_counter()
        tx = self.contract.functions.logDecision(
            b32(subscriber_ref), DECISION_CODE[decision], int(round(risk_score * 10000)),
            b32(decision_hash), b32(shap_hash)
        ).transact({"from": self.engine_account})
        receipt = self.w3.eth.wait_for_transaction_receipt(tx)
        if receipt["status"] != 1:
            raise ChainError("logDecision transaction reverted")
        event = self.contract.events.DecisionLogged().process_receipt(receipt)[0]
        return {
            "entry_id": int(event["args"]["entryId"]),
            "tx_hash": tx.hex() if tx.hex().startswith("0x") else "0x" + tx.hex(),
            "block_number": receipt["blockNumber"],
            "gas_used": receipt["gasUsed"],
            "chain_ms": (time.perf_counter() - t0) * 1000,
        }

    def resolve_review(self, entry_id: int, final_decision: str, analyst_ref: str, note_hash: str) -> Dict:
        tx = self.contract.functions.resolveReview(
            entry_id, DECISION_CODE[final_decision], b32(analyst_ref), b32(note_hash)
        ).transact({"from": self.engine_account})
        receipt = self.w3.eth.wait_for_transaction_receipt(tx)
        if receipt["status"] != 1:
            raise ChainError("resolveReview transaction reverted")
        return {"tx_hash": "0x" + tx.hex().removeprefix("0x"), "block_number": receipt["blockNumber"],
                "gas_used": receipt["gasUsed"]}

    # --- reads ------------------------------------------------------------
    def get_entry(self, entry_id: int) -> Dict:
        e = self.contract.functions.getEntry(entry_id).call()
        return {
            "entry_id": entry_id,
            "subscriber_ref": e[0].hex(),
            "decision_hash": e[1].hex(),
            "shap_hash": e[2].hex(),
            "timestamp": e[3],
            "risk_score": e[4] / 10000,
            "decision": DECISION_NAME[e[5]],
            "logged_by": e[6],
        }

    def get_resolution(self, entry_id: int) -> Optional[Dict]:
        if not self.contract.functions.isResolved(entry_id).call():
            return None
        r = self.contract.functions.getResolution(entry_id).call()
        return {"final_decision": DECISION_NAME[r[0]], "analyst_ref": r[1].hex(),
                "note_hash": r[2].hex(), "timestamp": r[3], "resolved_by": r[4]}

    def stats(self) -> Dict:
        total, approved, review, blocked = self.contract.functions.getStats().call()
        return {"total": total, "AUTO_APPROVE": approved, "MANUAL_REVIEW": review, "AUTO_BLOCK": blocked}

    def chain_info(self) -> Dict:
        d = self.deployment
        return {
            "network": f"Ganache local Ethereum (chain id {self.w3.eth.chain_id})",
            "rpc": self.w3.provider.endpoint_uri,
            "contract": d["address"],
            "latest_block": self.w3.eth.block_number,
            "engine_account": self.engine_account,
            "compiler": d["compiler"],
            "deploy_gas_used": d["deploy_gas_used"],
        }

    def verify_record(self, record: Dict, entry_id: int, on_chain: Optional[Dict] = None) -> Dict:
        """Recompute the hashes from the off-chain record and compare with the anchored ones."""
        h = compute_hashes(record)
        try:
            on_chain = on_chain or self.get_entry(entry_id)
        except Exception as exc:  # unknown entry id etc.
            return {"entry_id": entry_id, "ok": False, "decision_ok": False, "shap_ok": False,
                    "reason": f"no on-chain entry ({exc.__class__.__name__})"}
        decision_ok = on_chain["decision_hash"] == h["decision_hash"]
        shap_ok = on_chain["shap_hash"] == h["shap_hash"]
        problems = []
        if not decision_ok:
            problems.append("decision record hash mismatch")
        if not shap_ok:
            problems.append("SHAP explanation hash mismatch")
        if on_chain["subscriber_ref"] != record["subscriber_ref"]:
            problems.append("subscriber reference mismatch")
        if on_chain["decision"] != record["decision"]:
            problems.append(f"stored decision {record['decision']} differs from on-chain {on_chain['decision']}")
        return {"entry_id": entry_id, "ok": not problems, "decision_ok": decision_ok,
                "shap_ok": shap_ok, "reason": "; ".join(problems)}

    def entry_count(self) -> int:
        return int(self.contract.functions.entryCount().call())
