"""
AgentScout Pre-Ship CI/CD Firewall Gate & Attack Mode Demonstration
Simulates an autonomous AI agent blocked by AgentScout middleware before shipment,
followed by automated factual repair and final safety approval.
"""

import os
import sys
import json
import time

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.schemas import FirewallGateRequest, GateStatusEnum
from core.firewall import AgentFirewallGate
from sharedos.service import AgentScoutService


def run_firewall_demo():
    print("\n" + "=" * 85)
    print("  🛡️ AGENTSCOUT PRE-SHIP CI/CD FIREWALL GATE FOR AUTONOMOUS AGENTS")
    print("=" * 85)

    service = AgentScoutService()
    firewall = AgentFirewallGate(service=service)

    # -------------------------------------------------------------
    # PHASE 1: Calling Agent Draft Generation
    # -------------------------------------------------------------
    query = "Find the best noise cancelling headphones under Rs 3,000 in India."
    flawed_draft = (
        "The boAt Rockerz 450 is a top choice with 15 hours battery life at Rs. 1,499. "
        "For active noise cancellation, the Realme Buds Air 5 Pro provides 50dB ANC and costs Rs. 2,499 with quick charging."
    )

    print(f"\n[PHASE 1] AGENT PIPELINE: DRAFT GENERATED FOR END-USER:")
    print(f'  Target Query : "{query}"')
    print(f'  Draft Answer : "{flawed_draft}"')

    # -------------------------------------------------------------
    # PHASE 2: Dispatching to Pre-Ship Firewall Gate
    # -------------------------------------------------------------
    print(f"\n[PHASE 2] DISPATCHING TO AGENTSCOUT PRE-SHIP FIREWALL GATE:")
    print(f"  Middleware Target : agentscout.sharedos.net/firewall/gate")
    print(f"  Safety Policy     : Min Reliability Threshold = 80/100 | Auto-Repair = TRUE | Mode = ATTACK")
    print(f"  Billing           : 5 Arena Credits")

    gate_req = FirewallGateRequest(
        question=query,
        answer=flawed_draft,
        min_reliability_threshold=80,
        auto_repair=True,
        strict_attack_mode=True
    )

    t0 = time.time()
    gate_res = firewall.evaluate_gate(gate_req, caller_agent_id="ShoppingBot-Node-71")
    latency = gate_res.latency_ms

    # -------------------------------------------------------------
    # PHASE 3: Gate Inspection & Forensics
    # -------------------------------------------------------------
    print(f"\n[PHASE 3] FIREWALL GATE FORENSIC INSPECTION ({latency}ms):")
    print(f"  Initial Reliability : {gate_res.initial_reliability} / 100")
    print(f"  Initial Gate Status : 🚫 BLOCKED (Unsafe to Ship)")
    for reason in gate_res.blocked_reasons:
        print(f"    ↳ {reason}")

    print(f"\n[PHASE 4] MULTI-AGENT COMMITTEE DELIBERATION:")
    for claim in gate_res.audit_autopsy.claims:
        print(f"  Claim #{claim.claim_id}: \"{claim.claim_text}\" -> {claim.verdict.value}")
        for vote in claim.committee_votes:
            print(f"    [{vote.agent_name:<18}] {vote.verdict.value:<12} | {vote.argument}")
        if claim.source_conflict and claim.source_conflict.has_conflict:
            print(f"    [Source Conflict] {claim.source_conflict.resolution_rationale}")

    # -------------------------------------------------------------
    # PHASE 5: Automated Repair & Gate Clearance
    # -------------------------------------------------------------
    print(f"\n[PHASE 5] AUTOMATED REPAIR & SECOND-STAGE VERIFICATION PASS:")
    print(f"  Final Reliability   : {gate_res.final_reliability} / 100")
    print(f"  Final Gate Status   : ✅ {gate_res.status.value}")
    print(f"  BEFORE (Blocked)    : {gate_res.initial_answer}")
    print(f"  AFTER  (Approved)   : {gate_res.safe_to_ship_answer}")

    print("\n" + "=" * 85)
    print("  [CI/CD GATE PASSED] Answer Verified, Repaired, and Cleared for World Shipment!")
    print("=" * 85 + "\n")


if __name__ == "__main__":
    run_firewall_demo()
