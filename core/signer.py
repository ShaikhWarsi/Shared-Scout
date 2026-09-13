"""
AgentScout Cryptographic Docket Signer
Generates and maintains Ed25519 keypair for signing Pre-Ship Clearance Dockets.
Provides public key description for independent A2A verification.
"""

from __future__ import annotations

import os
import json
import base64
from pathlib import Path
from typing import Dict, Any, Tuple
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives import serialization

KEYS_FILE = Path(__file__).resolve().parents[1] / ".sharedos" / "ed25519_keys.json"


class DocketSigner:
    def __init__(self):
        self.private_key, self.public_key, self.key_id = self._load_or_generate_keys()

    def _load_or_generate_keys(self) -> Tuple[ed25519.Ed25519PrivateKey, ed25519.Ed25519PublicKey, str]:
        env_priv = os.getenv("AGENTSCOUT_PRIVATE_KEY", "").strip()
        env_pub = os.getenv("AGENTSCOUT_PUBLIC_KEY", "").strip()

        if env_priv and env_pub:
            try:
                priv = serialization.load_pem_private_key(env_priv.encode("utf-8"), password=None)
                pub = serialization.load_pem_public_key(env_pub.encode("utf-8"))
                return priv, pub, "agentscout-prod-key-1"
            except Exception:
                pass

        # Check local persistence file
        if KEYS_FILE.exists():
            try:
                with open(KEYS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                priv_bytes = base64.b64decode(data["private_key_der"])
                pub_bytes = base64.b64decode(data["public_key_der"])
                priv = serialization.load_der_private_key(priv_bytes, password=None)
                pub = serialization.load_der_public_key(pub_bytes)
                return priv, pub, data.get("key_id", "agentscout-local-key-1")
            except Exception:
                pass

        # Generate fresh Ed25519 keypair
        priv = ed25519.Ed25519PrivateKey.generate()
        pub = priv.public_key()
        key_id = "agentscout-ed25519-v1"

        priv_der = priv.private_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        )
        pub_der = pub.public_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )

        try:
            KEYS_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(KEYS_FILE, "w", encoding="utf-8") as f:
                json.dump({
                    "key_id": key_id,
                    "private_key_der": base64.b64encode(priv_der).decode("ascii"),
                    "public_key_der": base64.b64encode(pub_der).decode("ascii")
                }, f, indent=2)
        except Exception:
            pass

        return priv, pub, key_id

    def get_public_key_pem(self) -> str:
        pem = self.public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        return pem.decode("utf-8")

    def get_public_key_description(self) -> Dict[str, Any]:
        return {
            "algorithm": "Ed25519",
            "publicKey": self.get_public_key_pem(),
            "publicKeyFormat": "spki-pem",
            "publicKeyId": self.key_id,
            "trustEnvironment": "production" if os.getenv("AGENTSCOUT_PRIVATE_KEY") else "arena-local",
            "endpoint": "/api/v1/public-key",
            "note": "Official AgentScout Ed25519 verification key for Pre-Ship Clearance Dockets."
        }

    def sign(self, message: bytes) -> str:
        """Signs message bytes and returns hex string signature."""
        sig = self.private_key.sign(message)
        return sig.hex()

    def verify(self, message: bytes, signature_hex: str) -> bool:
        """Verifies signature against public key."""
        try:
            sig_bytes = bytes.fromhex(signature_hex)
            self.public_key.verify(sig_bytes, message)
            return True
        except Exception:
            return False


# Global default signer
signer = DocketSigner()
