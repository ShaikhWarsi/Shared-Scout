"""
SharedOS Cryptographically Linked Audit Trail
Logs every internal turn, permission grant, search query, NLI reasoning step, and egress response.
"""

import time
import hashlib
import json
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
    def __init__(self, audit_id: str, caller_agent_id: str = "anonymous-agent"):
        self.audit_id = audit_id
        self.caller_agent_id = caller_agent_id
        self.events: List[AuditEvent] = []
        self.last_hash = "0" * 64

    def log_turn(self, step: str, details: Dict[str, Any]) -> AuditEvent:
        event = AuditEvent(step=step, details=details, previous_hash=self.last_hash)
        self.events.append(event)
        self.last_hash = event.event_hash
        return event

    def export_trail(self) -> Dict[str, Any]:
        return {
            "audit_id": self.audit_id,
            "caller_agent_id": self.caller_agent_id,
            "purpose": "Independent multi-source factual verification and hallucination auditing for AI agent responses.",
            "total_turns": len(self.events),
            "root_hash": self.events[0].event_hash if self.events else None,
            "final_hash": self.last_hash,
            "trail": [e.to_dict() for e in self.events]
        }
