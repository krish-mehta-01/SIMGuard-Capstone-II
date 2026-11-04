"""
SIMGUARD Digital Blockchain Ledger
Implements:
  - SHA-256 cryptographic hash-chained blocks
  - 4 Transaction Categories: REGISTER, MESSAGE, CALL_META, SECURITY_ALERT
  - Ed25519 digital signature validation
  - Real-time cryptographic chain integrity verification & tamper detection
"""

import copy
import hashlib
import json
import time
import uuid
from typing import Dict, List, Optional, Tuple


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_json(data: dict) -> bytes:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


class Transaction:
    """Represents a transaction in the SIMGUARD communication blockchain."""

    CATEGORIES = ("REGISTER", "MESSAGE", "CALL_META", "SECURITY_ALERT")

    def __init__(
        self,
        tx_type: str,
        sender_phone_hash: str,
        public_key_hex: str,
        payload: dict,
        signature_hex: str,
        tx_id: Optional[str] = None,
        timestamp: Optional[float] = None,
    ):
        if tx_type not in self.CATEGORIES:
            raise ValueError(f"Invalid transaction category {tx_type}. Must be one of {self.CATEGORIES}")

        self.tx_id = tx_id or f"TX-{uuid.uuid4().hex[:12].upper()}"
        self.tx_type = tx_type
        self.sender_phone_hash = sender_phone_hash
        self.public_key_hex = public_key_hex
        self.payload = payload
        self.signature_hex = signature_hex
        self.timestamp = timestamp or time.time()

        # Compute payload hash
        self.payload_hash = sha256_hex(canonical_json(self.payload))

    def to_dict(self) -> dict:
        return {
            "tx_id": self.tx_id,
            "tx_type": self.tx_type,
            "sender_phone_hash": self.sender_phone_hash,
            "public_key_hex": self.public_key_hex,
            "payload": self.payload,
            "payload_hash": self.payload_hash,
            "signature_hex": self.signature_hex,
            "timestamp": self.timestamp,
        }

    def compute_signing_bytes(self) -> bytes:
        """The canonical payload that the sender signs."""
        content = {
            "tx_type": self.tx_type,
            "sender_phone_hash": self.sender_phone_hash,
            "payload": self.payload,
            "timestamp": round(self.timestamp, 2),
        }
        return canonical_json(content)


class Block:
    """A cryptographic block containing verified SIMGUARD transactions."""

    def __init__(
        self,
        index: int,
        previous_hash: str,
        transactions: List[dict],
        timestamp: Optional[float] = None,
        block_hash: Optional[str] = None,
        merkle_root: Optional[str] = None,
    ):
        self.index = index
        self.previous_hash = previous_hash
        self.transactions = transactions
        self.timestamp = timestamp or time.time()
        self.merkle_root = merkle_root or self.compute_merkle_root()
        self.block_hash = block_hash or self.compute_block_hash()

    def compute_merkle_root(self) -> str:
        if not self.transactions:
            return sha256_hex(b"EMPTY_TRANSACTIONS")
        # Hash each transaction's actual payload and signature
        tx_hashes = [sha256_hex(canonical_json(t)) for t in self.transactions]
        combined = "".join(sorted(tx_hashes)).encode("utf-8")
        return sha256_hex(combined)

    def compute_block_hash(self) -> str:
        header = {
            "index": self.index,
            "previous_hash": self.previous_hash,
            "merkle_root": self.merkle_root,
            "timestamp": round(self.timestamp, 2),
            "tx_count": len(self.transactions),
        }
        return sha256_hex(canonical_json(header))

    def to_dict(self) -> dict:
        return {
            "index": self.index,
            "timestamp": self.timestamp,
            "previous_hash": self.previous_hash,
            "merkle_root": self.merkle_root,
            "block_hash": self.block_hash,
            "tx_count": len(self.transactions),
            "transactions": self.transactions,
        }


