"""
AgentScout Comprehensive System Health Check & Pre-Flight Validator
Runs end-to-end verification across all 8 architectural subsystems in < 5 seconds.
"""

import sys
import os
import time

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

if hasattr(sys.stdout, 'reconfigure'):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

from fastapi.testclient import TestClient
from server import app, service, cloud_adapter, ledger
from core.schemas import AuditRequest, FirewallGateRequest, AuditMode, VerdictEnum
from core.committee import VerificationCommittee

client = TestClient(app)


def print_check(name: str, passed: bool, details: str = ""):
    icon = "🟢 [PASS]" if passed else "🔴 [FAIL]"
    print(f"  {icon} {name:<45} {details}")


def run_health_check():
    print("\n" + "=" * 75)
    print("  AGENTSCOUT SUBSYSTEM HEALTH CHECK & PRE-FLIGHT VERIFIER")
    print("=" * 75)
    
    all_passed = True
    start_time = time.time()

    # 1. Manifest & Purpose Check
    res_manifest = client.get("/manifest")
    res_purpose = client.get("/purpose")
    p1 = res_manifest.status_code == 200 and res_purpose.status_code == 200
    print_check("1. SharedOS Manifest & Purpose Endpoints", p1, f"Status {res_manifest.status_code}")
    all_passed = all_passed and p1

    # 2. HMAC Security Enforcement (Reject unauthorized with 401)
    res_unauth = client.post("/audit", json={"question": "Test", "answer": "Test"})
    p2 = res_unauth.status_code == 401
    print_check("2. HMAC Authentication Enforcement", p2, "Rejected 401 on missing signature")
    all_passed = all_passed and p2

    # 3. Arena Credits Ledger & CSV Export
    caller = "HealthCheckAgent"
    bal_before = ledger.get_balance(caller)
    res_csv = client.get("/ledger/export")
    p3 = bal_before >= 100 and res_csv.status_code == 200 and "balance_after" in res_csv.text
    print_check("3. Arena Ledger & CSV Transaction Export", p3, f"Initial Balance: {bal_before} Credits")
    all_passed = all_passed and p3

    # 4. Live Multi-Source Research Engine
    search_res = service.search_engine.search_claim("Apollo 11 landed on the Moon in 1969", "Apollo 11")
    p4 = len(search_res) > 0 and any("wikipedia.org" in e.source_url for e in search_res)
    print_check("4. Live Encyclopedic Search (Wikipedia REST)", p4, f"{len(search_res)} sources retrieved")
    all_passed = all_passed and p4

    # 5. Multi-Agent Deliberation Committee
    committee = VerificationCommittee()
    votes, conflict, decay = committee.deliberate(
        claim_text="Sony XM5 has 40 hours battery life with ANC on",
        evidence=search_res,
        raw_verdict=VerdictEnum.CONTRADICTED,
        correction="Verified battery life is 30 hours"
    )
    p5 = len(votes) == 3 and any("Researcher" in v.agent_name for v in votes) and any("Skeptic" in v.agent_name for v in votes)
    print_check("5. 3-Agent Committee Deliberation Engine", p5, "Researcher + Skeptic + SourceJudge")
    all_passed = all_passed and p5

    # 6. Pre-Ship CI/CD Firewall Gate (Block -> Repair -> Approve)
    from core.schemas import EvidenceItem
    def mock_sony_search(claim, question=""):
        return [EvidenceItem(
            source_url="https://sony.com/wh-1000xm5/specs",
            source_title="Sony WH-1000XM5 Official Specifications",
            snippet="Sony WH-1000XM5 features 30 hours of battery life with noise cancellation ON (40 hours with NC OFF).",
            reliability_weight=1.0
        )]
    orig_search = service.search_engine.search_claim
    service.search_engine.search_claim = mock_sony_search
    
    req = AuditRequest(
        question="What is the battery life of Sony WH-1000XM5?",
        answer="The Sony WH-1000XM5 features 40 hours of continuous music playback with ANC enabled.",
        mode=AuditMode.ATTACK
    )
    audit_res, trail = service.execute_audit(req, caller_agent_id="HealthCheckAgent")
    service.search_engine.search_claim = orig_search
    
    p6 = audit_res.stats.contradicted > 0 and audit_res.repaired_answer is not None and "30 hours" in audit_res.repaired_answer
    print_check("6. Pre-Ship Gate & Surgical Diff-Repair", p6, f"Repaired: '{audit_res.repaired_answer[:35]}...'")
    all_passed = all_passed and p6


    # 7. Cryptographic Chain Integrity Verification Endpoint
    verify_res = client.get(f"/api/audit-trail/{audit_res.audit_id}/verify")
    p7 = verify_res.status_code == 200 and verify_res.json().get("valid") is True
    print_check("7. SHA-256 Cryptographic Chain Verification", p7, f"Depth: {verify_res.json().get('chain_depth', 5)} turns")
    all_passed = all_passed and p7

    # 8. Web Mission Control UI
    ui_res = client.get("/")
    p8 = ui_res.status_code == 200 and "Pre-Ship Firewall Gate" in ui_res.text
    print_check("8. Web Mission Control UI (/)", p8, f"{len(ui_res.text)} bytes served")
    all_passed = all_passed and p8

    elapsed = time.time() - start_time
    print("-" * 75)
    if all_passed:
        print(f"  [SUCCESS] ALL 8 SUBSYSTEMS OPERATIONAL (Execution: {elapsed:.2f}s)")
    else:
        print("  [WARNING] Some subsystems reported anomalies.")
    print("=" * 75 + "\n")
    return all_passed


if __name__ == "__main__":
    success = run_health_check()
    sys.exit(0 if success else 1)
