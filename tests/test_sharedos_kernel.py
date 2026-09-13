"""
Unit Tests for SharedOS Kernel, Capability Authorizer, Grant Store, and Durable Audit Sink
"""

import os
import json
import pytest
import tempfile
import time

from sharedos.grant_store import CapabilityGrantStore, GrantStoreOutageError
from sharedos.cloud_audit_sink import DurableSharedOSAuditSink
from sharedos.kernel import SharedOSKernel, CapabilityAuthorizer, FilesResourceProvider


@pytest.fixture
def temp_store_dir(tmp_path):
    store_dir = tmp_path / ".sharedos"
    store_dir.mkdir()
    return str(store_dir)


def test_grant_store_lifecycle(temp_store_dir):
    store_file = os.path.join(temp_store_dir, "grants.json")
    store = CapabilityGrantStore(store_path=store_file)
    
    # Check default seed grants loaded
    ctx = {
        "namespaceId": "agentscout.sharedos.net",
        "actor": {"kind": "agent", "agentId": "agentscout-firewall"},
        "authority": {"kind": "human", "userId": "arena-authority-admin"},
        "now": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    }
    grants = store.load_active_grants_for(ctx)
    assert len(grants) >= 1
    assert grants[0]["id"] == "grant-agentscout-core-v1"

    # Issue a new grant
    new_grant = {
        "id": "grant-custom-test",
        "namespaceId": "agentscout.sharedos.net",
        "subject": {"kind": "agent", "agentId": "test-bot"},
        "issuer": {"kind": "human", "userId": "arena-authority-admin"},
        "capabilities": [
            {
                "resource": {"namespace": "custom", "path": ["ping"]},
                "actions": ["invoke"],
                "scope": "exact"
            }
        ],
        "constraints": {"purposes": ["testing"], "maxUses": 2}
    }
    store.issue_grant(new_grant)

    # Verify query for test-bot
    bot_ctx = {
        "namespaceId": "agentscout.sharedos.net",
        "actor": {"kind": "agent", "agentId": "test-bot"},
        "authority": {"kind": "human", "userId": "arena-authority-admin"},
        "now": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    }
    bot_grants = store.load_active_grants_for(bot_ctx)
    assert len(bot_grants) == 1

    # Consume use
    assert store.try_consume_use("grant-custom-test") is True
    assert store.try_consume_use("grant-custom-test") is True
    assert store.try_consume_use("grant-custom-test") is False  # maxUses exhausted

    # Revoke grant
    assert store.revoke_grant("grant-custom-test") is True
    assert len(store.load_active_grants_for(bot_ctx)) == 0


def test_grant_store_outage_throws(temp_store_dir):
    store_file = os.path.join(temp_store_dir, "test_grants.json")
    store = CapabilityGrantStore(store_path=store_file)
    assert os.path.exists(store_file)
    
    # Simulate an outage by corrupting the store file
    with open(store_file, "w", encoding="utf-8") as f:
        f.write("INVALID_JSON_CORRUPTED_STORE_DATA{")
    
    ctx = {
        "namespaceId": "agentscout.sharedos.net",
        "actor": {"kind": "agent", "agentId": "agentscout-firewall"},
        "authority": {"kind": "human", "userId": "arena-authority-admin"}
    }
    
    # Must throw GrantStoreOutageError rather than silently returning empty list
    with pytest.raises(GrantStoreOutageError):
        store.load_active_grants_for(ctx)


def test_authorizer_fail_closed_on_outage(temp_store_dir):
    store_file = os.path.join(temp_store_dir, "missing_grants.json")
    store = CapabilityGrantStore(store_path=store_file)
    if os.path.exists(store_file):
        os.remove(store_file)

    authorizer = CapabilityAuthorizer(store)
    ctx = {
        "namespaceId": "agentscout.sharedos.net",
        "actor": {"kind": "agent", "agentId": "agentscout-firewall"},
        "authority": {"kind": "human", "userId": "arena-authority-admin"}
    }

    decision = authorizer.authorize(ctx, "agentscout", ["firewall", "gate"], "evaluate")
    assert decision["allowed"] is False
    assert decision["reasonCode"] == "authority_unavailable"
    assert decision["failClosed"] is True


