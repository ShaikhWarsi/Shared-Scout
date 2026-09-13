"""
AgentScout FastAPI Server, SharedNet Gateway, Autonomous Repair Router, HMAC Auth & Rate Limiter
"""

import os
import json
import time
from typing import List
from collections import defaultdict
from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware

from core.schemas import AuditRequest, AuditResponse
from sharedos.service import AgentScoutService
from sharedos.manifest import SHAREDOS_MANIFEST, SHAREDOS_PURPOSE_STRING
from sharedos.cloud_adapter import SharedOSCloudAdapter
from arena.pitch_bot import ArenaPitchAgent

app = FastAPI(
    title="AgentScout - SharedOS Verification Layer",
    version="1.2.0",
    description="Independent verification and autonomous hallucination repair layer for AI agents on SharedOS."
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


@app.post("/audit", response_model=AuditResponse)
async def audit_answer(req: AuditRequest, request: Request, caller_id: str = Depends(authenticate_caller)):
    try:
        response, trail = service.execute_audit(req, caller_agent_id=caller_id)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Audit execution error: {str(e)}")


@app.post("/repair", response_model=AuditResponse)
async def repair_answer(req: AuditRequest, request: Request, caller_id: str = Depends(authenticate_caller)):
    """Executes audit and returns verified auto-repaired answer text."""
    try:
        response, _ = service.execute_audit(req, caller_agent_id=caller_id)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Repair execution error: {str(e)}")


@app.post("/batch-audit", response_model=List[AuditResponse])
async def batch_audit_answers(requests: List[AuditRequest], request: Request, caller_id: str = Depends(authenticate_caller)):
    """Audits multiple agent answers in a single batch call."""
    results = []
    for req in requests[:5]:  # Cap at 5 per batch for safety
        res, _ = service.execute_audit(req, caller_agent_id=caller_id)
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
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=False)
