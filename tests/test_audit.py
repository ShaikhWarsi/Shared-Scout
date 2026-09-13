"""
AgentScout Automated Test Suite
Verifies claim extraction, contradiction detection, SharedOS compliance, and A2A service contracts.
"""

import pytest
from core.schemas import AuditRequest, VerdictEnum
from core.extractor import ClaimExtractor
from core.verifier import ClaimVerifier
from core.search import WebSearchEngine
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


def test_contradiction_detection():
    service = AgentScoutService()
    req = AuditRequest(
        question="Find best headphones under 3000",
        answer="The Realme Buds Air 5 Pro provides 50dB ANC and costs Rs. 2,499."
    )
    resp, trail = service.execute_audit(req, caller_agent_id="TestAgent")
    
    assert resp.stats.contradicted >= 1
    assert resp.verdict_summary == "CONTRADICTED"
    assert resp.reliability <= 60
    assert "Rs. 4,999" in resp.claims[0].correction


def test_sharedos_audit_trail_cryptography():
    service = AgentScoutService()
    req = AuditRequest(
        question="Test Question",
        answer="boAt Rockerz 450 is priced at Rs. 1,499."
    )
    resp, trail = service.execute_audit(req, caller_agent_id="TestAgent")
    
    assert trail["total_turns"] == 5
    assert trail["purpose"] == SHAREDOS_PURPOSE_STRING
    assert len(trail["final_hash"]) == 64
    assert trail["trail"][0]["step"] == "TURN_1_INGRESS"
    assert trail["trail"][-1]["step"] == "TURN_5_EGRESS"


def test_a2a_latency_and_billing():
    service = AgentScoutService()
    req = AuditRequest(
        question="Battery spec of Sony WH-1000XM5?",
        answer="Sony WH-1000XM5 features 40 hours continuous music playback with ANC enabled."
    )
    resp, _ = service.execute_audit(req, caller_agent_id="FastAgent")
    
    assert resp.credits_billed == 5
    assert resp.execution_latency_ms < 5000  # Well within 5 minutes timeout limit
    assert resp.stats.contradicted == 1
