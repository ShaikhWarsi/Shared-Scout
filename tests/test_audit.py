"""
AgentScout Automated Test Suite
Verifies claim extraction, generalized NLI contradiction detection, SharedOS compliance, and A2A service contracts.
"""

import pytest
from core.schemas import AuditRequest, EvidenceItem, VerdictEnum
from core.extractor import ClaimExtractor
from core.verifier import ClaimVerifier
from core.scorer import AuditScorer
from sharedos.service import AgentScoutService
from sharedos.manifest import SHAREDOS_MANIFEST, SHAREDOS_PURPOSE_STRING


def test_sharedos_manifest():
    assert SHAREDOS_MANIFEST["agent_id"] == "agentscout-v1"
    assert SHAREDOS_MANIFEST["purpose"] == SHAREDOS_PURPOSE_STRING
    assert "network:http_client" in SHAREDOS_MANIFEST["grants"]
    assert SHAREDOS_MANIFEST["services"][0]["price_credits"] == 5


def test_claim_extractor_currency_protection():
    extractor = ClaimExtractor()
    q = "What are the headphone prices?"
    a = "boAt Rockerz costs Rs. 1,499 with 15hr battery. Realme Buds Air 5 Pro costs Rs. 2,499 with 50dB ANC."
    claims = extractor.extract_claims(q, a)
    assert len(claims) == 2
    assert "Rs. 1,499" in claims[0]
    assert "Rs. 2,499" in claims[1]


def test_verifier_price_contradiction_direct():
    """Tests generalized price contradiction detection with evidence."""
    verifier = ClaimVerifier()
    claim_text = "The Realme Buds Air 5 Pro provides 50dB ANC and costs Rs. 2,499."
    evidence = [
        EvidenceItem(
            source_url="https://buy.realme.com/in/goods/realme-buds-air-5-pro",
            source_title="Realme Official Store",
            snippet="Realme Buds Air 5 Pro official launch price is Rs. 4,999. Includes 50dB Active Noise Cancellation.",
            reliability_weight=1.0
        )
    ]
    audit = verifier.verify_claim(1, claim_text, evidence)
    assert audit.verdict == VerdictEnum.CONTRADICTED
    assert audit.confidence >= 0.90
    assert "Rs. 4,999" in audit.correction
    assert "Rs. 2,499" in audit.contradiction_details


def test_verifier_battery_spec_contradiction_direct():
    """Tests generalized spec/qualifier contradiction detection with evidence."""
    verifier = ClaimVerifier()
    claim_text = "Sony WH-1000XM5 features 40 hours continuous music playback with ANC enabled."
    evidence = [
        EvidenceItem(
            source_url="https://www.sony.com/electronics/headband-headphones/wh-1000xm5/specifications",
            source_title="Sony Official Global Specifications",
            snippet="Battery Life (Continuous Music Playback): Max. 30 hours (NC ON), Max. 40 hours (NC OFF). 3 min quick charge provides 3 hours playback.",
            reliability_weight=1.0
        )
    ]
    audit = verifier.verify_claim(1, claim_text, evidence)
    assert audit.verdict == VerdictEnum.CONTRADICTED
    assert audit.confidence >= 0.90
    assert "30 hours" in audit.correction


def test_service_execution_and_repair(monkeypatch):
    """Tests full service pipeline with injected search evidence."""
    service = AgentScoutService()
    
    # Mock search_engine.search_claim to return evidence
    def mock_search(claim, question=""):
        return [
            EvidenceItem(
                source_url="https://buy.realme.com/in/goods/realme-buds-air-5-pro",
                source_title="Realme Official Store",
                snippet="Realme Buds Air 5 Pro launch price is Rs. 4,999 with 50dB ANC.",
                reliability_weight=1.0
            )
        ]
    monkeypatch.setattr(service.search_engine, "search_claim", mock_search)
    
    req = AuditRequest(
        question="Find headphones under 3000",
        answer="The Realme Buds Air 5 Pro costs Rs. 2,499 with 50dB ANC."
    )
    resp, trail = service.execute_audit(req, caller_agent_id="TestAgent")
    
    assert resp.stats.contradicted >= 1
    assert resp.verdict_summary == "CONTRADICTED"
    assert resp.reliability <= 60
    assert "Rs. 4,999" in resp.repaired_answer
    assert trail["total_turns"] == 5
    assert trail["purpose"] == SHAREDOS_PURPOSE_STRING
    assert len(trail["final_hash"]) == 64


def test_unverified_fallback_when_no_evidence():
    """Tests that missing search evidence properly returns UNVERIFIED with 0 hardcoding."""
    service = AgentScoutService()
    # Query an arbitrary made-up product that has 0 search results
    req = AuditRequest(
        question="What is the price of NonExistentWidget99?",
        answer="The NonExistentWidget99 costs Rs. 1,234 with quantum battery."
    )
    resp, _ = service.execute_audit(req, caller_agent_id="TestAgent")
    assert resp.stats.unverified >= 1
    assert resp.claims[0].verdict == VerdictEnum.UNVERIFIED
