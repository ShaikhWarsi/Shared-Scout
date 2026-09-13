"""
Pytest integration for Hostile Black-Box Edge Cases
Ensures 100% crash resistance and graceful handling across 14 edge cases.
"""

import pytest
from core.firewall import AgentFirewallGate
from core.schemas import FirewallGateRequest, AuditRequest
from sharedos.service import AgentScoutService
from scripts.torture_test import TORTURE_CASES


@pytest.fixture(scope="module")
def gate_system():
    service = AgentScoutService()
    firewall = AgentFirewallGate(service=service)
    return service, firewall


@pytest.mark.parametrize("case", TORTURE_CASES, ids=[f"case_{c['id']}_{c['name'].replace(' ', '_')}" for c in TORTURE_CASES])
def test_torture_edge_case_no_crash(gate_system, case):
    service, firewall = gate_system

    req = FirewallGateRequest(
        question=case["question"],
        answer=case["answer"],
        min_reliability_threshold=80,
        auto_repair=True,
        strict_attack_mode=False
    )
    
    # 1. Must never raise an unhandled exception
    gate_res = firewall.evaluate_gate(req, caller_agent_id="pytest-torture")
    assert gate_res.status is not None
    assert 0 <= gate_res.final_reliability <= 100
    assert gate_res.safe_to_ship_answer is not None

    # 2. Audit request must succeed
    audit_req = AuditRequest(question=case["question"], answer=case["answer"])
    audit_res, trail = service.execute_audit(audit_req, caller_agent_id="pytest-torture")
    assert audit_res.verdict_summary is not None
    assert audit_res.reliability >= 0
