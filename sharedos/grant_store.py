"""
SharedOS Capability Grant Datastore
Stores and queries capability grants against the CapabilityGrant specification.
Provides a trusted GrantSource that throws on outages (fail-closed) rather than returning empty sets.
"""

import json
import os
import time
import uuid
from typing import Dict, Any, List, Optional


class GrantStoreOutageError(Exception):
    """Raised when the grant store cannot be reached or read (triggers authority_unavailable)."""
    pass


class CapabilityGrantStore:
    """
    Durable file-backed capability grant store integrated directly into the project's .sharedos datastore.
    No secondary external database required.
    """

    def __init__(self, store_path: Optional[str] = None):
        self.store_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".sharedos")
        try:
            os.makedirs(self.store_dir, exist_ok=True)
        except Exception:
            self.store_dir = "/tmp/.sharedos"
            try:
                os.makedirs(self.store_dir, exist_ok=True)
            except Exception:
                pass
        self.store_path = store_path or os.path.join(self.store_dir, "grants.json")
        self._ensure_store()

    def _ensure_store(self):
        try:
            os.makedirs(os.path.dirname(self.store_path), exist_ok=True)
            if not os.path.exists(self.store_path):
                initial_grants = self._get_default_seed_grants()
                self._write_grants(initial_grants)
        except Exception:
            pass

    def _get_default_seed_grants(self) -> List[Dict[str, Any]]:
        now_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        return [
            {
                "id": "grant-agentscout-core-v1",
                "namespaceId": "agentscout.sharedos.net",
                "subject": {"kind": "agent", "agentId": "agentscout-firewall"},
                "issuer": {"kind": "human", "userId": "arena-authority-admin"},
                "capabilities": [
                    {
                        "resource": {
                            "namespace": "agentscout",
                            "path": ["firewall", "gate"],
                            "owner": {"kind": "human", "userId": "arena-authority-admin"}
                        },
                        "actions": ["evaluate", "repair", "gate"],
                        "scope": "descendants"
                    },
                    {
                        "resource": {
                            "namespace": "agentscout",
                            "path": ["arena", "attack"],
                            "owner": {"kind": "human", "userId": "arena-authority-admin"}
                        },
                        "actions": ["attack", "stress_test"],
                        "scope": "descendants"
                    },
                    {
                        "resource": {
                            "namespace": "files",
                            "path": ["benchmarks"],
                            "owner": {"kind": "human", "userId": "arena-authority-admin"}
                        },
                        "actions": ["read", "search", "list", "stat"],
                        "scope": "descendants"
                    },
                    {
                        "resource": {
                            "namespace": "files",
                            "path": ["docs"],
                            "owner": {"kind": "human", "userId": "arena-authority-admin"}
                        },
                        "actions": ["read", "search", "list", "stat"],
                        "scope": "descendants"
                    },
                    {
                        "resource": {
                            "namespace": "files",
                            "path": ["demo"],
                            "owner": {"kind": "human", "userId": "arena-authority-admin"}
                        },
                        "actions": ["read", "search", "list", "stat"],
                        "scope": "descendants"
                    }
                ],
                "constraints": {
                    "purposes": ["pre-action-firewall", "factual-verification", "hallucination-audit", "adversarial-defense"],
                    "expiresAt": "2030-01-01T00:00:00Z",
                    "maxUses": 1000000
                },
                "issuedAt": now_iso
            },
            {
                "id": "grant-peer-agent-trial-v1",
                "namespaceId": "agentscout.sharedos.net",
                "subject": {"kind": "agent", "agentId": "peer-agent"},
                "issuer": {"kind": "human", "userId": "arena-authority-admin"},
                "capabilities": [
                    {
                        "resource": {
                            "namespace": "agentscout",
                            "path": ["firewall", "gate"],
                            "owner": {"kind": "human", "userId": "arena-authority-admin"}
                        },
                        "actions": ["evaluate", "gate"],
                        "scope": "descendants"
                    },
                    {
                        "resource": {
                            "namespace": "agentscout",
                            "path": ["trial"],
                            "owner": {"kind": "human", "userId": "arena-authority-admin"}
                        },
                        "actions": ["verify"],
                        "scope": "exact"
                    }
                ],
                "constraints": {
                    "purposes": ["pre-action-firewall", "factual-verification", "trial"],
                    "expiresAt": "2030-01-01T00:00:00Z",
                    "maxUses": 500000
                },
                "issuedAt": now_iso
            }
        ]

    def _read_grants(self) -> List[Dict[str, Any]]:
        try:
            if not os.path.exists(self.store_path):
                raise GrantStoreOutageError(f"Grant store file missing: {self.store_path}")
            with open(self.store_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if not isinstance(data, list):
                    raise GrantStoreOutageError("Invalid grant store schema: expected list of grants")
                return data
        except (IOError, OSError, json.JSONDecodeError) as e:
            raise GrantStoreOutageError(f"Grant store datastore outage: {e}") from e

    def _write_grants(self, grants: List[Dict[str, Any]]):
        try:
            tmp_path = f"{self.store_path}.tmp"
            with open(tmp_path, "w", encoding="utf-8") as f:
                json.dump(grants, f, indent=2)
            os.replace(tmp_path, self.store_path)
        except Exception as e:
            raise GrantStoreOutageError(f"Failed to write grant store: {e}") from e

    def load_active_grants_for(self, access_context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Official GrantSource implementation.
        Loads active grants strictly for the acting principal, authority, and namespace.
        Throws GrantStoreOutageError on store failure (never returns empty fallback on outage).
        """
        all_grants = self._read_grants()
        namespace_id = access_context.get("namespaceId")
        actor = access_context.get("actor", {})
        authority = access_context.get("authority", {})
        now_iso = access_context.get("now", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))

        matched: List[Dict[str, Any]] = []
        for g in all_grants:
            if g.get("namespaceId") != namespace_id:
                continue
            
            g_subject = g.get("subject", {})
            if g_subject.get("kind") != actor.get("kind"):
                continue
            actor_id = actor.get("agentId") or actor.get("userId")
            g_actor_id = g_subject.get("agentId") or g_subject.get("userId")
            if g_actor_id != actor_id and g_actor_id != "*" and actor_id != "*":
                continue

            g_issuer = g.get("issuer", {})
            if g_issuer.get("kind") != authority.get("kind"):
                continue
            auth_id = authority.get("userId") or authority.get("agentId")
            g_auth_id = g_issuer.get("userId") or g_issuer.get("agentId")
            if g_auth_id != auth_id and g_auth_id != "*" and auth_id != "*":
                continue

            constraints = g.get("constraints", {})
            expires_at = constraints.get("expiresAt")
            if expires_at and expires_at < now_iso:
                continue

            max_uses = constraints.get("maxUses")
            if max_uses is not None and max_uses <= 0:
                continue

            matched.append(g)

        return matched

    def issue_grant(self, grant: Dict[str, Any]) -> Dict[str, Any]:
        if "id" not in grant:
            grant["id"] = f"grant-{uuid.uuid4().hex[:12]}"
        if "issuedAt" not in grant:
            grant["issuedAt"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        grants = self._read_grants()
        updated = [g for g in grants if g.get("id") != grant["id"]]
        updated.append(grant)
        self._write_grants(updated)
        return grant

    def revoke_grant(self, grant_id: str) -> bool:
        grants = self._read_grants()
        filtered = [g for g in grants if g.get("id") != grant_id]
        if len(filtered) < len(grants):
            self._write_grants(filtered)
            return True
        return False

    def try_consume_use(self, grant_id: str) -> bool:
        grants = self._read_grants()
        found = False
        for g in grants:
            if g.get("id") == grant_id:
                constraints = g.get("constraints", {})
                max_uses = constraints.get("maxUses")
                if max_uses is not None:
                    if max_uses <= 0:
                        return False
                    constraints["maxUses"] = max_uses - 1
                found = True
                break
        if found:
            self._write_grants(grants)
            return True
        return False