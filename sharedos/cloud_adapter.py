"""
SharedOS Gateway Adapter & HMAC-SHA256 Turn Authorization
Enforces cryptographic token verification on incoming A2A calls and tracks kernel turn synchronizations.
"""

import time
import hmac
import hashlib
import json
import os
import urllib.request
import urllib.parse
from typing import Dict, Any, Optional, List
from sharedos.manifest import SHAREDOS_MANIFEST, SHAREDOS_PURPOSE_STRING


class SharedOSCloudAdapter:
    def __init__(self, node_id: str = "agentscout.sharedos.net"):
        self.node_id = node_id
        self.purpose = SHAREDOS_PURPOSE_STRING
        self.secret_key = os.getenv("SHAREDOS_SECRET_KEY", "sharedos_production_secret_key_v1")
        self.enforce_hmac = os.getenv("SHAREDOS_ENFORCE_HMAC", "true").lower() in {"true", "1", "yes"}
        self.connected_since = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        self.active_turns_synced = 0
        self.seed_peers = [
            p.strip() for p in os.getenv("SHAREDOS_SEED_NODES", "http://localhost:8001,http://localhost:8002").split(",") if p.strip()
        ]
        self.registered_peers: Dict[str, Dict[str, Any]] = {}

    def verify_turn_authorization(self, headers: Dict[str, str], raw_body: bytes = b"") -> Dict[str, Any]:
        caller = headers.get("x-sharedos-agent-id", "arena-peer-agent")
        signature = headers.get("x-sharedos-signature", "")
        
        # Cryptographic HMAC-SHA256 signature verification
        is_valid_sig = True
        if signature:
            expected = hmac.new(self.secret_key.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()
            is_valid_sig = hmac.compare_digest(signature, expected)
        elif self.enforce_hmac:
            is_valid_sig = False

        self.active_turns_synced += 1
        return {
            "authorized": is_valid_sig,
            "hmac_verified": is_valid_sig and bool(signature),
            "caller_agent_id": caller,
            "purpose": self.purpose,
            "grants": SHAREDOS_MANIFEST["grants"],
            "kernel_turn_index": self.active_turns_synced
        }

    def generate_signature(self, raw_body: bytes) -> str:
        """Utility for calling agents to sign their payloads."""
        return hmac.new(self.secret_key.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()

    def get_auth_headers(self, agent_id: str, raw_body: bytes) -> Dict[str, str]:
        """Generates full authenticated SharedNet request headers."""
        return {
            "x-sharedos-agent-id": agent_id,
            "x-sharedos-signature": self.generate_signature(raw_body),
            "Content-Type": "application/json"
        }

    def dial_peer_node(self, peer_url: str, endpoint: str = "/purpose") -> Dict[str, Any]:
        """Dials outbound SharedNet peer node with cryptographic HMAC handshake."""
        target_url = peer_url.rstrip("/") + endpoint
        dummy_payload = json.dumps({"dialer_node": self.node_id, "timestamp": time.time()}).encode("utf-8")
        headers = self.get_auth_headers(self.node_id, dummy_payload)
        
        try:
            req = urllib.request.Request(target_url, headers=headers)
            with urllib.request.urlopen(req, timeout=2.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                peer_id = data.get("agent_id", peer_url)
                self.registered_peers[peer_id] = {
                    "url": peer_url,
                    "status": "REACHABLE",
                    "last_seen": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "info": data
                }
                return {"status": "SUCCESS", "peer_id": peer_id, "data": data}
        except Exception as e:
            return {"status": "UNREACHABLE", "peer_url": peer_url, "error": str(e)}

    def register_peer(self, peer_id: str, peer_url: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Registers a discovered peer node in the local SharedNet topology."""
        self.registered_peers[peer_id] = {
            "url": peer_url,
            "status": "REGISTERED",
            "last_seen": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "metadata": metadata or {}
        }
        return self.registered_peers[peer_id]

    def get_node_status(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "status": "ONLINE_ACTIVE",
            "protocol": "SharedNet/1.0",
            "purpose": self.purpose,
            "service": "audit",
            "price_credits": 5,
            "connected_since": self.connected_since,
            "turns_synced": self.active_turns_synced,
            "hmac_enforced": self.enforce_hmac,
            "sandbox_isolated": True,
            "kernel_audit_compliant": True,
            "peer_nodes_count": len(self.registered_peers),
            "seed_peers": self.seed_peers
        }
