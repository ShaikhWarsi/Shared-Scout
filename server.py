"""
AgentScout FastAPI Server, SharedNet Gateway, Autonomous Repair Router, HMAC Auth & Rate Limiter
"""

import os
import json
import time
from typing import List
from collections import defaultdict
from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.responses import HTMLResponse, JSONResponse, PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware

from core.schemas import (
    AuditRequest,
    AuditResponse,
    AuditMode,
    FirewallGateRequest,
    FirewallGateResponse
)
from sharedos.service import AgentScoutService
from sharedos.manifest import SHAREDOS_MANIFEST, SHAREDOS_PURPOSE_STRING
from sharedos.cloud_adapter import SharedOSCloudAdapter
from arena.pitch_bot import ArenaPitchAgent
from arena.ledger import ArenaLedger
from core.firewall import AgentFirewallGate

app = FastAPI(
    title="AgentScout - SharedOS Verification Layer",
    version="1.3.0",
    description="Independent verification, adversarial attack testing, and Pre-Ship CI/CD Firewall Gate for AI agents on SharedOS."
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

service = AgentScoutService()
cloud_adapter = SharedOSCloudAdapter()
pitch_agent = ArenaPitchAgent()
ledger = ArenaLedger()
firewall_gate = AgentFirewallGate(service=service)

# In-Memory Rate Limiter (Max 60 requests/minute per caller agent)
RATE_LIMIT = 60
request_timestamps = defaultdict(list)


def check_rate_limit(caller_id: str):
    now = time.time()
    timestamps = [t for t in request_timestamps[caller_id] if now - t < 60.0]
    if len(timestamps) >= RATE_LIMIT:
        raise HTTPException(status_code=429, detail="Rate limit exceeded (Max 60 audits/min)")
    timestamps.append(now)
    request_timestamps[caller_id] = timestamps


async def authenticate_caller(request: Request) -> str:
    caller_id = request.headers.get("x-sharedos-agent-id", "peer-agent-node")
    check_rate_limit(caller_id)
    raw_body = await request.body()
    auth_res = cloud_adapter.verify_turn_authorization(dict(request.headers), raw_body)
    if not auth_res["authorized"]:
        raise HTTPException(
            status_code=401,
            detail="SharedOS Authentication Failed: Invalid or missing x-sharedos-signature HMAC token."
        )
    # Check credit balance
    balance = ledger.get_balance(caller_id)
    if balance < 5:
        raise HTTPException(
            status_code=403,
            detail=f"Forbidden: Insufficient Arena Credits for agent '{caller_id}'. Balance: {balance}, Required: 5."
        )
    return caller_id


@app.get("/manifest")
def get_manifest():
    return JSONResponse(content=SHAREDOS_MANIFEST)


@app.get("/purpose")
def get_purpose():
    return JSONResponse(content={
        "agent_id": "agentscout-v1",
        "purpose": SHAREDOS_PURPOSE_STRING,
        "status": "ACTIVE_VERIFIED"
    })


@app.get("/node-info")
def get_node_info():
    return JSONResponse(content=cloud_adapter.get_node_status())


@app.get("/credits/{caller_id}")
def get_caller_credits(caller_id: str):
    """Returns the live Arena credits balance and transaction ledger for a caller agent."""
    return JSONResponse(content=ledger.get_account_summary(caller_id))


@app.get("/ledger/export", response_class=PlainTextResponse)
def export_ledger_csv():
    """Exports the entire Arena transaction ledger as CSV for audit inspection."""
    lines = ["timestamp,caller_id,amount,type,details,balance_after"]
    for tx in ledger.transactions:
        clean_details = str(tx.get("details", "")).replace(",", ";")
        lines.append(f"{tx.get('timestamp','')},{tx.get('caller_id','')},{tx.get('amount','')},{tx.get('type','')},{clean_details},{tx.get('balance_after','')}")
    return "\n".join(lines)


@app.post("/credits/{caller_id}/topup")
def topup_caller_credits(caller_id: str, amount: int = 50):
    """Credits Arena tokens to the specified agent account."""
    new_balance = ledger.add_credits(caller_id, amount, reason="MANUAL_TOPUP")
    return JSONResponse(content={
        "caller_id": caller_id,
        "credit_balance": new_balance,
        "status": "TOPUP_SUCCESS"
    })


@app.post("/firewall/gate", response_model=FirewallGateResponse)
async def evaluate_firewall_gate(req: FirewallGateRequest, request: Request, caller_id: str = Depends(authenticate_caller)):
    """
    Pre-Ship CI/CD Firewall Gate for Autonomous Agents.
    Blocks hallucinated responses below safety threshold from reaching users,
    auto-repairs contradictions, and re-evaluates before granting shipment clearance.
    """
    try:
        success, bal, msg = ledger.deduct_credits(caller_id, amount=5, service_name="POST /firewall/gate")
        if not success:
            raise HTTPException(status_code=403, detail=msg)
        gate_res = firewall_gate.evaluate_gate(req, caller_agent_id=caller_id)
        return gate_res
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Firewall Gate execution error: {str(e)}")


@app.post("/attack", response_model=AuditResponse)
async def attack_answer(req: AuditRequest, request: Request, caller_id: str = Depends(authenticate_caller)):
    """
    Adversarial Attack Mode: Actively hunts for conflicting specifications,
    superseded facts, and counter-evidence to stress-test an agent's answer.
    """
    req.mode = AuditMode.ATTACK
    try:
        success, bal, msg = ledger.deduct_credits(caller_id, amount=5, service_name="POST /attack")
        if not success:
            raise HTTPException(status_code=403, detail=msg)
        response, _ = service.execute_audit(req, caller_agent_id=caller_id)
        response.remaining_credits = bal
        return response
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Attack execution error: {str(e)}")


@app.post("/api/ui/repair", response_model=AuditResponse)
async def ui_repair_interactive(req: AuditRequest):
    """
    Dedicated local interactive playground route for browser UI demonstration.
    Supports both standard VERIFY mode and adversarial ATTACK mode with Pre-Ship Firewall Gate tagging.
    """
    caller_id = "local-browser-session"
    check_rate_limit(caller_id)
    success, bal, msg = ledger.deduct_credits(caller_id, amount=5, service_name="POST /api/ui/repair")
    if not success:
        raise HTTPException(status_code=403, detail=msg)
    response, _ = service.execute_audit(req, caller_agent_id=caller_id)
    response.remaining_credits = bal
    return response


@app.get("/sharednet/peers")
def get_peer_network():
    """Returns the current registered SharedNet peer topology."""
    return JSONResponse(content={
        "node_id": cloud_adapter.node_id,
        "peers_count": len(cloud_adapter.registered_peers),
        "peers": cloud_adapter.registered_peers,
        "seed_peers": cloud_adapter.seed_peers
    })


@app.post("/sharednet/peers/register")
async def register_peer_node(request: Request, caller_id: str = Depends(authenticate_caller)):
    """Registers a peer node into the local SharedNet routing table."""
    try:
        data = await request.json()
        peer_id = data.get("peer_id", caller_id)
        peer_url = data.get("peer_url", "")
        metadata = data.get("metadata", {})
        res = cloud_adapter.register_peer(peer_id, peer_url, metadata)
        return JSONResponse(content={"status": "REGISTERED", "peer": res})
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Peer registration failed: {str(e)}")


@app.post("/sharednet/peers/dial")
def dial_peer_node(peer_url: str):
    """Actively dials an outbound SharedNet peer to perform handshake."""
    res = cloud_adapter.dial_peer_node(peer_url)
    return JSONResponse(content=res)


@app.post("/audit", response_model=AuditResponse)
async def audit_answer(req: AuditRequest, request: Request, caller_id: str = Depends(authenticate_caller)):
    try:
        success, bal, msg = ledger.deduct_credits(caller_id, amount=5, service_name="POST /audit")
        if not success:
            raise HTTPException(status_code=403, detail=msg)
        response, trail = service.execute_audit(req, caller_agent_id=caller_id)
        response.remaining_credits = bal
        return response
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Audit execution error: {str(e)}")


@app.post("/repair", response_model=AuditResponse)
async def repair_answer(req: AuditRequest, request: Request, caller_id: str = Depends(authenticate_caller)):
    """Executes audit and returns verified auto-repaired answer text."""
    try:
        success, bal, msg = ledger.deduct_credits(caller_id, amount=5, service_name="POST /repair")
        if not success:
            raise HTTPException(status_code=403, detail=msg)
        response, _ = service.execute_audit(req, caller_agent_id=caller_id)
        response.remaining_credits = bal
        return response
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Repair execution error: {str(e)}")


@app.post("/batch-audit", response_model=List[AuditResponse])
async def batch_audit_answers(requests: List[AuditRequest], request: Request, caller_id: str = Depends(authenticate_caller)):
    """Audits multiple agent answers in a single batch call."""
    req_count = min(len(requests), 5)
    total_fee = req_count * 5
    success, bal, msg = ledger.deduct_credits(caller_id, amount=total_fee, service_name="POST /batch-audit")
    if not success:
        raise HTTPException(status_code=403, detail=msg)

    results = []
    for req in requests[:5]:  # Cap at 5 per batch for safety
        res, _ = service.execute_audit(req, caller_agent_id=caller_id)
        res.remaining_credits = bal
        results.append(res)
    return results


@app.get("/api/audit-trail/{audit_id}")
def get_audit_trail(audit_id: str):
    if audit_id not in service.audit_history:
        raise HTTPException(status_code=404, detail="Audit ID not found in local SharedOS trail cache")
    return JSONResponse(content=service.audit_history[audit_id].export_trail())


@app.get("/api/fixtures")
def get_demo_fixtures():
    fixtures_path = os.path.join(os.path.dirname(__file__), "demo", "demo_fixtures.json")
    if os.path.exists(fixtures_path):
        with open(fixtures_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


@app.get("/api/pitch")
def get_pitch_info():
    return {
        "pitch": pitch_agent.get_elevator_pitch(),
        "service_price": pitch_agent.service_price,
        "node_id": pitch_agent.node_id
    }


@app.get("/", response_class=HTMLResponse)
def serve_ui():
    ui_path = os.path.join(os.path.dirname(__file__), "ui", "index.html")
    if os.path.exists(ui_path):
        with open(ui_path, "r", encoding="utf-8") as f:
            return f.read()
    return "<h1>AgentScout UI file not found</h1>"


if __name__ == "__main__":
    import argparse
    import uvicorn
    
    parser = argparse.ArgumentParser(description="AgentScout SharedOS Verification & Peer Node Gateway")
    parser.add_argument("--port", type=int, default=int(os.getenv("PORT", "8000")), help="Port to bind (default: 8000)")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="Host address to bind (default: 0.0.0.0)")
    parser.add_argument("--node-id", type=str, default=None, help="Custom SharedNet Node ID")
    args = parser.parse_args()
    
    if args.node_id:
        cloud_adapter.node_id = args.node_id
        
    print(f"[*] Starting AgentScout Node [{cloud_adapter.node_id}] on http://{args.host}:{args.port}")
    uvicorn.run(app, host=args.host, port=args.port, reload=False)
