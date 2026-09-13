"""
AgentScout Model Context Protocol (MCP) Server
Enables autonomous agents on SharedNet / Claude Code / Cursor / Codex to discover,
call, and pay for AgentScout verification and pre-ship firewall services over stdio JSON-RPC.
"""

import sys
import json
import os

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from core.schemas import FirewallGateRequest, AuditRequest, AuditMode
from core.firewall import AgentFirewallGate
from sharedos.service import AgentScoutService
from arena.ledger import ArenaLedger
from sharedos.manifest import SHAREDOS_MANIFEST, SHAREDOS_PURPOSE_STRING


service = AgentScoutService()
firewall = AgentFirewallGate(service=service)
ledger = ArenaLedger()


TOOLS_DEFINITIONS = [
    {
        "name": "agentscout_free_manifest",
        "description": "FREE TIER: Get AgentScout node info, service catalog, grants, and purpose string.",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": []
        }
    },
    {
        "name": "agentscout_free_trial",
        "description": "FREE TIER (0 Credits): Trial factual verification on a single atomic claim.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "question": {"type": "string", "description": "The prompt / research question"},
                "answer": {"type": "string", "description": "The proposed draft answer"}
            },
            "required": ["question", "answer"]
        }
    },
    {
        "name": "agentscout_firewall_gate",
        "description": "PAID TIER (5 Credits): Pre-Ship CI/CD Firewall Gate. Intercepts draft, detects hallucinations, blocks unsafe responses (<80/100), and auto-repairs contradictions.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "caller_agent_id": {"type": "string", "description": "Your agent's SharedNet Node ID"},
                "question": {"type": "string", "description": "The question being answered"},
                "answer": {"type": "string", "description": "The draft response you want verified before shipping"},
                "min_reliability_threshold": {"type": "integer", "default": 80, "description": "Minimum acceptable reliability (50-100)"},
                "auto_repair": {"type": "boolean", "default": True, "description": "Automatically repair if contradictions found"}
            },
            "required": ["caller_agent_id", "question", "answer"]
        }
    },
    {
        "name": "agentscout_adversarial_attack",
        "description": "PAID TIER (5 Credits): Adversarially stress-tests a proposition for specification discrepancies and temporal obsolescence.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "caller_agent_id": {"type": "string", "description": "Your agent's SharedNet Node ID"},
                "question": {"type": "string", "description": "The question being answered"},
                "answer": {"type": "string", "description": "The draft response to attack"}
            },
            "required": ["caller_agent_id", "question", "answer"]
        }
    },
    {
        "name": "agentscout_send_credits",
        "description": "ARENA MARKET: Transfer credits to AgentScout to pay for verification services.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "sender_agent_id": {"type": "string", "description": "Your agent ID"},
                "amount": {"type": "integer", "description": "Credits to transfer (e.g. 5, 10, 20)"},
                "note": {"type": "string", "description": "Payment note / service reference"}
            },
            "required": ["sender_agent_id", "amount"]
        }
    }
]


def handle_tool_call(name: str, arguments: dict) -> dict:
    if name == "agentscout_free_manifest":
        return {
            "manifest": SHAREDOS_MANIFEST,
            "purpose": SHAREDOS_PURPOSE_STRING,
            "pricing": {
                "free_tier": "0 credits (1-claim trial via agentscout_free_trial)",
                "firewall_gate": "5 credits per pre-ship evaluation & repair",
                "adversarial_attack": "5 credits per stress-test"
            }
        }
    
    elif name == "agentscout_free_trial":
        req = AuditRequest(question=arguments.get("question", ""), answer=arguments.get("answer", ""), max_claims=1)
        res, _ = service.execute_audit(req, caller_agent_id="mcp-free-trial")
        return {
            "tier": "FREE_TRIAL",
            "verdict": res.verdict_summary,
            "reliability": res.reliability,
            "claims_checked": len(res.claims),
            "credits_billed": 0,
            "repaired_answer": res.repaired_answer
        }

    elif name == "agentscout_firewall_gate":
        caller = arguments.get("caller_agent_id", "mcp-agent-caller")
        success, bal, msg = ledger.deduct_credits(caller, amount=5, service_name="MCP agentscout_firewall_gate")
        if not success:
            return {"error": "INSUFFICIENT_CREDITS", "detail": msg, "required": 5, "current_balance": bal}
        
        gate_req = FirewallGateRequest(
            question=arguments.get("question", ""),
            answer=arguments.get("answer", ""),
            min_reliability_threshold=arguments.get("min_reliability_threshold", 80),
            auto_repair=arguments.get("auto_repair", True)
        )
        gate_res = firewall.evaluate_gate(gate_req, caller_agent_id=caller)
        return {
            "status": gate_res.status.value,
            "initial_reliability": gate_res.initial_reliability,
            "final_reliability": gate_res.final_reliability,
            "safe_to_ship_answer": gate_res.safe_to_ship_answer,
            "credits_remaining": bal,
            "blocked_reasons": gate_res.blocked_reasons
        }

    elif name == "agentscout_adversarial_attack":
        caller = arguments.get("caller_agent_id", "mcp-agent-caller")
        success, bal, msg = ledger.deduct_credits(caller, amount=5, service_name="MCP agentscout_adversarial_attack")
        if not success:
            return {"error": "INSUFFICIENT_CREDITS", "detail": msg, "required": 5, "current_balance": bal}
        
        audit_req = AuditRequest(question=arguments.get("question", ""), answer=arguments.get("answer", ""), mode=AuditMode.ATTACK)
        res, _ = service.execute_audit(audit_req, caller_agent_id=caller)
        return {
            "verdict": res.verdict_summary,
            "reliability": res.reliability,
            "contradictions_found": res.stats.contradicted,
            "credits_remaining": bal,
            "claims": [c.model_dump() for c in res.claims]
        }

    elif name == "agentscout_send_credits":
        sender = arguments.get("sender_agent_id", "peer-agent")
        amt = int(arguments.get("amount", 5))
        note = arguments.get("note", "MCP Credit Transfer")
        new_bal = ledger.add_credits(sender, amt, reason=f"MCP_PAYMENT: {note}")
        return {
            "status": "PAYMENT_ACKNOWLEDGED",
            "sender_agent_id": sender,
            "credits_credited": amt,
            "new_balance": new_bal,
            "message": f"Successfully received {amt} Arena credits from {sender}."
        }
    
    return {"error": f"Unknown tool '{name}'"}


def run_mcp_server():
    """Runs a standard JSON-RPC 2.0 stdio loop for MCP clients."""
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
            req_id = req.get("id")
            method = req.get("method")

            if method == "tools/list":
                resp = {"jsonrpc": "2.0", "id": req_id, "result": {"tools": TOOLS_DEFINITIONS}}
            elif method == "tools/call":
                params = req.get("params", {})
                tool_name = params.get("name")
                tool_args = params.get("arguments", {})
                result = handle_tool_call(tool_name, tool_args)
                resp = {"jsonrpc": "2.0", "id": req_id, "result": {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}}
            elif method == "initialize":
                resp = {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "protocolVersion": "2024-11-05",
                        "serverInfo": {"name": "agentscout-mcp", "version": "1.0.0"},
                        "capabilities": {"tools": {}}
                    }
                }
            else:
                resp = {"jsonrpc": "2.0", "id": req_id, "result": {}}

            sys.stdout.write(json.dumps(resp) + "\n")
            sys.stdout.flush()
        except Exception as e:
            err_resp = {"jsonrpc": "2.0", "id": None, "error": {"code": -32603, "message": str(e)}}
            sys.stdout.write(json.dumps(err_resp) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    run_mcp_server()
