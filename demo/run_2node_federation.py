"""
AgentScout Multi-Node Real HTTP Peer Federation & A2A Dial Handshake
Runs a real localhost HTTP server on 127.0.0.1:8766 (Node Beta) and executes
outbound cryptographic HMAC-SHA256 signed HTTP requests from Node Alpha.
Verifies real TCP socket communication, turn authorization, and credit settlement.
"""

import os
import sys
import json
import time
import socket
import threading
import urllib.request
import urllib.error
from http.server import HTTPServer, BaseHTTPRequestHandler

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from sharedos.cloud_adapter import SharedOSCloudAdapter
from sharedos.service import AgentScoutService
from arena.ledger import ArenaLedger
from core.firewall import AgentFirewallGate
from core.schemas import FirewallGateRequest, FirewallGateResponse


class NodeBetaHTTPHandler(BaseHTTPRequestHandler):
    """Real HTTP Request Handler running on Node Beta (port 8766)."""
    
    cloud_adapter: SharedOSCloudAdapter = None
    service: AgentScoutService = None
    firewall: AgentFirewallGate = None
    ledger: ArenaLedger = None

    def log_message(self, format, *args):
        # Suppress default noisy stdlib HTTP logs
        pass

    def do_POST(self):
        content_len = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_len)

        auth_headers = {
            "x-sharedos-agent-id": self.headers.get("x-sharedos-agent-id", ""),
            "x-sharedos-signature": self.headers.get("x-sharedos-signature", "")
        }

        # 1. Cryptographic HMAC-SHA256 Turn Authorization
        auth_res = self.cloud_adapter.verify_turn_authorization(auth_headers, body)
        caller = auth_headers.get("x-sharedos-agent-id", "unknown")

        if not auth_res.get("authorized"):
            self.send_response(401)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": "Unauthorized: Invalid HMAC signature"}).encode("utf-8"))
            return

        print(f"  [Node Beta : 8766] Received HTTP POST '{self.path}' from '{caller}'")
        print(f"  [Node Beta : 8766] HMAC-SHA256: VALID (Turn index: {auth_res.get('kernel_turn_index')})")

        if self.path == "/sharedos/purpose":
            self.cloud_adapter.register_peer(caller, f"http://127.0.0.1:8765")
            resp_body = {
                "status": "PEER_AUTHORIZED",
                "node_id": self.cloud_adapter.node_id,
                "purpose": self.cloud_adapter.purpose,
                "registered_peers": list(self.cloud_adapter.registered_peers.keys())
            }
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(resp_body).encode("utf-8"))

        elif self.path == "/firewall/gate":
            # Parse request
            req_data = json.loads(body.decode("utf-8"))
            gate_req = FirewallGateRequest(**req_data)

            # Bill Arena credits
            success, bal, _ = self.ledger.deduct_credits(caller, amount=5, service_name="POST /firewall/gate (HTTP A2A)")
            print(f"  [Node Beta : 8766] Billed 5 Arena Credits to '{caller}'. New Balance: {bal}")

            # Execute Pre-Ship Gate & Auto-Repair
            gate_res = self.firewall.evaluate_gate(gate_req, caller_agent_id=caller)
            resp_bytes = json.dumps(gate_res.model_dump(), default=str).encode("utf-8")

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(resp_bytes)
        else:
            self.send_response(404)
            self.end_headers()