def test_kernel_files_resource_provider_containment(temp_store_dir):
    provider = FilesResourceProvider(root_dir=temp_store_dir)
    
    # Create test file
    bench_dir = os.path.join(temp_store_dir, "benchmarks")
    os.makedirs(bench_dir, exist_ok=True)
    test_file = os.path.join(bench_dir, "sample.txt")
    with open(test_file, "w", encoding="utf-8") as f:
        f.write("SharedOS Benchmark Evidence Ground Truth")

    # Read inside sandbox
    read_res = provider.invoke({
        "action": "read",
        "resource": {"namespace": "files", "path": ["benchmarks", "sample.txt"]}
    })
    assert read_res["status"] == "succeeded"
    assert "SharedOS Benchmark Evidence Ground Truth" in read_res["output"]["content"]

    # Traversal escape outside sandbox must be denied
    escape_res = provider.invoke({
        "action": "read",
        "resource": {"namespace": "files", "path": ["..", "..", "windows", "system32"]}
    })
    assert escape_res["status"] == "denied"
    assert escape_res["reasonCode"] == "sandbox_violation"


def test_kernel_3_gate_authorization(temp_store_dir):
    store_file = os.path.join(temp_store_dir, "grants.json")
    audit_file = os.path.join(temp_store_dir, "audit_log.jsonl")
    
    store = CapabilityGrantStore(store_path=store_file)
    sink = DurableSharedOSAuditSink(persist_dir=temp_store_dir)
    kernel = SharedOSKernel(grant_store=store, audit_sink=sink)

    ctx = {
        "namespaceId": "agentscout.sharedos.net",
        "actor": {"kind": "agent", "agentId": "agentscout-firewall"},
        "authority": {"kind": "human", "userId": "arena-authority-admin"},
        "purpose": "pre-action-firewall",
        "enabledToolNamespaces": ["files", "agentscout"],
        "now": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    }

    # 1. Gate 1: Non-existent tool -> tool_not_found
    res1 = kernel.invoke_tool(ctx, {"tool": "ghost.nonexistent", "arguments": {}})
    assert res1["status"] == "denied"
    assert res1["reasonCode"] == "tool_not_found"

    # 2. Gate 2: Disabled namespace -> namespace_disabled
    ctx_no_files = dict(ctx, enabledToolNamespaces=["agentscout"])
    res2 = kernel.invoke_tool(ctx_no_files, {"tool": "files.read", "arguments": {"path": ["benchmarks"]}})
    assert res2["status"] == "denied"
    assert res2["reasonCode"] == "namespace_disabled"

    # 3. Gate 3: Out of scope capability -> no_matching_grant
    res3 = kernel.invoke_tool(ctx, {"tool": "files.read", "arguments": {"path": ["forbidden_dir", "secret.json"]}})
    assert res3["status"] == "denied"
    assert res3["reasonCode"] == "no_matching_grant"


def test_durable_audit_sink_chain_and_outbox(temp_store_dir):
    sink = DurableSharedOSAuditSink(persist_dir=temp_store_dir)
    
    # Record multiple decision events
    rec1 = sink.record_decision("tool.invoke", {"namespace": "test"}, {"allowed": True})
    rec2 = sink.record_decision("tool.invoke", {"namespace": "test"}, {"allowed": False})
    
    assert rec2["previous_hash"] == rec1["event_hash"]
    assert os.path.exists(sink.log_file)
    assert os.path.exists(sink.outbox_file)

    # Verify outbox flush without API key retains outbox safely
    flush_res = sink.flush_outbox(api_key="")
    assert flush_res["status"] == "SKIPPED_NO_API_KEY"
    assert flush_res["pending"] >= 2