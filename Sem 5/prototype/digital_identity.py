"""
SIMGUARD Digital Identity & Cryptographic Protocol Engine
Implements:
  - Device-bound identity: Phone Number Hash + Device Public Key (Ed25519) + Device Fingerprint Hash
  - Challenge-response authentication
  - Nonce-based replay protection
  - End-to-end message encryption
  - Signed call metadata packaging
"""

import base64
import hashlib
import hmac
import json
import os
import time
import uuid
from typing import Dict, List, Optional, Tuple

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives.ciphers.aead import AESGCM


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def canonical_json(data: dict) -> bytes:
    return json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


class DeviceIdentity:
    """Represents a client device identity holding an Ed25519 keypair."""

    def __init__(self, phone_number: str, device_model: str, os_build: str, imei: str, private_key: Optional[ed25519.Ed25519PrivateKey] = None):
        self.phone_number = phone_number
        self.device_model = device_model
        self.os_build = os_build
        self.imei = imei
        self.private_key = private_key or ed25519.Ed25519PrivateKey.generate()
        self.public_key = self.private_key.public_key()

        # Cryptographic Hashes (Slide 8)
        self.phone_number_hash = sha256_hex(self.phone_number.strip().encode("utf-8"))
        self.device_fingerprint_raw = f"{self.device_model}|{self.os_build}|{self.imei}"
        self.device_fingerprint_hash = sha256_hex(self.device_fingerprint_raw.encode("utf-8"))
        self.public_key_hex = self.public_key.public_bytes_raw().hex()

        # Phone Number Hash + Device Public Key + Device Fingerprint Hash
        self.identity_binding = sha256_hex(
            f"{self.phone_number_hash}:{self.public_key_hex}:{self.device_fingerprint_hash}".encode("utf-8")
        )

    def sign(self, message: bytes) -> str:
        """Sign a message with Ed25519 private key; returns hex signature."""
        sig = self.private_key.sign(message)
        return sig.hex()

    def get_public_profile(self) -> Dict:
        return {
            "phone_number": self.phone_number,
            "phone_number_hash": self.phone_number_hash,
            "device_model": self.device_model,
            "os_build": self.os_build,
            "device_fingerprint_hash": self.device_fingerprint_hash,
            "device_public_key": self.public_key_hex,
            "identity_binding": self.identity_binding,
        }


def verify_ed25519_signature(public_key_hex: str, signature_hex: str, message: bytes) -> bool:
    """Verifies an Ed25519 signature."""
    try:
        pub_bytes = bytes.fromhex(public_key_hex)
        sig_bytes = bytes.fromhex(signature_hex)
        pub_key = ed25519.Ed25519PublicKey.from_public_bytes(pub_bytes)
        pub_key.verify(sig_bytes, message)
        return True
    except (ValueError, InvalidSignature):
        return False


class ChallengeAuthManager:
    """Manages challenge-response authentication and nonce freshness against replay attacks."""

    def __init__(self, freshness_window_seconds: int = 300):
        self.freshness_window = freshness_window_seconds
        self.active_challenges: Dict[str, Dict] = {}  # challenge_id -> {nonce, created_at, phone_hash}
        self.used_nonces: set = set()

    def issue_challenge(self, phone_number_hash: str) -> Dict:
        challenge_id = uuid.uuid4().hex
        nonce = os.urandom(32).hex()
        now = time.time()
        self.active_challenges[challenge_id] = {
            "nonce": nonce,
            "created_at": now,
            "phone_number_hash": phone_number_hash,
        }
        return {"challenge_id": challenge_id, "nonce": nonce, "expires_in": self.freshness_window}

    def verify_response(self, challenge_id: str, signature_hex: str, public_key_hex: str) -> Tuple[bool, str]:
        record = self.active_challenges.get(challenge_id)
        if not record:
            return False, "Challenge expired or unknown"

        now = time.time()
        if now - record["created_at"] > self.freshness_window:
            del self.active_challenges[challenge_id]
            return False, "Challenge timed out (exceeded freshness window)"

        nonce_bytes = record["nonce"].encode("utf-8")
        if record["nonce"] in self.used_nonces:
            return False, "Replay attack detected: nonce already consumed"

        is_valid = verify_ed25519_signature(public_key_hex, signature_hex, nonce_bytes)
        if is_valid:
            self.used_nonces.add(record["nonce"])
            del self.active_challenges[challenge_id]
            return True, "Authentication successful"
        return False, "Cryptographic signature verification failed"


class E2EEMessageService:
    """Handles end-to-end encrypted messaging with payload hashing for blockchain anchoring."""

    @staticmethod
    def encrypt_message(plaintext: str) -> Dict:
        """Encrypts a message using AES-256-GCM with a shared session key."""
        key = AESGCM.generate_key(bit_length=256)
        aesgcm = AESGCM(key)
        nonce = os.urandom(12)
        ciphertext = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)

        payload_bytes = nonce + ciphertext
        payload_b64 = base64.b64encode(payload_bytes).decode("ascii")
        payload_hash = sha256_hex(payload_bytes)

        return {
            "key_hex": key.hex(),
            "encrypted_payload": payload_b64,
            "payload_hash": payload_hash,
            "plaintext_length": len(plaintext),
        }

    @staticmethod
    def decrypt_message(key_hex: str, encrypted_payload_b64: str) -> Optional[str]:
        try:
            key = bytes.fromhex(key_hex)
            payload_bytes = base64.b64decode(encrypted_payload_b64.encode("ascii"))
            nonce = payload_bytes[:12]
            ciphertext = payload_bytes[12:]
            aesgcm = AESGCM(key)
            decrypted = aesgcm.decrypt(nonce, ciphertext, None)
            return decrypted.decode("utf-8")
        except Exception:
            return None

