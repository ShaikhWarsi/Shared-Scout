"""
AgentScout Multi-Node Peer Federation & A2A Dial Handshake Demonstration
Demonstrates cryptographic HMAC turn authorization, outbound peer dialing,
mutual manifest discovery, and cross-node audit execution across 2 simulated SharedNet nodes.
"""

import os
import sys
import json
import time

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sharedos.cloud_adapter import SharedOSCloudAdapter
from sharedos.service import AgentScoutService
from arena.ledger import ArenaLedger
from core.schemas import AuditRequest


def run_2node_federation_demo():
    print("\n" + "=" * 85)
    print("  🌐 SHAREDNET 2-NODE PEER FEDERATION & CRYPTOGRAPHIC DIAL HANDSHAKE")
    print("=" * 85)

    # -----------------------------------------------------------------
    # STEP 1: Initialize Node Alpha and Node Beta
    # -----------------------------------------------------------------
    node_a = SharedOSCloudAdapter(node_id="node-alpha.agentscout.net")
    node_b = SharedOSCloudAdapter(node_id="node-beta.agentscout.net")
    service_b = AgentScoutService()
    ledger_b = ArenaLedger(initial_grant=100)

    print(f"\n[STEP 1] INITIALIZED 2 SHAREDNET PEER NODES:")
    print(f"  Node Alpha (Primary Verifier) : {node_a.node_id} (HMAC Enforced: {node_a.enforce_hmac})")
    print(f"  Node Beta  (Federated Peer)   : {node_b.node_id} (HMAC Enforced: {node_b.enforce_hmac})")

    # -----------------------------------------------------------------
    # STEP 2: Node Alpha dials Node Beta (Outbound HMAC Handshake)
    # -----------------------------------------------------------------
    print(f"\n[STEP 2] NODE ALPHA INITIATES SIGNED DIAL HANDSHAKE TO NODE BETA:")
    handshake_payload = json.dumps({
        "dialer_node": node_a.node_id,
        "purpose": node_a.purpose,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    }, separators=(",", ":")).encode("utf-8")

    headers_from_alpha = node_a.get_auth_headers(node_a.node_id, handshake_payload)
    print(f"  Dial Target     : {node_b.node_id}/purpose")
    print(f"  Auth Header     : x-sharedos-agent-id = {headers_from_alpha['x-sharedos-agent-id']}")
    print(f"  HMAC-SHA256 Sig : {headers_from_alpha['x-sharedos-signature'][:32]}...")

    # -----------------------------------------------------------------
    # STEP 3: Node Beta verifies cryptographic turn authorization
    # -----------------------------------------------------------------
    auth_result = node_b.verify_turn_authorization(headers_from_alpha, handshake_payload)
    print(f"\n[STEP 3] NODE BETA VERIFIES CRYPTOGRAPHIC TURN AUTHORIZATION:")
    print(f"  Authorized      : {auth_result['authorized']}")
    print(f"  HMAC Verified   : {auth_result['hmac_verified']}")
    print(f"  Kernel Turn Idx : {auth_result['kernel_turn_index']}")

    if not auth_result["authorized"]:
        print("  [FAIL] Cryptographic handshake failed.")
        return

    # -----------------------------------------------------------------
    # STEP 4: Mutual Topology Registration
    # -----------------------------------------------------------------
    node_a.register_peer(node_b.node_id, "http://localhost:8001", metadata={"status": "ONLINE_ACTIVE"})
    node_b.register_peer(node_a.node_id, "http://localhost:8000", metadata={"status": "ONLINE_ACTIVE"})
    print(f"\n[STEP 4] MUTUAL PEER FEDERATION ESTABLISHED:")
    print(f"  Node Alpha Registered Peers : {list(node_a.registered_peers.keys())}")
    print(f"  Node Beta Registered Peers  : {list(node_b.registered_peers.keys())}")

    # -----------------------------------------------------------------
    # STEP 5: Cross-Node Verification Audit & Ledger Metering
    # -----------------------------------------------------------------
    print(f"\n[STEP 5] NODE ALPHA DISPATCHES AUDIT PAYLOAD TO NODE BETA:")
    query = "Find Sony WH-1000XM5 battery life"
    flawed_answer = "Sony WH-1000XM5 features 40 hours continuous music playback with ANC enabled."
    audit_req = AuditRequest(question=query, answer=flawed_answer)
    audit_payload_bytes = json.dumps(audit_req.model_dump(), separators=(",", ":")).encode("utf-8")
    audit_headers = node_a.get_auth_headers(node_a.node_id, audit_payload_bytes)

    # Node B authorizes & bills
    auth_audit = node_b.verify_turn_authorization(audit_headers, audit_payload_bytes)
    assert auth_audit["authorized"]

    success, bal, msg = ledger_b.deduct_credits(node_a.node_id, amount=5, service_name="POST /audit")
    response, trail = service_b.execute_audit(audit_req, caller_agent_id=node_a.node_id)
    response.remaining_credits = bal

    print(f"  Audit Execution : {response.verdict_summary} (Reliability: {response.reliability} / 100)")
    print(f"  Billed To Caller: 5 Arena Credits")
    print(f"  Node Alpha Bal  : {bal} Arena Credits remaining on Node Beta Ledger")
    print(f"  Repaired Output : {response.repaired_answer}")

    print("\n" + "=" * 85)
    print("  [SUCCESS] 2-Node SharedNet Federation & Authenticated Handshake Verified!")
    print("=" * 85 + "\n")


if __name__ == "__main__":
    run_2node_federation_demo()
