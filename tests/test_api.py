import sys
import os
import pytest
from fastapi.testclient import TestClient
from server import app

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

def test_audit_api_endpoint():
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
    
    # Check audit trail retrieval
    trail_res = client.get(f"/api/audit-trail/{data['audit_id']}")
    assert trail_res.status_code == 200
    trail_data = trail_res.json()
    assert trail_data["total_turns"] == 5

def test_ui_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    assert "AgentScout" in response.text
    assert "Challenge an Answer" in response.text
