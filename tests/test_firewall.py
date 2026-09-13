import pytest
from core.schemas import FirewallGateRequest, GateStatusEnum, EvidenceItem
from core.firewall import AgentFirewallGate
from sharedos.service import AgentScoutService


def test_firewall_gate_blocking_and_repair(monkeypatch):
    service = AgentScoutService()
    
    # Mock search to return contradicted evidence for initial draft, and supported for repaired draft
    def mock_search(claim, question=""):
        if "2,499" in claim or "realme" in claim.lower():
            return [
                EvidenceItem(
                    source_url="https://buy.realme.com/in/goods/realme-buds-air-5-pro",
                    source_title="Realme Official Catalog",
                    snippet="Realme Buds Air 5 Pro official price is Rs. 4,999 with 50dB ANC.",
                    reliability_weight=1.0
                )
            ]
        elif "boat" in claim.lower() or "1,499" in claim:
            return [
                EvidenceItem(
                    source_url="https://www.boat-lifestyle.com/products/rockerz-450",
                    source_title="boAt Official Store",
                    snippet="boAt Rockerz 450 is priced at Rs. 1,499 with 15 hours battery.",
                    reliability_weight=1.0
                )
            ]
        return []

    monkeypatch.setattr(service.search_engine, "search_claim", mock_search)
    firewall = AgentFirewallGate(service=service)

    req = FirewallGateRequest(
        question="Find headphones under 3000",
        answer="The boAt Rockerz 450 is Rs. 1,499. The Realme Buds Air 5 Pro is Rs. 2,499.",
        min_reliability_threshold=80,
        auto_repair=True,
        strict_attack_mode=True
    )

    res = firewall.evaluate_gate(req, caller_agent_id="TestAgent")
    assert res.status == GateStatusEnum.REPAIRED_AND_APPROVED
    assert res.initial_reliability <= 60
    assert "Rs. 4,999" in res.safe_to_ship_answer
    assert len(res.blocked_reasons) >= 1
