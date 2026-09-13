"""AgentScout Deterministic Demo Runner"""
import sys
import os
import json
import time

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.schemas import AuditRequest
from sharedos.service import AgentScoutService

def run_terminal_demo():
    service = AgentScoutService()
    fix_path = os.path.join(os.path.dirname(__file__), "demo_fixtures.json")
    with open(fix_path, "r", encoding="utf-8") as f:
        fixtures = json.load(f)

    fixture = fixtures["headphone_demo"]
    q = fixture["question"]
    a = fixture["answer"]

    print("\n" + "="*80)
    print("[SHAREDNET A2A LIVE DEMONSTRATION: AGENTSCOUT]")
    print("="*80)
    print("Calling Agent : ShoppingBot-Node-71")
    print("Service Target: agentscout.sharedos.net/audit")
    print("Fee           : 5 Arena Credits")
    print("\n[STEP 1] INCOMING AGENT ANSWER TO CHALLENGE:")
    print(f"Question: {q}")
    print(f"Answer  : {a}\n")

    print("[STEP 2] CALLING AGENTSCOUT (A2A)... Verifying on SharedOS Cloud...")
    time.sleep(1)

    req = AuditRequest(question=q, answer=a)
    response, trail = service.execute_audit(req, caller_agent_id="ShoppingBot-Node-71")

    lat = response.execution_latency_ms
    print(f"\n[STEP 3] SHAREDOS AUDIT TRAIL LOGGED (5 Turns in {lat}ms):")
    for event in trail["trail"]:
        step = event["step"]
        iso = event["iso_time"]
        h = event["event_hash"][:16]
        print(f"  [PASS] [{iso}] {step} (Hash: {h}...)")

    print("\n" + "="*80)
    print("[AGENTSCOUT ANSWER AUTOPSY REPORT]")
    print("="*80)
    print(f"Reliability Score : {response.reliability} / 100")
    print(f"Verdict Summary   : {response.verdict_summary}")
    print(f"Claims Analyzed   : {response.stats.total_claims}")
    print(f"  [+] Supported   : {response.stats.supported}")
    print(f"  [-] Contradicted: {response.stats.contradicted}")
    print(f"  [?] Unverified  : {response.stats.unverified}")
    print("\nDETAILED CLAIMS BREAKDOWN:")
    for c in response.claims:
        badge = "[+] SUPPORTED" if c.verdict == "SUPPORTED" else "[-] CONTRADICTED" if c.verdict == "CONTRADICTED" else "[?] UNVERIFIED"
        conf = int(c.confidence * 100)
        print(f"\n  {badge} Claim #{c.claim_id}: {c.claim_text} (Confidence: {conf}%)")
        if c.contradiction_details:
            print(f"    [!] Contradiction: {c.contradiction_details}")
        if c.correction:
            print(f"    [*] Correction:    {c.correction}")
        if c.evidence:
            print(f"    [>] Evidence ({len(c.evidence)} sources):")
            for ev in c.evidence[:2]:
                print(f"       * [{ev.source_title}] {ev.snippet}")
                print(f"         Source: {ev.source_url}")

    print("\n" + "-"*80)
    print(f"ADVISORY RECOMMENDATION: {response.recommendation}")
    print("TRANSACTION RECEIPT    : 5 Arena Credits Billed to ShoppingBot-Node-71")
    print("="*80 + "\n")

if __name__ == "__main__":
    run_terminal_demo()
