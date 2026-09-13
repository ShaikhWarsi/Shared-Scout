import pytest
from core.schemas import EvidenceItem, VerdictEnum, AuditMode, AuditRequest
from core.committee import VerificationCommittee
from sharedos.service import AgentScoutService
from fastapi.testclient import TestClient
from server import app, service

client = TestClient(app)



def test_committee_independent_reasoning_contradiction():
    committee = VerificationCommittee()
    claim = "Realme Buds Air 5 Pro costs Rs. 2,499 with 50dB ANC"
    evidence = [
        EvidenceItem(
            source_url="https://realme.com/in/buds-air-5-pro",
            source_title="Realme Official Store",
            snippet="Realme Buds Air 5 Pro official price is Rs. 4,999 in India.",
            reliability_weight=1.0
        )
    ]
    
    votes, conflict, decay_risk = committee.deliberate(
        claim_text=claim,
        evidence=evidence,
        raw_verdict=VerdictEnum.CONTRADICTED,
        correction="Actual verified price is Rs. 4,999"
    )
    
    assert len(votes) == 3
    researcher = next(v for v in votes if "Researcher" in v.agent_name)
    skeptic = next(v for v in votes if "Skeptic" in v.agent_name)
    source_judge = next(v for v in votes if "SourceJudge" in v.agent_name)
    
    # Researcher checks citation consistency
    assert researcher.verdict == VerdictEnum.CONTRADICTED
    assert "Cross-referenced authoritative catalog" in researcher.argument
    
    # Skeptic detects temporal volatility and numeric mismatch
    assert skeptic.verdict == VerdictEnum.CONTRADICTED
    assert "Adversarial stress-test failed" in skeptic.argument
    assert decay_risk == "HIGH"
    
    # Source Judge evaluates authority tier
    assert source_judge.verdict == VerdictEnum.CONTRADICTED
    assert source_judge.confidence >= 0.90


def test_committee_supported_consensus():
    committee = VerificationCommittee()
    claim = "Python was created by Guido van Rossum and released in 1991."
    evidence = [
        EvidenceItem(
            source_url="https://en.wikipedia.org/wiki/Python_(programming_language)",
            source_title="Wikipedia: Python (programming language)",
            snippet="Python was created by Guido van Rossum and first released in 1991.",
            reliability_weight=0.90
        )
    ]
    
    votes, conflict, decay_risk = committee.deliberate(
        claim_text=claim,
        evidence=evidence,
        raw_verdict=VerdictEnum.SUPPORTED,
        correction=None
    )
    
    assert len(votes) == 3
    for v in votes:
        assert v.verdict == VerdictEnum.SUPPORTED


def test_audit_trail_chain_verify_endpoint(monkeypatch):
    def mock_search(claim, question=""):
        return [EvidenceItem(
            source_url="https://speed-of-light.gov",
            source_title="Physics Standards",
            snippet="The speed of light in vacuum is 299792 km/s.",
            reliability_weight=1.0
        )]
    monkeypatch.setattr(service.search_engine, "search_claim", mock_search)
    
    req = AuditRequest(question="Speed of light", answer="Speed of light is 299792 km/s.")
    resp, trail = service.execute_audit(req, caller_agent_id="test-verifier")
    
    verify_res = client.get(f"/api/audit-trail/{resp.audit_id}/verify")
    assert verify_res.status_code == 200
    v_data = verify_res.json()
    assert v_data["valid"] is True
    assert v_data["chain_depth"] >= 5
    assert v_data["root_hash"] is not None
    assert v_data["tamper_proof"] is True
