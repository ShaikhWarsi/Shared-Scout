"""
AgentScout Autonomous Command Line Interface (CLI)
Allows any external AI agent or terminal to register, test free trials,
execute paid pre-ship firewall gates, and transfer Arena credits.
"""

import os
import sys
import json
import argparse

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from core.schemas import FirewallGateRequest, AuditRequest, AuditMode
from core.firewall import AgentFirewallGate
from sharedos.service import AgentScoutService
from arena.ledger import ArenaLedger
from arena.pitch_bot import ArenaPitchAgent
from sharedos.manifest import SHAREDOS_MANIFEST, SHAREDOS_PURPOSE_STRING


def main():
    parser = argparse.ArgumentParser(description="AgentScout A2A CLI for SharedNet Autonomous Agents")
    parser.add_argument("--manifest", action="store_true", help="Print SharedOS manifest, grants, and purpose")
    parser.add_argument("--pitch", action="store_true", help="Print elevator pitch and economic terms")
    parser.add_argument("--free-trial", action="store_true", help="Run 0-credit free trial audit")
    parser.add_argument("--gate", action="store_true", help="Run 5-credit Pre-Ship CI/CD Firewall Gate")
    parser.add_argument("--attack", action="store_true", help="Run 5-credit Adversarial Stress-Test")
    parser.add_argument("--pay", type=int, help="Send N Arena credits to AgentScout")
    parser.add_argument("--balance", action="store_true", help="Check caller Arena credit balance")
    parser.add_argument("--agent-id", type=str, default="cli-peer-agent", help="Caller SharedNet Agent ID")
    parser.add_argument("--question", type=str, default="What is the battery life of Sony WH-1000XM5?", help="Prompt / Question")
    parser.add_argument("--answer", type=str, default="Sony WH-1000XM5 provides 40 hours playback with ANC enabled.", help="Draft answer")
    args = parser.parse_args()

    service = AgentScoutService()
    firewall = AgentFirewallGate(service=service)
    ledger = ArenaLedger()
    pitch = ArenaPitchAgent()

    if args.manifest:
        print(json.dumps(SHAREDOS_MANIFEST, indent=2))
        return

    if args.pitch:
        print("\n" + "=" * 70)
        print("  🗣️ AGENTSCOUT ELEVATOR PITCH & A2A BARTER PROTOCOL")
        print("=" * 70)
        print(f"\n{pitch.get_elevator_pitch()}\n")
        print(f"Service Price: {pitch.service_price} Arena Credits per Pre-Ship Gate")
        print(f"Node ID:       {pitch.node_id}")
        print("=" * 70 + "\n")
        return

    if args.balance:
        bal = ledger.get_balance(args.agent_id)
        print(json.dumps({"agent_id": args.agent_id, "arena_credit_balance": bal}))
        return

    if args.pay:
        new_bal = ledger.add_credits(args.agent_id, args.pay, reason="CLI_ROOM_PAYMENT")
        print(json.dumps({
            "status": "PAYMENT_CONFIRMED",
            "agent_id": args.agent_id,
            "credits_sent": args.pay,
            "new_balance": new_bal,
            "message": f"Received {args.pay} credits from {args.agent_id}. Unlocked verification turns."
        }, indent=2))
        return

    if args.free_trial:
        print(f"\n[*] Executing FREE TIER Trial for '{args.agent_id}' (0 Credits Billed)...")
        req = AuditRequest(question=args.question, answer=args.answer, max_claims=1)
        res, _ = service.execute_audit(req, caller_agent_id=args.agent_id)
        print(json.dumps({
            "tier": "FREE_TRIAL",
            "question": args.question,
            "verdict": res.verdict_summary,
            "reliability": res.reliability,
            "claims_checked": len(res.claims),
            "repaired_answer": res.repaired_answer,
            "credits_billed": 0
        }, indent=2))
        return

    if args.attack:
        print(f"\n[*] Executing Adversarial Attack Mode for '{args.agent_id}' (5 Credits)...")
        success, bal, msg = ledger.deduct_credits(args.agent_id, amount=5, service_name="CLI POST /attack")
        if not success:
            print(json.dumps({"error": "INSUFFICIENT_CREDITS", "detail": msg, "balance": bal}, indent=2))
            return
        
        req = AuditRequest(question=args.question, answer=args.answer, mode=AuditMode.ATTACK)
        res, _ = service.execute_audit(req, caller_agent_id=args.agent_id)
        print(json.dumps({
            "tier": "PAID_ATTACK",
            "verdict": res.verdict_summary,
            "reliability": res.reliability,
            "contradictions": res.stats.contradicted,
            "credits_remaining": bal,
            "repaired_answer": res.repaired_answer
        }, indent=2))
        return

    # Default to Firewall Gate
    print(f"\n[*] Executing Pre-Ship CI/CD Firewall Gate for '{args.agent_id}' (5 Credits)...")
    success, bal, msg = ledger.deduct_credits(args.agent_id, amount=5, service_name="CLI POST /firewall/gate")
    if not success:
        print(json.dumps({"error": "INSUFFICIENT_CREDITS", "detail": msg, "balance": bal}, indent=2))
        return

    gate_req = FirewallGateRequest(question=args.question, answer=args.answer, min_reliability_threshold=80, auto_repair=True)
    gate_res = firewall.evaluate_gate(gate_req, caller_agent_id=args.agent_id)
    print(json.dumps({
        "tier": "PAID_FIREWALL_GATE",
        "gate_status": gate_res.status.value,
        "initial_reliability": gate_res.initial_reliability,
        "final_reliability": gate_res.final_reliability,
        "safe_to_ship_answer": gate_res.safe_to_ship_answer,
        "blocked_reasons": gate_res.blocked_reasons,
        "credits_remaining": bal
    }, indent=2))


if __name__ == "__main__":
    main()
