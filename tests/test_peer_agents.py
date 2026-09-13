import json
import pytest
from fastapi.testclient import TestClient
from server import app, cloud_adapter

client = TestClient(app)

def test_three_peer_agents_concurrent_audits():
    peers = [
        ("ShoppingBot-Alpha", "Find headphones", "boAt Rockerz 450 is Rs. 1,499 with 15h battery."),
        ("TechReviewer-Beta", "Sony XM5 battery", "Sony WH-1000XM5 features 40 hours battery life with ANC enabled."),
        ("MarketResearch-Gamma", "Realme pricing", "Realme Buds Air 5 Pro provides 50dB ANC and costs Rs. 2,499.")
    ]

    for agent_id, q, a in peers:
        payload = {"question": q, "answer": a}
        raw_body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
        headers = cloud_adapter.get_auth_headers(agent_id, raw_body)
        resp = client.post(
            "/audit",
            json=payload,
            headers=headers
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["credits_billed"] == 5
        assert "as-audit-" in data["audit_id"]
        assert data["execution_latency_ms"] < 5000