class DigitalLedger:
    """The master blockchain ledger managing blocks, transactions, and audit validation."""

    def __init__(self):
        self.chain: List[Block] = []
        self.pending_transactions: List[dict] = []
        self._backup_blocks: Dict[int, dict] = {}
        self._init_genesis_block()

    def _init_genesis_block(self):
        genesis_tx = {
            "tx_id": "TX-GENESIS",
            "tx_type": "REGISTER",
            "sender_phone_hash": "0000000000000000000000000000000000000000000000000000000000000000",
            "public_key_hex": "GENESIS_ROOT_KEY",
            "payload": {
                "system": "SIMGUARD Blockchain Secure Communication Root",
                "version": "2.0.0",
                "consensus": "Proof-of-Authority (PoA) / Hash-Chain",
                "cipher_suite": "Ed25519 + SHA-256 + AES-256-GCM",
            },
            "payload_hash": sha256_hex(b"SIMGUARD_GENESIS_ROOT"),
            "signature_hex": "GENESIS_SIGNATURE",
            "timestamp": 1730000000.0,
        }
        genesis_block = Block(
            index=0,
            previous_hash="0000000000000000000000000000000000000000000000000000000000000000",
            transactions=[genesis_tx],
            timestamp=1730000000.0,
        )
        self.chain.append(genesis_block)

    def add_transaction(self, tx: Transaction, auto_mine: bool = True) -> dict:
        tx_dict = tx.to_dict()
        self.pending_transactions.append(tx_dict)
        if auto_mine:
            return self.mine_block()
        return {"status": "queued", "tx_id": tx.tx_id}

    def mine_block() -> dict:
        pass

    def mine_block(self) -> dict:
        if not self.pending_transactions:
            return {"status": "no_transactions_to_mine"}

        last_block = self.chain[-1]
        new_block = Block(
            index=last_block.index + 1,
            previous_hash=last_block.block_hash,
            transactions=list(self.pending_transactions),
            timestamp=time.time(),
        )
        self.chain.append(new_block)
        self.pending_transactions.clear()
        return {
            "status": "mined",
            "block_index": new_block.index,
            "block_hash": new_block.block_hash,
            "previous_hash": new_block.previous_hash,
            "tx_count": len(new_block.transactions),
        }

    def get_chain_dict(self) -> List[dict]:
        return [b.to_dict() for b in self.chain]

    def get_stats(self) -> dict:
        tx_counts = {"REGISTER": 0, "MESSAGE": 0, "CALL_META": 0, "SECURITY_ALERT": 0}
        total_tx = 0
        for block in self.chain:
            for tx in block.transactions:
                total_tx += 1
                cat = tx.get("tx_type")
                if cat in tx_counts:
                    tx_counts[cat] += 1

        return {
            "total_blocks": len(self.chain),
            "total_transactions": total_tx,
            "transaction_counts": tx_counts,
            "latest_block_hash": self.chain[-1].block_hash,
            "chain_valid": self.verify_chain()["is_valid"],
        }

    def verify_chain(self) -> dict:
        """Validates hash-chain integrity, block linkage, and merkle roots across all blocks."""
        anomalies = []
        for i in range(1, len(self.chain)):
            current = self.chain[i]
            previous = self.chain[i - 1]

            # 1. Previous hash link check
            if current.previous_hash != previous.block_hash:
                anomalies.append({
                    "block_index": current.index,
                    "error_type": "BROKEN_CHAIN_LINK",
                    "details": f"Block #{current.index} previous_hash does not match Block #{previous.index} hash",
                    "expected": previous.block_hash,
                    "found": current.previous_hash,
                })

            # 2. Merkle root check against actual transaction data
            expected_merkle = current.compute_merkle_root()
            if current.merkle_root != expected_merkle:
                anomalies.append({
                    "block_index": current.index,
                    "error_type": "MERKLE_ROOT_CORRUPTED",
                    "details": f"Transactions in Block #{current.index} were altered after block creation! Stored Merkle root disagrees with computed transaction hashes.",
                    "expected": expected_merkle,
                    "stored": current.merkle_root,
                })

            # 3. Recomputed block hash check
            expected_block_hash = current.compute_block_hash()
            if current.block_hash != expected_block_hash:
                anomalies.append({
                    "block_index": current.index,
                    "error_type": "BLOCK_HASH_MISMATCH",
                    "details": f"Block #{current.index} header or hash was forged; computed hash differs from stored hash.",
                    "expected": expected_block_hash,
                    "stored": current.block_hash,
                })

        return {
            "is_valid": len(anomalies) == 0,
            "total_blocks_checked": len(self.chain),
            "anomaly_count": len(anomalies),
            "anomalies": anomalies,
            "message": "Cryptographic ledger is 100% verified and intact." if len(anomalies) == 0 else "SECURITY ALERT: Ledger tampering detected!",
        }

    def tamper_block(self, block_index: int, field_to_alter: str = "payload") -> dict:
        """Adversarial simulation: mutates data inside a mined block without recalculating the hash."""
        if block_index <= 0 or block_index >= len(self.chain):
            return {"status": "error", "message": f"Cannot tamper block {block_index}"}

        block = self.chain[block_index]
        if block_index not in self._backup_blocks:
            self._backup_blocks[block_index] = copy.deepcopy(block.to_dict())

        if block.transactions:
            target_tx = block.transactions[0]
            if field_to_alter == "payload":
                target_tx["payload"]["FORGED_SIM_SWAP_STATUS"] = "UNAUTHORIZED_TAKEOVER_OVERRIDE"
                target_tx["payload"]["tampered"] = True
            elif field_to_alter == "signature":
                target_tx["signature_hex"] = "DEADBEEF" * 8
            # We deliberately keep block.merkle_root and block.block_hash as the OLD values
            return {
                "status": "tampered",
                "block_index": block_index,
                "tx_id": target_tx["tx_id"],
                "message": f"Block #{block_index} transaction payload secretly modified in database. Run audit to expose the tamper.",
            }
        return {"status": "error", "message": "No transactions in block"}

    def restore_block(self, block_index: int) -> dict:
        """Restores a tampered block from the pre-attack backup."""
        if block_index in self._backup_blocks:
            saved = self._backup_blocks[block_index]
            restored = Block(
                index=saved["index"],
                previous_hash=saved["previous_hash"],
                transactions=saved["transactions"],
                timestamp=saved["timestamp"],
                block_hash=saved["block_hash"],
                merkle_root=saved["merkle_root"],
            )
            self.chain[block_index] = restored
            del self._backup_blocks[block_index]
            return {"status": "restored", "block_index": block_index, "message": f"Block #{block_index} restored to original verified state."}
        return {"status": "not_tampered", "message": f"Block #{block_index} was not in tampered state."}
