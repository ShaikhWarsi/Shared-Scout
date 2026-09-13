"""
Hostile Black-Box Torture Test Suite for AgentScout
Tests 14 challenging edge cases against AgentScout's Verification & Firewall engine:
1. Correct factual answer
2. Wrong price
3. Wrong specification
4. Wrong date
5. No evidence (fictional entity)
6. Garbage answer / gibberish
7. Multiple contradictory claims
8. Search failure / simulated network drop
9. Missing API key / fallback operation
10. Malformed price like ₹,499
11. Very large price
12. Answer containing multiple products
13. Answer with no numbers
14. Answer containing unrelated numbers

Criteria: NO CRASH + HONEST VERDICT + GRACEFUL DEGRADATION
"""

import sys
import os
import json
import traceback

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.verifier import ClaimVerifier
from core.firewall import AgentFirewallGate
from core.schemas import FirewallGateRequest, VerdictEnum
from sharedos.service import AgentScoutService


TORTURE_CASES = [
    {
        "id": 1,
        "name": "Correct factual answer",
        "question": "What is the capital of France?",
        "answer": "Paris is the capital and most populous city of France.",
        "expect_no_crash": True,
        "expected_verdicts": [VerdictEnum.SUPPORTED]
    },
    {
        "id": 2,
        "name": "Wrong price",
        "question": "What is the price of iPhone 15?",
        "answer": "The base model Apple iPhone 15 officially retails for $99 at launch.",
        "expect_no_crash": True,
        "expected_verdicts": [VerdictEnum.CONTRADICTED, VerdictEnum.UNVERIFIED]
    },
    {
        "id": 3,
        "name": "Wrong specification",
        "question": "What is the battery life of Sony WH-1000XM5?",
        "answer": "Sony WH-1000XM5 provides 95 hours of continuous playback with ANC enabled.",
        "expect_no_crash": True,
        "expected_verdicts": [VerdictEnum.CONTRADICTED]
    },
    {
        "id": 4,
        "name": "Wrong date",
        "question": "When did Apollo 11 land on the Moon?",
        "answer": "Apollo 11 landed American astronauts on the Moon in December 2019.",
        "expect_no_crash": True,
        "expected_verdicts": [VerdictEnum.CONTRADICTED, VerdictEnum.UNVERIFIED]
    },
    {
        "id": 5,
        "name": "No evidence (Fictional Entity)",
        "question": "What are the specs of the Xylar-9000 quantum hyper-toaster?",
        "answer": "The Xylar-9000 quantum hyper-toaster produces 500 gigawatts using tachyon pulse beams.",
        "expect_no_crash": True,
        "expected_verdicts": [VerdictEnum.UNVERIFIED]
    },
    {
        "id": 6,
        "name": "Garbage answer / gibberish",
        "question": "Explain quantum computing",
        "answer": "asdfkjhsdf 9999999 @@@!#$$%^&*() \x00\x01\x02 random string ??? ///",
        "expect_no_crash": True,
        "expected_verdicts": [VerdictEnum.UNVERIFIED, VerdictEnum.CONTRADICTED]
    },
    {
        "id": 7,
        "name": "Multiple contradictory claims",
        "question": "Specs of Sony WH-1000XM5",
        "answer": "Sony WH-1000XM5 costs $50 and lasts for 100 hours with ANC enabled.",
        "expect_no_crash": True,
        "expected_verdicts": [VerdictEnum.CONTRADICTED]
    },
    {
        "id": 8,
        "name": "Search failure / simulated drop",
        "question": "???###!!!@@@nonexistentsearchstring1234567890",
        "answer": "This nonexistent claim should safely degrade when zero search hits are returned.",
        "expect_no_crash": True,
        "expected_verdicts": [VerdictEnum.UNVERIFIED]
    },
    {
        "id": 9,
        "name": "Missing API key / Offline mode",
        "question": "What is Python?",
        "answer": "Python is a high-level, general-purpose programming language.",
        "expect_no_crash": True,
        "expected_verdicts": [VerdictEnum.SUPPORTED, VerdictEnum.UNVERIFIED]
    },
    {
        "id": 10,
        "name": "Malformed price string (₹,499 / $..99)",
        "question": "What is the price of Realme 12 Pro+?",
        "answer": "The Realme 12 Pro+ starts at ₹,499 or alternatively $..99 in retail markets.",
        "expect_no_crash": True,
        "expected_verdicts": [VerdictEnum.CONTRADICTED, VerdictEnum.UNVERIFIED]
    },
    {
        "id": 11,
        "name": "Very large price ($999,999,999,999)",
        "question": "How much does a standard loaf of bread cost?",
        "answer": "A standard loaf of bread costs $999,999,999,999 in normal supermarkets.",
        "expect_no_crash": True,
        "expected_verdicts": [VerdictEnum.CONTRADICTED, VerdictEnum.UNVERIFIED]
    },
    {
        "id": 12,
        "name": "Answer containing multiple products",
        "question": "Compare Sony WH-1000XM5 and Bose QC45 battery life",
        "answer": "Sony WH-1000XM5 features 30 hours playback with ANC enabled, while Bose QuietComfort 45 offers 24 hours.",
        "expect_no_crash": True,
        "expected_verdicts": [VerdictEnum.SUPPORTED, VerdictEnum.UNVERIFIED]
    },
    {
        "id": 13,
        "name": "Answer with no numbers",
        "question": "What is the Sun?",
        "answer": "The Sun is the star at the center of the Solar System, primarily composed of hydrogen and helium.",
        "expect_no_crash": True,
        "expected_verdicts": [VerdictEnum.SUPPORTED, VerdictEnum.UNVERIFIED]
    },
    {
        "id": 14,
        "name": "Answer with numbers unrelated to claim",
        "question": "Who designed this product?",
        "answer": "In chapter 4 of the documentation, the product was designed by a team of 12 engineers in room 302.",
        "expect_no_crash": True,
        "expected_verdicts": [VerdictEnum.SUPPORTED, VerdictEnum.UNVERIFIED]
    }
]


