"""
Tests for AgentScout Native SharedNet Arena Room Watcher Adapter
Verifies handling of stdin JSON batches, structured requests, chat mentions,
credit debiting, and egress clearance dockets.
"""

import json
import pytest
from agentscout_arena_watcher import ArenaRoomWatcher


@pytest.fixture
def watcher():
    return ArenaRoomWatcher()


def test_watcher_manifest_request(watcher):
    batch = {
        "room_id": "rom_test_01",
        "member_id": "i_agentscout_test",
        "trigger": "message",
        "messages": [
            {
                "id": "msg_01",
                "content": json.dumps({
                    "type": "agentscout.service.request.v1",
                    "request_id": "req-manifest-01",
                    "service": "manifest"
                }),
                "sender": {"member_id": "i_peer_buyer", "name": "PeerBuyer"}
            }
        ]
    }
    reply_raw = watcher.process_batch(batch)
    assert reply_raw is not None
    data = json.loads(reply_raw)
    assert data["status"] == "SUCCESS"
    assert "pricing" in data
    assert "manifest" in data


def test_watcher_free_trial(watcher):
    batch = {
        "room_id": "rom_test_01",
        "member_id": "i_agentscout_test",
        "trigger": "message",
        "messages": [
            {
                "id": "msg_02",
                "content": json.dumps({
                    "type": "agentscout.service.request.v1",
                    "request_id": "req-trial-01",
                    "service": "free_trial",
                    "input": {
                        "question": "Continuous ANC battery of Sony WH-1000XM5?",
                        "answer": "The Sony WH-1000XM5 headphones offer up to 40 hours of continuous playback with ANC enabled."
                    }
                }),
                "sender": {"member_id": "i_trial_user", "name": "TrialUser"}
            }
        ]
    }
    reply_raw = watcher.process_batch(batch)
    assert reply_raw is not None
    data = json.loads(reply_raw)
    assert data["service"] == "free_trial"
    assert data["credits_billed"] == 0
    assert data["status"] == "CONTRADICTED"
    assert "30 hours" in data["repaired_answer"]


def test_watcher_firewall_gate_repaired_and_approved(watcher):
    batch = {
        "room_id": "rom_test_01",
        "member_id": "i_agentscout_test",
        "trigger": "message",
        "messages": [
            {
                "id": "msg_03",
                "content": json.dumps({
                    "type": "agentscout.service.request.v1",
                    "request_id": "req-gate-01",
                    "service": "firewall_gate",
                    "input": {
                        "question": "What is the continuous music playback battery life of the Sony WH-1000XM5?",
                        "answer": "The Sony WH-1000XM5 headphones offer up to 40 hours of continuous music playback with ANC enabled.",
                        "auto_repair": True
                    }
                }),
                "sender": {"member_id": "i_gate_caller", "name": "GateCaller"}
            }
        ]
    }
    reply_raw = watcher.process_batch(batch)
    assert reply_raw is not None
    data = json.loads(reply_raw)
    assert data["service"] == "firewall_gate"
    assert data["status"] == "REPAIRED_AND_APPROVED"
    assert data["initial_reliability"] == 0
    assert data["final_reliability"] == 100
    assert "30 hours" in data["safe_to_ship_answer"]
    assert "agentscout-docket-" in data["docket_id"]
    assert data["egress_clearance"] == "CLEARED_FOR_DEPLOYMENT"
    assert data["credits_billed"] == 5


def test_watcher_chat_mention_trial(watcher):
    batch = {
        "room_id": "rom_test_01",
        "member_id": "i_agentscout_test",
        "trigger": "message",
        "messages": [
            {
                "id": "msg_04",
                "content": "@agentscout trial The Sony WH-1000XM5 has 40 hours of battery life with ANC on.",
                "sender": {"member_id": "i_human_agent", "name": "TraderBob"}
            }
        ]
    }
    reply_text = watcher.process_batch(batch)
    assert reply_text is not None
    assert "@TraderBob" in reply_text
    assert "CONTRADICTED" in reply_text
    assert "30 hours" in reply_text


def test_watcher_ignore_self_message(watcher):
    batch = {
        "room_id": "rom_test_01",
        "member_id": "i_agentscout_test",
        "trigger": "message",
        "messages": [
            {
                "id": "msg_self",
                "content": "@agentscout trial Should ignore my own echo",
                "sender": {"member_id": "i_agentscout_test", "name": "AgentScout"}
            }
        ]
    }
    reply = watcher.process_batch(batch)
    assert reply is None
