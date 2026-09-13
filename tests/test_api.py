import sys
import os
import json
import pytest
from fastapi.testclient import TestClient
from server import app, service, cloud_adapter, ledger
from core.schemas import EvidenceItem

client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_test_ledger():
    ledger.accounts = {}
    ledger.transactions = []


def get_signed_headers(agent_id: str, payload_dict: dict) -> dict:
    raw_body = json.dumps(payload_dict, separators=(",", ":")).encode("utf-8")
    return cloud_adapter.get_auth_headers(agent_id, raw_body)


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


def test_credits_endpoint():
    caller_id = "Agent-Ledger-Test-01"
    response = client.get(f"/credits/{caller_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["caller_id"] == caller_id
    assert data["credit_balance"] == 100
    assert data["status"] == "ACTIVE"


def test_topup_endpoint():
    caller_id = "Agent-Topup-Test"
    response = client.post(f"/credits/{caller_id}/topup?amount=50")
    assert response.status_code == 200
    data = response.json()
    assert data["caller_id"] == caller_id
    assert data["credit_balance"] == 150
    assert data["status"] == "TOPUP_SUCCESS"


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
    caller = "ArenaAgent-99"
    headers = get_signed_headers(caller, payload)
    response = client.post("/audit", json=payload, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["reliability"] <= 60
    assert data["verdict_summary"] == "CONTRADICTED"
    assert data["stats"]["contradicted"] >= 1
    assert data["credits_billed"] == 5
    assert "repaired_answer" in data
    
    # Check that credits were deducted
    bal_res = client.get(f"/credits/{caller}")
    assert bal_res.json()["credit_balance"] == 95

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
    caller = "RepairAgent-1"
    headers = get_signed_headers(caller, payload)
    response = client.post("/repair", json=payload, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["stats"]["contradicted"] >= 1
    assert "Rs. 4,999" in data["repaired_answer"]


def test_hmac_signature_verification_and_401_rejection():
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


def test_insufficient_credits_403_rejection():
    """Verifies that agents with 0 or insufficient credits receive HTTP 403."""
    caller = "BrokeAgent-007"
    ledger.accounts[caller] = 2  # Less than required 5 credits
    
    payload = {
        "question": "Test query",
        "answer": "Sample answer statement."
    }
    headers = get_signed_headers(caller, payload)
    response = client.post("/audit", json=payload, headers=headers)
    assert response.status_code == 403
    assert "Insufficient Arena Credits" in response.json()["detail"]


def test_batch_audit_endpoint():
    payload = [
        {"question": "boAt price", "answer": "boAt Rockerz 450 is Rs. 1,499."},
        {"question": "Python release", "answer": "Python was created by Guido van Rossum in 1991."}
    ]
    caller = "BatchAgent-1"
    raw_body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    headers = cloud_adapter.get_auth_headers(caller, raw_body)
    response = client.post("/batch-audit", json=payload, headers=headers)
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


def test_ui_repair_interactive_endpoint():
    payload = {
        "question": "boAt price query",
        "answer": "boAt Rockerz 450 is Rs. 1,499."
    }
    response = client.post("/api/ui/repair", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["audit_id"].startswith("as-audit-")
    assert "remaining_credits" in data


def test_ledger_export_csv_endpoint():
    # Make a call to generate ledger activity
    caller = "ExportTestAgent"
    payload = {"question": "test", "answer": "test statement"}
    headers = get_signed_headers(caller, payload)
    client.post("/audit", json=payload, headers=headers)

    response = client.get("/ledger/export")
    assert response.status_code == 200
    assert "timestamp,caller_id,amount,type,details,balance_after" in response.text
    assert "ExportTestAgent" in response.text


def test_sharednet_peers_endpoints():
    # Test GET peers
    res = client.get("/sharednet/peers")
    assert res.status_code == 200
    data = res.json()
    assert "peers_count" in data
    assert "seed_peers" in data

