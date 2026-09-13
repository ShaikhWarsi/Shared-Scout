import sys
import os
import json
import pytest
from fastapi.testclient import TestClient
from server import app, service
from core.schemas import EvidenceItem

client = TestClient(app)


def test_manifest_endpoint():
    response = client.get("/manifest")
    assert response.status_code == 200
    data = response.json()
    assert data["agent_id"] == "agentscout-v1"
    assert data["purpose"] != ""
    assert data["services"][0]["price_credits"] == 5


def test_purpose_endpoint():
    response = client.get("/purpose")
    assert response.status_code == 200
    data = response.json()
    assert "Independent multi-source factual verification" in data["purpose"]


def test_audit_api_endpoint(monkeypatch):
    def mock_search(claim, question=""):
        if "boat" in claim.lower():
            return [
                EvidenceItem(
                    source_url="https://www.boat-lifestyle.com/products/rockerz-450",
                    source_title="boAt Official Store",
                    snippet="boAt Rockerz 450 is priced at Rs. 1,499 with 15 hours battery.",
                    reliability_weight=1.0
                )
            ]
        elif "realme" in claim.lower():
            return [
                EvidenceItem(
                    source_url="https://buy.realme.com/in/goods/realme-buds-air-5-pro",
                    source_title="Realme Official Catalog",
                    snippet="Realme Buds Air 5 Pro official price is Rs. 4,999 with 50dB ANC.",
                    reliability_weight=1.0
                )
            ]
        return []

    monkeypatch.setattr(service.search_engine, "search_claim", mock_search)

    payload = {
        "question": "Find the best noise cancelling headphones under Rs 3,000 in India.",
        "answer": "boAt Rockerz 450 is Rs. 1,499 with 15h battery. Realme Buds Air 5 Pro is Rs. 2,499 with 50dB ANC."
    }
    response = client.post("/audit", json=payload, headers={"x-sharedos-agent-id": "ArenaAgent-99"})
    assert response.status_code == 200
    data = response.json()
    assert data["reliability"] <= 60
    assert data["verdict_summary"] == "CONTRADICTED"
    assert data["stats"]["contradicted"] >= 1
    assert data["credits_billed"] == 5
    assert "repaired_answer" in data
    
    # Check audit trail retrieval
    trail_res = client.get(f"/api/audit-trail/{data['audit_id']}")
    assert trail_res.status_code == 200
    trail_data = trail_res.json()
    assert trail_data["total_turns"] == 5


def test_repair_endpoint(monkeypatch):
    def mock_search(claim, question=""):
        return [
            EvidenceItem(
                source_url="https://buy.realme.com/in/goods/realme-buds-air-5-pro",
                source_title="Realme Official Store",
                snippet="Realme Buds Air 5 Pro price is Rs. 4,999 with 50dB ANC.",
                reliability_weight=1.0
            )
        ]
    monkeypatch.setattr(service.search_engine, "search_claim", mock_search)

    payload = {
        "question": "Find headphones under 3000",
        "answer": "The Realme Buds Air 5 Pro costs Rs. 2,499 with 50dB ANC."
    }
    response = client.post("/repair", json=payload, headers={"x-sharedos-agent-id": "RepairAgent-1"})
    assert response.status_code == 200
    data = response.json()
    assert data["stats"]["contradicted"] >= 1
    assert "Rs. 4,999" in data["repaired_answer"]


def test_hmac_signature_verification_and_401_rejection(monkeypatch):
    """Verifies that invalid HMAC signatures are rejected with HTTP 401."""
    payload = {
        "question": "Test query",
        "answer": "Sample answer statement."
    }
    
    # Send forged signature
    response = client.post(
        "/audit",
        json=payload,
        headers={
            "x-sharedos-agent-id": "FraudulentAgent",
            "x-sharedos-signature": "forged_hex_signature_1234567890abcdef"
        }
    )
    assert response.status_code == 401
    assert "SharedOS Authentication Failed" in response.json()["detail"]


def test_batch_audit_endpoint():
    payload = [
        {"question": "boAt price", "answer": "boAt Rockerz 450 is Rs. 1,499."},
        {"question": "Python release", "answer": "Python was created by Guido van Rossum in 1991."}
    ]
    response = client.post("/batch-audit", json=payload, headers={"x-sharedos-agent-id": "BatchAgent-1"})
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["credits_billed"] == 5
    assert data[1]["credits_billed"] == 5


def test_ui_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    assert "AgentScout" in response.text
    assert "Challenge an Answer" in response.text
