"""
SharedOS Durable Audit Sink & Cloud Outbox Synchronizer
Persists authorization decisions locally to .sharedos/audit_log.jsonl with SHA-256 hash chains,
and delivers batched events to https://www.sharedos.ai/v1/audit/events with bounded timeouts, retries, and preserved IDs.
"""

import hashlib
import json
import os
import sys
import threading
import time
import urllib.error
import urllib.request
import uuid
from typing import Dict, Any, List, Optional


class DurableSharedOSAuditSink:
    """
    Durable AuditSink implementing local append-only persistence (.sharedos/audit_log.jsonl)
    and asynchronous / synchronous batch delivery to SharedOS Cloud audit ingest.
    """

    def __init__(
        self,
        persist_dir: Optional[str] = None,
        cloud_url: str = "https://www.sharedos.ai/v1/audit/events",
        batch_size: int = 50,
        timeout_seconds: float = 4.0,
        max_retries: int = 3
    ):
        self.persist_dir = persist_dir or os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".sharedos")
        os.makedirs(self.persist_dir, exist_ok=True)
        self.log_file = os.path.join(self.persist_dir, "audit_log.jsonl")
        self.outbox_file = os.path.join(self.persist_dir, "audit_outbox.jsonl")
        self.cloud_url = cloud_url
        self.batch_size = batch_size
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.last_hash = "0" * 64
        self._lock = threading.Lock()
        self._init_last_hash()

    def _init_last_hash(self):
        """Initializes the last hash from existing log file if available."""
        if os.path.exists(self.log_file):
            try:
                with open(self.log_file, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            entry = json.loads(line)
                            if "final_hash" in entry:
                                self.last_hash = entry["final_hash"]
                            elif "event_hash" in entry:
                                self.last_hash = entry["event_hash"]
            except Exception:
                pass

    def record_decision(
        self,
        event_type: str,
        context: Dict[str, Any],
        decision: Dict[str, Any],
        request: Optional[Dict[str, Any]] = None,
        event_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Records an authorization or turn decision, computes SHA-256 link, persists locally,
        and enqueues for cloud batch delivery.
        """
        timestamp = time.time()
        iso_time = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(timestamp))
        unique_event_id = event_id or f"evt_{uuid.uuid4().hex[:16]}"
        
        details = {
            "type": event_type,
            "context": context,
            "decision": decision,
            "request": request or {}
        }
        
        payload_str = f"{timestamp}|{event_type}|{json.dumps(details, sort_keys=True)}|{self.last_hash}"
        event_hash = hashlib.sha256(payload_str.encode("utf-8")).hexdigest()

        event_record = {
            "id": unique_event_id,
            "timestamp": timestamp,
            "iso_time": iso_time,
            "type": event_type,
            "previous_hash": self.last_hash,
            "event_hash": event_hash,
            "details": details
        }

        with self._lock:
            self.last_hash = event_hash
            self._append_local_log(event_record)
            self._append_outbox(event_record)

        return event_record

    def _append_local_log(self, record: Dict[str, Any]):
        try:
            with open(self.log_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(record) + "\n")
        except Exception as e:
            print(f"[AuditSink] Error writing to local audit log: {e}", file=sys.stderr)

    def _append_outbox(self, record: Dict[str, Any]):
        try:
            with open(self.outbox_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(record) + "\n")
        except Exception as e:
            print(f"[AuditSink] Error writing to audit outbox: {e}", file=sys.stderr)

    def flush_outbox(self, api_key: Optional[str] = None) -> Dict[str, Any]:
        """
        Reads pending events from the local outbox, batches them, and delivers to SharedOS Cloud.
        Preserves event IDs across retries.
        """
        key = api_key or os.environ.get("SHAREDOS_KEY") or os.environ.get("SHAREDOS_API_KEY", "")
        
        with self._lock:
            if not os.path.exists(self.outbox_file):
                return {"delivered": 0, "pending": 0, "status": "EMPTY"}

            pending_events: List[Dict[str, Any]] = []
            try:
                with open(self.outbox_file, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            pending_events.append(json.loads(line))
            except Exception as e:
                return {"error": f"Failed to read outbox: {e}", "delivered": 0, "status": "READ_ERROR"}

            if not pending_events:
                return {"delivered": 0, "pending": 0, "status": "EMPTY"}

            # If no API key provided, retain outbox locally without failing
            if not key:
                return {"delivered": 0, "pending": len(pending_events), "status": "SKIPPED_NO_API_KEY"}

            # Process in bounded batches
            delivered_count = 0
            failed_events: List[Dict[str, Any]] = []

            for i in range(0, len(pending_events), self.batch_size):
                batch = pending_events[i:i + self.batch_size]
                success = self._send_batch_with_retry(batch, key)
                if success:
                    delivered_count += len(batch)
                else:
                    failed_events.extend(batch)

            # Rewrite outbox with only the remaining unacknowledged events
            try:
                with open(self.outbox_file, "w", encoding="utf-8") as f:
                    for evt in failed_events:
                        f.write(json.dumps(evt) + "\n")
            except Exception as e:
                print(f"[AuditSink] Warning: failed to rewrite outbox: {e}", file=sys.stderr)

            return {
                "delivered": delivered_count,
                "pending": len(failed_events),
                "status": "DELIVERED" if not failed_events else "PARTIAL"
            }

    def _send_batch_with_retry(self, batch: List[Dict[str, Any]], api_key: str) -> bool:
        """
        POSTs a batch to https://www.sharedos.ai/v1/audit/events with bounded timeout and retries.
        Preserves original event IDs.
        """
        payload = json.dumps({"events": batch}).encode("utf-8")
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        for attempt in range(1, self.max_retries + 1):
            try:
                req = urllib.request.Request(self.cloud_url, data=payload, headers=headers, method="POST")
                with urllib.request.urlopen(req, timeout=self.timeout_seconds) as resp:
                    if resp.status in (200, 201, 202):
                        return True
            except urllib.error.HTTPError as e:
                # If 4xx client rejection (e.g. invalid key or schema), log and fail without endless spin
                if 400 <= e.code < 500:
                    print(f"[AuditSink] Cloud ingest rejected batch with status {e.code}: {e.reason}", file=sys.stderr)
                    return False
                # If 5xx server error, backoff and retry
                time.sleep(0.2 * (2 ** (attempt - 1)))
            except Exception as e:
                # Network timeout or DNS failure, backoff and retry
                time.sleep(0.2 * (2 ** (attempt - 1)))

        return False