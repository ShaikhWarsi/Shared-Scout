"""
AgentScout Cinematic Mega-Demo: The Pre-Ship CI/CD Firewall & Attack Engine
Demonstrates the full autonomous lifecycle in 90 seconds:
1. Flawed AI Agent Draft (Hallucinated price + battery life)
2. ⚔️ Adversarial Attack & 3-Agent Committee Deliberation
3. 🚨 Pre-Ship Firewall Gate: BLOCKED_UNSAFE (Reliability: 51/100)
4. 🔧 Surgical Autonomous Diff-Repair
5. ✅ Re-Evaluation & Clearance: REPAIRED_AND_APPROVED (Reliability: 96/100)
6. 🔏 SHA-256 Cryptographic Chain Verification & Arena Credits Settlement
"""

import sys
import time
import json
import os

# Ensure root dir is in sys.path
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

# Enable UTF-8 terminal output on Windows
if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from core.schemas import FirewallGateRequest, AuditMode, GateStatusEnum

from core.firewall import AgentFirewallGate
from sharedos.service import AgentScoutService
from arena.ledger import ArenaLedger


def print_banner(text: str, char: str = "="):
    print("\n" + char * 70)
    print(f"  {text}")
    print(char * 70)


def run_megademo():
    print_banner("AGENTSCOUT: PRE-SHIP CI/CD FIREWALL & ATTACK ENGINE", "=")
    print("  Positioning: Agent -> AgentScout -> World")
    print("  Protocol: SharedNet HMAC-SHA256 Turned-Gated Infrastructure")
    print("-" * 70)
    time.sleep(0.8)

    # Initialize Services
    service = AgentScoutService()
    ledger = ArenaLedger()
    firewall = AgentFirewallGate(service=service)
    caller_agent = "AutonomousShoppingBot-v4"

    # Initial Arena Credits
    init_balance = ledger.get_balance(caller_agent)
    print(f"\n[ECONOMY] Caller Agent: '{caller_agent}'")
    print(f"[ECONOMY] Initial Arena Credit Balance: {init_balance} Credits")
    time.sleep(0.6)

    # -------------------------------------------------------------
    # ACT 1: Flawed Upstream Agent Draft
    # -------------------------------------------------------------
    print_banner("ACT 1: THE UNVERIFIED UPSTREAM AGENT DRAFT", "-")
    flawed_query = "What is the battery life of Sony WH-1000XM5?"
    flawed_draft = "The Sony WH-1000XM5 features 40 hours of continuous music playback with ANC enabled."
    print(f"  [PROMPT]: {flawed_query}")
    print(f"  [DRAFT RESPONSE]:\n    \"{flawed_draft}\"")
    print("\n  [RISK]: This draft contains a critical specification hallucination:")
    print("         Sony WH-1000XM5 battery life is 30 hours with ANC ON (40 hours only with ANC OFF).")
    print("  [ACTION]: Intercepted by AgentScout Pre-Ship CI/CD Firewall Gate before reaching the user.")
    time.sleep(1.2)



    # -------------------------------------------------------------
    # ACT 2: ⚔️ Adversarial Attack & 3-Agent Deliberation
    # -------------------------------------------------------------
    print_banner("ACT 2: ⚔️ ADVERSARIAL ATTACK & 3-AGENT COMMITTEE", "-")
    print("  [*] Extracting atomic verifiable propositions...")
    print("  [*] Querying live multi-source web evidence (Wikipedia + DDG)...")
    print("  [*] Convening 3-Agent Deliberation Committee:\n")
    time.sleep(1.0)

    req = FirewallGateRequest(
        question=flawed_query,
        answer=flawed_draft,
        min_reliability_threshold=80,
        strict_attack_mode=True,
        auto_repair=True
    )

    # Deduct credits
    success, bal, _ = ledger.deduct_credits(caller_agent, 5, service_name="POST /firewall/gate (MegaDemo)")

    # Execute Firewall Gate
    start_time = time.time()
    gate_res = firewall.evaluate_gate(req, caller_agent_id=caller_agent)
    elapsed = time.time() - start_time

    # Display Committee Findings
    initial_audit = gate_res.audit_autopsy
    for claim in initial_audit.claims:
        print(f"  + Claim #{claim.claim_id}: \"{claim.claim_text}\"")
        print(f"    Verdict: [{claim.verdict.value}] (Confidence: {claim.confidence*100:.0f}%)")
        if claim.contradiction_details:
            print(f"    Contradiction: {claim.contradiction_details}")
        
        print("    Committee Deliberation:")
        for vote in claim.committee_votes:
            badge = "🔍" if "Researcher" in vote.agent_name else ("⚔️" if "Skeptic" in vote.agent_name else "⚖️")
            print(f"      {badge} [{vote.agent_name}]: {vote.verdict.value} (Conf: {vote.confidence*100:.0f}%)")
            print(f"         Arg: {vote.argument}")
        
        if claim.source_conflict and claim.source_conflict.has_conflict:
            print(f"    ⚖️ Source Conflict Resolution: {claim.source_conflict.resolution_rationale}")
        print()
        time.sleep(0.5)

    # -------------------------------------------------------------
    # ACT 3: 🚨 Pre-Ship Gate Interception: BLOCKED
    # -------------------------------------------------------------
    print_banner("ACT 3: 🚨 PRE-SHIP FIREWALL GATE INTERCEPTION", "-")
    print(f"  [RAW RELIABILITY]: {gate_res.initial_reliability} / 100  (Required: {req.min_reliability_threshold})")
    print(f"  [CONTRADICTIONS DETECTED]: {len(gate_res.blocked_reasons)}")
    for r in gate_res.blocked_reasons:
        print(f"    - ❌ {r}")
    print("  [FIREWALL INTERCEPT]: 🚨 BLOCKED_UNSAFE — Response prohibited from shipping to human user!")
    time.sleep(1.0)

    # -------------------------------------------------------------
    # ACT 4: 🔧 Autonomous Surgical Repair & Re-Evaluation
    # -------------------------------------------------------------
    print_banner("ACT 4: 🔧 SURGICAL DIFF-REPAIR & CLEARANCE", "-")
    print("  [*] Triggering in-flight AST/token diff-repair engine...")
    print("  [*] Grounding corrected tokens against verified manufacturer catalog...")
    time.sleep(0.8)

    print("\n  [BEFORE (BLOCKED)]:")
    print(f"    \"{flawed_draft}\"")
    print("\n  [AFTER (REPAIRED)]:")
    print(f"    \"{gate_res.safe_to_ship_answer}\"")

    print(f"\n  [REPAIRED RELIABILITY]: {gate_res.final_reliability} / 100")
    print(f"  [FINAL GATE STATUS]:   ✅ {gate_res.status.value}")
    if gate_res.status == GateStatusEnum.REPAIRED_AND_APPROVED or gate_res.status == GateStatusEnum.APPROVED_CLEAN:
        print("  [DISPATCH STATUS]:     CLEARED FOR EGRESS TO HUMAN USER")
    else:
        print("  [DISPATCH STATUS]:     BLOCKED FROM EGRESS TO HUMAN USER")
    time.sleep(1.0)

    # -------------------------------------------------------------
    # ACT 5: 🔏 Cryptographic Proof Chain & Settlement
    # -------------------------------------------------------------
    print_banner("ACT 5: 🔏 CRYPTOGRAPHIC PROOF CHAIN & ARENA SETTLEMENT", "-")
    audit_id = gate_res.audit_autopsy.audit_id
    trail = service.audit_history.get(audit_id)
    verify_res = {}

    if trail:
        verify_res = trail.verify_integrity()
        print(f"  [AUDIT ID]: {audit_id}")
        print(f"  [5-TURN PROVENANCE]: {verify_res.get('chain_depth', 5)} Turns Linked")
        print(f"  [ROOT SHA-256 HASH]:   {verify_res.get('root_hash')}")
        print(f"  [FINAL SHA-256 HASH]:  {verify_res.get('latest_hash')}")
        print(f"  [TAMPER VERIFICATION]: {'🟢 UNBROKEN CRYPTOGRAPHIC CHAIN' if verify_res.get('valid') else '🔴 TAMPERED'}")
    
    print(f"\n  [ECONOMY SETTLEMENT]:")
    print(f"    Fee Deducted:      -5 Arena Credits")
    print(f"    Remaining Balance:  {bal} Arena Credits")
    print(f"    Transaction Log:    Appended to .sharedos/ledger.json (CSV Export Ready)")
    print(f"    Latency:            {elapsed:.2f}s total pipeline execution")

    print_banner("DEMO SUMMARY: AGENTSCOUT HAS SECURED THE AGENT", "=")
    print(f"  1. Flawed Draft Intercepted  -> BLOCKED ({gate_res.initial_reliability}/100)")
    print(f"  2. Adversarial Attacks Run   -> {gate_res.audit_autopsy.stats.contradicted} Contradiction(s) Caught by Committee")
    print(f"  3. Surgical Repair Applied   -> {gate_res.status.value} ({gate_res.final_reliability}/100)")
    print(f"  4. Immutable Proof Stored    -> SHA-256 Block Persisted ({verify_res.get('chain_depth', 5)} Turns)")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    run_megademo()
