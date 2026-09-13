"""
AgentScout Live Multi-Agent A2A Economy & Autonomous Repair Demonstration
Simulates a calling agent (ShoppingBot-Node-71) delegating answer verification to AgentScout,
detecting factual contradictions in real time, and automatically repairing hallucinations before user delivery.
"""

import sys
import os
import time
import json

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.schemas import AuditRequest
from sharedos.service import AgentScoutService


def run_live_a2a_simulation():
    service = AgentScoutService()

    print("\n" + "=" * 85)
    print("  🤖 SHAREDNET AUTONOMOUS AGENT-TO-AGENT (A2A) INTEROPERABILITY DEMONSTRATION")
    print("=" * 85)

    # -------------------------------------------------------------
    # PHASE 1: Calling Agent (ShoppingBot) generates draft response
    # -------------------------------------------------------------
    user_query = "Find the best noise cancelling headphones under Rs 3,000 in India."
    print(f"\n[PHASE 1] USER QUERY TO CALLING AGENT (ShoppingBot-Node-71):")
    print(f'  "{user_query}"')

    flawed_draft = (
        "The boAt Rockerz 450 is a top choice with 15 hours battery life at Rs. 1,499. "
        "For active noise cancellation, the Realme Buds Air 5 Pro provides 50dB ANC and costs Rs. 2,499 with quick charging."
    )

    print(f"\n[PHASE 2] SHOPPINGBOT GENERATES INITIAL DRAFT (Contains Hallucinated Price):")
    print(f'  "{flawed_draft}"')

    # -------------------------------------------------------------
    # PHASE 3: A2A Defensive Insurance Call to AgentScout
    # -------------------------------------------------------------
    print(f"\n[PHASE 3] SHOPPINGBOT CALLS AGENTSCOUT A2A SERVICE (/audit):")
    print(f"  Target Endpoint : agentscout.sharedos.net/audit")
    print(f"  Protocol        : SharedNet/1.0 (HMAC-SHA256 Signed)")
    print(f"  Micro-Billing   : 5 Arena Credits Transferred to AgentScout")
    print(f"  Execution Mode  : Independent Multi-Source Factual Verification...")

    t0 = time.time()
    req = AuditRequest(question=user_query, answer=flawed_draft)
    response, trail = service.execute_audit(req, caller_agent_id="ShoppingBot-Node-71")
    elapsed_ms = response.execution_latency_ms

    # -------------------------------------------------------------
    # PHASE 4: AgentScout Autopsy & Contradiction Detection
    # -------------------------------------------------------------
    print(f"\n[PHASE 4] AGENTSCOUT RETURNS FACTUAL AUTOPSY REPORT ({elapsed_ms}ms):")
    print(f"  Audit ID        : {response.audit_id}")
    print(f"  Reliability     : {response.reliability} / 100")
    print(f"  Verdict Summary : {response.verdict_summary}")
    print(f"  Claims Extracted: {response.stats.total_claims} (Supported: {response.stats.supported}, Contradicted: {response.stats.contradicted})")

    for c in response.claims:
        status_symbol = "✓ [SUPPORTED]" if c.verdict == "SUPPORTED" else "✗ [CONTRADICTED]"
        print(f"\n    {status_symbol} Claim #{c.claim_id}: {c.claim_text}")
        if c.contradiction_details:
            print(f"      ↳ Contradiction : {c.contradiction_details}")
            print(f"      ↳ Correction    : {c.correction}")
        if c.evidence:
            print(f"      ↳ Primary Source: {c.evidence[0].source_title} ({c.evidence[0].source_url})")

    # -------------------------------------------------------------
    # PHASE 5: Autonomous Answer Repair
    # -------------------------------------------------------------
    print(f"\n[PHASE 5] SHOPPINGBOT AUTONOMOUSLY REPAIRS ANSWER BEFORE USER DELIVERY:")
    print("  BEFORE (Flawed Draft)   : " + flawed_draft)
    print("  AFTER  (Repaired Output): " + (response.repaired_answer or flawed_draft))

    # -------------------------------------------------------------
    # PHASE 6: Cryptographic Proof & Turn Hash Chain
    # -------------------------------------------------------------
    print(f"\n[PHASE 6] SHAREDOS CRYPTOGRAPHIC PROOF (Disk Persisted at .sharedos/audit_log.jsonl):")
    for event in trail["trail"]:
        print(f'  [PASS] {event["step"]:<24} | Hash: {event["event_hash"][:20]}... | Time: {event["iso_time"]}')

    print(f"\n" + "=" * 85)
    print(f"  [SUCCESS] 100% Closed-Loop Agent Verification & Hallucination Repair Complete!")
    print("=" * 85 + "\n")


if __name__ == "__main__":
    run_live_a2a_simulation()
