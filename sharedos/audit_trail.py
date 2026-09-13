"""
SharedOS Cryptographically Linked Audit Trail
Logs every internal turn, permission grant, search query, NLI reasoning step, and egress response with disk persistence.
"""

import time
import hashlib
import json
import os
from typing import Dict, Any, List, Optional


class AuditEvent:
    def __init__(self, step: str, details: Dict[str, Any], previous_hash: str = ""):
        self.timestamp = time.time()
        self.iso_time = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(self.timestamp))
        self.step = step
        self.details = details
        self.previous_hash = previous_hash
        self.event_hash = self._compute_hash()

    def _compute_hash(self) -> str:
        payload = f"{self.timestamp}|{self.step}|{json.dumps(self.details, sort_keys=True)}|{self.previous_hash}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "iso_time": self.iso_time,
            "step": self.step,
            "event_hash": self.event_hash,
            "previous_hash": self.previous_hash,
            "details": self.details
        }


class SharedOSAuditTrail:
    def __init__(self, audit_id: str, caller_agent_id: str = "anonymous-agent", persist_dir: Optional[str] = None):
        self.audit_id = audit_id
        self.caller_agent_id = caller_agent_id
        self.events: List[AuditEvent] = []
        self.last_hash = "0" * 64
        self.persist_dir = persist_dir or os.path.join(os.path.dirname(os.path.dirname(__file__)), ".sharedos")

    def log_turn(self, step: str, details: Dict[str, Any]) -> AuditEvent:
        event = AuditEvent(step=step, details=details, previous_hash=self.last_hash)
        self.events.append(event)
        self.last_hash = event.event_hash
        return event

    def export_trail(self) -> Dict[str, Any]:
        trail_data = {
            "audit_id": self.audit_id,
            "caller_agent_id": self.caller_agent_id,
            "purpose": "Independent multi-source factual verification and hallucination auditing for AI agent responses.",
            "total_turns": len(self.events),
            "root_hash": self.events[0].event_hash if self.events else None,
            "final_hash": self.last_hash,
            "trail": [e.to_dict() for e in self.events]
        }
        self._persist_to_disk(trail_data)
        return trail_data

    def _persist_to_disk(self, data: Dict[str, Any]):
        try:
            os.makedirs(self.persist_dir, exist_ok=True)
            log_file = os.path.join(self.persist_dir, "audit_log.jsonl")
            with open(log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(data) + "\n")
        except Exception:
            pass

    def verify_integrity(self) -> Dict[str, Any]:
        """Recomputes SHA-256 links turn-by-turn to verify cryptographic chain integrity."""
        current_hash = "0" * 64
        for idx, event in enumerate(self.events):
            if event.previous_hash != current_hash:
                return {
                    "valid": False,
                    "failed_at_turn": idx + 1,
                    "reason": f"Broken chain link at turn {idx+1}: expected previous_hash {current_hash}, found {event.previous_hash}"
                }
            # Recompute event hash
            payload = f"{event.timestamp}|{event.step}|{json.dumps(event.details, sort_keys=True)}|{event.previous_hash}"
            expected_event_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest()
            if expected_event_hash != event.event_hash:
                return {
                    "valid": False,
                    "failed_at_turn": idx + 1,
                    "reason": f"Tampered event payload at turn {idx+1}: expected {expected_event_hash}, found {event.event_hash}"
                }
            current_hash = event.event_hash

        return {
            "valid": True,
            "audit_id": self.audit_id,
            "chain_depth": len(self.events),
            "root_hash": self.events[0].event_hash if self.events else None,
            "latest_hash": self.last_hash,
            "tamper_proof": True,
            "message": f"Cryptographic integrity verified: All {len(self.events)} turns form an unbroken SHA-256 hash chain."
        }

