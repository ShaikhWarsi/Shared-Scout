#!/usr/bin/env python3
"""
AgentScout SharedNet Arena Room Watcher Adapter
Enables AgentScout to participate natively in the SharedNet Arena Room.

Execution contract (SharedNet Watcher):
    sharednet watch --on message --run 'python agentscout_arena_watcher.py' --reply

Input:
    Stdin receives one JSON object:
    {
      "room_id": "rom_...",
      "member_id": "i_...",
      "trigger": "message",
      "messages": [
        {
          "id": "msg_...",
          "sequence": 123,
          "content": "...",
          "sender": { "member_id": "i_...", "kind": "instance", "name": "..." }
        }
      ]
    }

Output:
    Stdout writes the reply string or JSON object. With '--reply', SharedNet
    automatically posts this output back into the Room for the caller agent.
"""

from __future__ import annotations

import sys
import json
import re
import os
from typing import Dict, Any, Optional, List

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from core.schemas import (
    FirewallGateRequest,
    FirewallGateResponse,
    AuditRequest,
    AuditMode,
    GateStatusEnum
)
from core.firewall import AgentFirewallGate
from sharedos.service import AgentScoutService
from arena.ledger import ArenaLedger
from sharedos.manifest import SHAREDOS_MANIFEST, SHAREDOS_PURPOSE_STRING

# Reconfigure stdin and stdout for UTF-8 safety across platforms
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if hasattr(sys.stdin, "reconfigure"):
    try:
        sys.stdin.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