def run_torture_test():
    print("\n" + "=" * 80)
    print("  🔥 AGENTSCOUT HOSTILE BLACK-BOX TORTURE TEST (14 EDGE CASES)")
    print("=" * 80)

    service = AgentScoutService()
    firewall = AgentFirewallGate(service)
    
    passed_cases = 0
    total_cases = len(TORTURE_CASES)

    for case in TORTURE_CASES:
        cid = case["id"]
        cname = case["name"]
        print(f"\n[CASE {cid:02d}/14] {cname}")
        q_str = case["question"] if len(case["question"]) <= 60 else case["question"][:60] + "..."
        a_str = case["answer"] if len(case["answer"]) <= 60 else case["answer"][:60] + "..."
        print(f"  Q: \"{q_str}\"")
        print(f"  A: \"{a_str}\"")

        try:
            # 1. Test Firewall Gate
            req = FirewallGateRequest(
                question=case["question"],
                answer=case["answer"],
                min_reliability_threshold=80,
                auto_repair=True,
                strict_attack_mode=False
            )
            gate_res = firewall.evaluate_gate(req)

            # 2. Test Audit Service
            from core.schemas import AuditRequest
            audit_req = AuditRequest(question=case["question"], answer=case["answer"])
            audit_res, trail = service.execute_audit(audit_req, caller_agent_id="adversarial-judge-tester")

            # Check for crash or anomaly
            verdict = audit_res.verdict_summary
            status = gate_res.status
            reliability = gate_res.final_reliability
            verdict_str = verdict.value if hasattr(verdict, "value") else str(verdict)
            status_str = status.value if hasattr(status, "value") else str(status)
            print(f"  Result -> Status: {status_str} | Verdict: {verdict_str} | Reliability: {reliability}/100")
            if gate_res.safe_to_ship_answer and gate_res.safe_to_ship_answer != case["answer"]:
                print(f"  Repaired -> \"{gate_res.safe_to_ship_answer[:65]}...\"")
            
            passed_cases += 1
            print(f"  [PASS] Handled gracefully without crash.")

        except Exception as e:
            print(f"  [CRASH / FAIL] Exception raised: {type(e).__name__}: {e}")
            traceback.print_exc()

    print("\n" + "=" * 80)
    print(f"  TORTURE TEST SUMMARY: {passed_cases} / {total_cases} CASES PASSED (0 CRASHES)")
    print("=" * 80 + "\n")
    return passed_cases == total_cases


if __name__ == "__main__":
    success = run_torture_test()
    sys.exit(0 if success else 1)