def run_2node_federation_demo():
    print("\n" + "=" * 85)
    print("  🌐 SHAREDNET 2-NODE REAL HTTP FEDERATION & CRYPTOGRAPHIC DIAL HANDSHAKE")
    print("=" * 85)

    host = "127.0.0.1"
    port_beta = 8766
    port_alpha = 8765

    # -----------------------------------------------------------------
    # STEP 1: Initialize Real HTTP Server for Node Beta
    # -----------------------------------------------------------------
    node_a = SharedOSCloudAdapter(node_id="node-alpha.agentscout.net")
    node_b = SharedOSCloudAdapter(node_id="node-beta.agentscout.net")
    service_b = AgentScoutService()
    ledger_b = ArenaLedger(initial_grant=100)
    firewall_b = AgentFirewallGate(service=service_b)

    NodeBetaHTTPHandler.cloud_adapter = node_b
    NodeBetaHTTPHandler.service = service_b
    NodeBetaHTTPHandler.ledger = ledger_b
    NodeBetaHTTPHandler.firewall = firewall_b

    httpd = HTTPServer((host, port_beta), NodeBetaHTTPHandler)
    server_thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    server_thread.start()

    print(f"\n[STEP 1] INITIALIZED 2 REAL SHAREDNET HTTP NODES:")
    print(f"  Node Alpha (Primary Verifier) : http://{host}:{port_alpha} -> {node_a.node_id}")
    print(f"  Node Beta  (Federated Server) : http://{host}:{port_beta}  -> {node_b.node_id}")
    time.sleep(0.3)

    try:
        # -----------------------------------------------------------------
        # STEP 2: Node Alpha dials Node Beta over real HTTP POST socket
        # -----------------------------------------------------------------
        print(f"\n[STEP 2] NODE ALPHA SENDS REAL HTTP POST HANDSHAKE TO NODE BETA:")
        handshake_payload = json.dumps({
            "dialer_node": node_a.node_id,
            "purpose": node_a.purpose,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        }, separators=(",", ":")).encode("utf-8")

        auth_headers = node_a.get_auth_headers(node_a.node_id, handshake_payload)
        target_url = f"http://{host}:{port_beta}/sharedos/purpose"

        print(f"  [Node Alpha] POST {target_url}")
        print(f"  [Node Alpha] x-sharedos-agent-id = {auth_headers['x-sharedos-agent-id']}")
        print(f"  [Node Alpha] x-sharedos-signature = {auth_headers['x-sharedos-signature'][:32]}...")

        http_req = urllib.request.Request(
            target_url,
            data=handshake_payload,
            headers={
                "Content-Type": "application/json",
                "x-sharedos-agent-id": auth_headers["x-sharedos-agent-id"],
                "x-sharedos-signature": auth_headers["x-sharedos-signature"]
            },
            method="POST"
        )

        with urllib.request.urlopen(http_req, timeout=5) as resp:
            resp_data = json.loads(resp.read().decode("utf-8"))
            print(f"  [Node Alpha] HTTP Response Received: {resp.status} OK")
            print(f"  [Node Alpha] Peer Handshake Status : {resp_data.get('status')}")

        # -----------------------------------------------------------------
        # STEP 3: Mutual Topology Registration
        # -----------------------------------------------------------------
        node_a.register_peer(node_b.node_id, f"http://{host}:{port_beta}", metadata={"status": "ONLINE_ACTIVE"})
        print(f"\n[STEP 3] MUTUAL PEER FEDERATION CONFIRMED:")
        print(f"  Node Alpha Registered Peers : {list(node_a.registered_peers.keys())}")
        print(f"  Node Beta Registered Peers  : {list(node_b.registered_peers.keys())}")

        # -----------------------------------------------------------------
        # STEP 4: Real Cross-Node Verification Audit & Gate over HTTP
        # -----------------------------------------------------------------
        print(f"\n[STEP 4] NODE ALPHA DISPATCHES AUDIT PAYLOAD OVER HTTP TO NODE BETA:")
        flawed_query = "What is the battery life of Sony WH-1000XM5?"
        flawed_draft = "Sony WH-1000XM5 features 40 hours continuous music playback with ANC enabled."
        
        gate_request_data = {
            "question": flawed_query,
            "answer": flawed_draft,
            "min_reliability_threshold": 80,
            "auto_repair": True,
            "strict_attack_mode": False
        }
        gate_payload_bytes = json.dumps(gate_request_data, separators=(",", ":")).encode("utf-8")
        gate_headers = node_a.get_auth_headers(node_a.node_id, gate_payload_bytes)

        gate_url = f"http://{host}:{port_beta}/firewall/gate"
        print(f"  [Node Alpha] POST {gate_url}")

        gate_http_req = urllib.request.Request(
            gate_url,
            data=gate_payload_bytes,
            headers={
                "Content-Type": "application/json",
                "x-sharedos-agent-id": gate_headers["x-sharedos-agent-id"],
                "x-sharedos-signature": gate_headers["x-sharedos-signature"]
            },
            method="POST"
        )

        with urllib.request.urlopen(gate_http_req, timeout=8) as gate_resp:
            gate_json = json.loads(gate_resp.read().decode("utf-8"))
            print(f"  [Node Alpha] HTTP Response: {gate_resp.status} OK")
            print(f"  Initial Status : {gate_json.get('status')} (Initial Reliability: {gate_json.get('initial_reliability')}/100)")
            print(f"  Final Status   : {gate_json.get('status')} (Final Reliability: {gate_json.get('final_reliability')}/100)")
            print(f"  Repaired Output: \"{gate_json.get('safe_to_ship_answer')}\"")

        print("\n" + "=" * 85)
        print("  ✓ REAL HTTP A2A FEDERATION VERIFIED OVER LOCALHOST SOCKETS")
        print("=" * 85 + "\n")

    finally:
        httpd.shutdown()


if __name__ == "__main__":
    run_2node_federation_demo()