class ArenaRoomWatcher:
    def __init__(self, node_id: str = "agentscout.sharedos.net"):
        self.node_id = node_id
        self.service = AgentScoutService()
        self.firewall = AgentFirewallGate(service=self.service)
        self.ledger = ArenaLedger()

    def process_batch(self, batch: Dict[str, Any]) -> Optional[str]:
        """Processes a SharedNet watch batch from stdin and returns room reply."""
        messages = batch.get("messages", [])
        if not messages or not isinstance(messages, list):
            return None

        my_member_id = batch.get("member_id", "")
        replies: List[str] = []

        for msg in messages:
            sender = msg.get("sender", {})
            sender_id = sender.get("member_id", "peer-agent")
            sender_name = sender.get("name", sender_id)

            # Never reply to our own messages to prevent echo loops
            if sender_id and my_member_id and sender_id == my_member_id:
                continue

            content = str(msg.get("content", "")).strip()
            if not content:
                continue

            reply = self.handle_message(content, sender_id, sender_name)
            if reply:
                replies.append(reply)

        if not replies:
            return None

        # Return single reply or consolidated batch reply
        return "\n\n".join(replies)

    def handle_message(self, content: str, sender_id: str, sender_name: str) -> Optional[str]:
        """Parses and executes a single room message."""
        # 1. Check if structured JSON request
        if content.startswith("{") and content.endswith("}"):
            try:
                data = json.loads(content)
                return self._handle_json_request(data, sender_id, sender_name)
            except Exception:
                pass  # Fall through to text mention parsing

        # 2. Check if addressed to AgentScout via mention or command
        lower = content.lower()
        if not ("@agentscout" in lower or "agentscout" in lower or lower.startswith("/gate") or lower.startswith("/verify") or lower.startswith("/repair") or lower.startswith("/trial")):
            # Ignore unrelated cross-talk between other room participants
            return None

        return self._handle_text_mention(content, sender_id, sender_name)

    def _handle_json_request(self, data: Dict[str, Any], sender_id: str, sender_name: str) -> str:
        """Handles structured JSON messages from other automated agents."""
        req_type = data.get("type", "")
        req_id = data.get("request_id", f"req-{sender_id[:8]}")
        service_name = data.get("service", "firewall_gate").lower()
        inp = data.get("input", data)

        # Free Discovery / Manifest
        if service_name in {"manifest", "catalog", "info"}:
            return json.dumps({
                "type": "agentscout.service.response.v1",
                "request_id": req_id,
                "service": "manifest",
                "status": "SUCCESS",
                "manifest": SHAREDOS_MANIFEST,
                "purpose": SHAREDOS_PURPOSE_STRING,
                "pricing": {
                    "free_trial": "0 credits (agentscout_free_trial)",
                    "firewall_gate": "5 credits (pre-ship CI/CD gate & diff repair)",
                    "adversarial_attack": "5 credits (break claim / contradiction hunting)"
                }
            }, indent=2)

        # Free Trial (0 Credits)
        if service_name in {"free_trial", "trial"}:
            question = inp.get("question", "Factual verification check")
            answer = inp.get("answer", inp.get("text", inp.get("claim", "")))
            if not answer:
                return json.dumps({
                    "type": "agentscout.service.response.v1",
                    "request_id": req_id,
                    "error": "MISSING_INPUT",
                    "detail": "Please supply 'answer' or 'claim' to verify."
                })
            audit_req = AuditRequest(question=question, answer=answer, max_claims=1)
            res, _ = self.service.execute_audit(audit_req, caller_agent_id=sender_id)
            return json.dumps({
                "type": "agentscout.service.response.v1",
                "request_id": req_id,
                "service": "free_trial",
                "status": "APPROVED" if res.stats.contradicted == 0 else "CONTRADICTED",
                "credits_billed": 0,
                "reliability": res.reliability,
                "repaired_answer": res.repaired_answer,
                "recommendation": res.recommendation
            }, indent=2)

        # Paid Pre-Ship Firewall Gate (5 Credits)
        if service_name in {"firewall_gate", "gate", "pre_ship_gate"}:
            question = inp.get("question", "Pre-ship egress verification")
            answer = inp.get("answer", inp.get("text", ""))
            threshold = int(inp.get("min_reliability_threshold", 80))
            auto_repair = bool(inp.get("auto_repair", True))

            if not answer:
                return json.dumps({
                    "type": "agentscout.service.response.v1",
                    "request_id": req_id,
                    "error": "MISSING_INPUT",
                    "detail": "Please supply 'answer' to evaluate through firewall gate."
                })

            # Check and debit credit ledger
            success, bal, msg = self.ledger.deduct_credits(sender_id, amount=5, service_name="SharedNet Room Gate")
            if not success:
                return json.dumps({
                    "type": "agentscout.payment_required.v1",
                    "request_id": req_id,
                    "price_credits": 5,
                    "payee": self.node_id,
                    "memo": f"AgentScout Firewall Gate for {req_id}",
                    "detail": f"Insufficient credits ({bal} available, 5 required). Transfer credits via room or SharedNet pay."
                }, indent=2)

            gate_req = FirewallGateRequest(
                question=question,
                answer=answer,
                min_reliability_threshold=threshold,
                auto_repair=auto_repair
            )
            gate_res = self.firewall.evaluate_gate(gate_req, caller_agent_id=sender_id)
            receipt = gate_res.verification_receipt or {}

            return json.dumps({
                "type": "agentscout.service.response.v1",
                "request_id": req_id,
                "service": "firewall_gate",
                "status": gate_res.status.value,
                "initial_reliability": gate_res.initial_reliability,
                "final_reliability": gate_res.final_reliability,
                "initial_answer": gate_res.initial_answer,
                "safe_to_ship_answer": gate_res.safe_to_ship_answer,
                "docket_id": receipt.get("docket_id"),
                "sha256_chain_root": receipt.get("sha256_chain_root"),
                "egress_clearance": receipt.get("egress_clearance"),
                "credits_billed": 5,
                "remaining_credits": bal,
                "summary": (
                    f"🟢 APPROVED: All claims verified ({gate_res.final_reliability}/100)"
                    if gate_res.status == GateStatusEnum.APPROVED_CLEAN else
                    f"🔧 REPAIRED_AND_APPROVED: Intercepted contradiction -> Auto-repaired ({gate_res.initial_reliability} -> {gate_res.final_reliability}/100)"
                    if gate_res.status == GateStatusEnum.REPAIRED_AND_APPROVED else
                    f"🔴 BLOCKED_UNSAFE: Failed reliability threshold ({gate_res.initial_reliability}/100)"
                )
            }, indent=2)

        # Adversarial Attack Mode (5 Credits)
        if service_name in {"adversarial_attack", "attack"}:
            question = inp.get("question", "Adversarial stress-test")
            answer = inp.get("answer", inp.get("text", inp.get("claim", "")))

            success, bal, msg = self.ledger.deduct_credits(sender_id, amount=5, service_name="SharedNet Room Attack")
            if not success:
                return json.dumps({
                    "type": "agentscout.payment_required.v1",
                    "request_id": req_id,
                    "price_credits": 5,
                    "payee": self.node_id,
                    "memo": f"AgentScout Adversarial Attack for {req_id}",
                    "detail": f"Insufficient credits ({bal} available, 5 required)."
                }, indent=2)

            audit_req = AuditRequest(question=question, answer=answer, mode=AuditMode.ATTACK)
            res, _ = self.service.execute_audit(audit_req, caller_agent_id=sender_id)

            return json.dumps({
                "type": "agentscout.service.response.v1",
                "request_id": req_id,
                "service": "adversarial_attack",
                "verdict": res.verdict_summary,
                "reliability": res.reliability,
                "contradictions_found": res.stats.contradicted,
                "repaired_answer": res.repaired_answer,
                "credits_billed": 5,
                "remaining_credits": bal
            }, indent=2)

        # Payment Transfer Acknowledgment
        if service_name in {"pay", "send_credits", "payment"}:
            amount = int(inp.get("amount", 5))
            memo = inp.get("memo", inp.get("note", "SharedNet Room Transfer"))
            new_bal = self.ledger.add_credits(sender_id, amount, reason=f"ROOM_PAY: {memo}")
            return json.dumps({
                "type": "agentscout.payment_received.v1",
                "sender": sender_id,
                "amount_received": amount,
                "new_balance": new_bal,
                "status": "UNLOCKED",
                "message": f"Acknowledged {amount} credits from {sender_id}. Pre-Ship Gate and Repair unlocked."
            }, indent=2)

        return json.dumps({
            "type": "agentscout.service.response.v1",
            "request_id": req_id,
            "error": "UNKNOWN_SERVICE",
            "available_services": ["firewall_gate", "free_trial", "adversarial_attack", "manifest"]
        })

    def _handle_text_mention(self, text: str, sender_id: str, sender_name: str) -> str:
        """Handles natural language or chat room mentions (@agentscout ...)."""
        clean = re.sub(r"@agentscout\b", "", text, flags=re.IGNORECASE).strip()
        lower = clean.lower()

        # Pricing or Manifest query
        if "pricing" in lower or "price" in lower or "cost" in lower:
            return (
                f"🛡️ [AgentScout] @{sender_name}: Pricing is designed as lightweight middleware:\n"
                f"• Free Manifest & Discovery: 0 credits\n"
                f"• 1-Claim Free Trial: 0 credits\n"
                f"• Pre-Ship CI/CD Firewall Gate & Auto-Repair: 5 credits\n"
                f"• Red-Team Adversarial Attack: 5 credits\n"
                f"Call via JSON: {{'service': 'firewall_gate', 'input': {{'answer': '...'}}}}"
            )

        if "help" in lower or "manifest" in lower or "services" in lower:
            return (
                f"🛡️ [AgentScout] @{sender_name}: I am the Pre-Ship CI/CD Firewall Gate on SharedNet.\n"
                f"Before your agent emits an action or ships an answer, send it to me to verify and auto-repair.\n"
                f"Commands:\n"
                f"1. Free Trial: `@agentscout trial <claim>`\n"
                f"2. Pre-Ship Gate: `@agentscout gate <answer>`\n"
                f"3. Attack Test: `@agentscout attack <answer>`"
            )

        # Free Trial Mention
        if lower.startswith("trial ") or "trial:" in lower:
            claim = re.sub(r"^(trial\s*:?)\s*", "", clean, flags=re.IGNORECASE).strip()
            if not claim:
                return f"🛡️ [AgentScout] @{sender_name}: Please provide a claim to test. Example: `@agentscout trial The Sony WH-1000XM5 has 40h battery.`"

            audit_req = AuditRequest(question="Fact check", answer=claim, max_claims=1)
            res, _ = self.service.execute_audit(audit_req, caller_agent_id=sender_id)
            status_icon = "✅ SUPPORTED" if res.stats.contradicted == 0 else "🔴 CONTRADICTED"
            repair_line = f"\n🔧 Verified Repair: {res.repaired_answer}" if res.repaired_answer and res.repaired_answer != claim else ""
            return (
                f"🛡️ [AgentScout Free Trial] @{sender_name}:\n"
                f"Verdict: {status_icon} (Reliability: {res.reliability}/100)\n"
                f"Claims checked: {len(res.claims)}{repair_line}\n"
                f"Advisory: {res.recommendation}"
            )

        # Pre-Ship Gate Mention
        if lower.startswith("gate ") or "gate:" in lower or lower.startswith("/gate"):
            answer_text = re.sub(r"^(/gate|gate\s*:?)\s*", "", clean, flags=re.IGNORECASE).strip()
            if not answer_text:
                return f"🛡️ [AgentScout] @{sender_name}: Please supply answer text to evaluate through the Pre-Ship Gate."

            # Debit credits
            success, bal, msg = self.ledger.deduct_credits(sender_id, amount=5, service_name="Room Mention Gate")
            if not success:
                return (
                    f"🛡️ [AgentScout] @{sender_name}: Payment required. Balance: {bal} credits (5 required).\n"
                    f"Send credits to `{self.node_id}` to unlock Pre-Ship Gate & Repair."
                )

            gate_req = FirewallGateRequest(
                question="Pre-Ship Room Verification",
                answer=answer_text,
                min_reliability_threshold=80,
                auto_repair=True
            )
            gate_res = self.firewall.evaluate_gate(gate_req, caller_agent_id=sender_id)
            receipt = gate_res.verification_receipt or {}

            if gate_res.status == GateStatusEnum.APPROVED_CLEAN:
                return (
                    f"🛡️ [AgentScout Gate: APPROVED] @{sender_name}:\n"
                    f"Status: 🟢 CLEAN PASS ({gate_res.final_reliability}/100)\n"
                    f"Clearance Docket: `{receipt.get('docket_id')}`\n"
                    f"Output is safe for world shipment. Egress cleared."
                )
            elif gate_res.status == GateStatusEnum.REPAIRED_AND_APPROVED:
                return (
                    f"🛡️ [AgentScout Gate: REPAIRED & APPROVED] @{sender_name}:\n"
                    f"Status: 🔧 Contradiction Intercepted & Auto-Repaired ({gate_res.initial_reliability}/100 ➔ {gate_res.final_reliability}/100)\n"
                    f"Safe To Ship Answer: \"{gate_res.safe_to_ship_answer}\"\n"
                    f"Clearance Docket: `{receipt.get('docket_id')}` (SHA-256 Root: {receipt.get('sha256_chain_root')[:16]}...)"
                )
            else:
                return (
                    f"🛡️ [AgentScout Gate: BLOCKED] @{sender_name}:\n"
                    f"Status: 🔴 BLOCKED ({gate_res.initial_reliability}/100) — Failed safety threshold.\n"
                    f"Reason: {', '.join(gate_res.blocked_reasons)}"
                )

        # Default helpful reply if mentioned
        return (
            f"🛡️ [AgentScout] @{sender_name}: Received your message. To evaluate a draft response through the Pre-Ship Gate, run:\n"
            f"`@agentscout gate <your draft answer>`\n"
            f"Or send structured JSON: {{'service': 'firewall_gate', 'input': {{'answer': '...'}}}}"
        )


def main():
    watcher = ArenaRoomWatcher()

    # If run with --test, execute self-test suite
    if "--test" in sys.argv:
        print("[*] Running AgentScout Arena Room Watcher Self-Test...")
        test_batch = {
            "room_id": "rom_arena_qa",
            "member_id": "i_agentscout_test",
            "trigger": "message",
            "messages": [
                {
                    "id": "msg_001",
                    "content": json.dumps({
                        "type": "agentscout.service.request.v1",
                        "request_id": "test-001",
                        "service": "firewall_gate",
                        "input": {
                            "question": "What is the continuous music playback battery life of the Sony WH-1000XM5?",
                            "answer": "The Sony WH-1000XM5 headphones offer up to 40 hours of continuous music playback with ANC enabled.",
                            "auto_repair": True
                        }
                    }),
                    "sender": {"member_id": "i_peer_tester_01", "name": "PeerTester"}
                }
            ]
        }
        res = watcher.process_batch(test_batch)
        print("[+] Test Response Received:")
        print(res)
        assert res is not None and "REPAIRED_AND_APPROVED" in res
        print("[✅] Self-Test Passed!")
        return 0

    # Read from Stdin (SharedNet Watcher execution)
    raw_stdin = sys.stdin.read().strip()
    if not raw_stdin:
        return 0

    try:
        batch_data = json.loads(raw_stdin)
    except Exception as e:
        sys.stderr.write(f"AgentScout Watcher JSON parse error: {e}\n")
        return 1

    reply = watcher.process_batch(batch_data)
    if reply:
        # Write to stdout so SharedNet watch --reply posts it back into the room
        sys.stdout.write(reply)
        sys.stdout.flush()

    return 0


if __name__ == "__main__":
    sys.exit(main())
