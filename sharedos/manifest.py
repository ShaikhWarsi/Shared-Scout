"""
SharedOS Manifest and Purpose Declarations
Defines the required grants, permission scope, and immutable purpose string.
"""

from typing import Dict, List, Any

SHAREDOS_PURPOSE_STRING = (
    "Independent multi-source factual verification and hallucination auditing for AI agent responses."
)

SHAREDOS_MANIFEST: Dict[str, Any] = {
    "agent_id": "agentscout-v1",
    "node_id": "agentscout.sharedos.net",
    "name": "AgentScout",
    "version": "1.0.0",
    "tagline": "The independent verification layer for AI agents.",
    "purpose": SHAREDOS_PURPOSE_STRING,
    "grants": [
        "network:http_client",
        "storage:ephemeral_audit",
        "agent:message_receive",
        "agent:message_send",
        "tools:web_search",
        "tools:content_extract"
    ],
    "services": [
        {
            "name": "firewall/gate",
            "alias": "Pre-Ship CI/CD Firewall Gate",
            "description": "Evaluates candidate AI agent drafts before user shipment, enforces reliability safety thresholds (>=80/100), blocks unsafe hallucinations, and surgically auto-repairs contradictions with verified ground truth.",
            "price_credits": 5,
            "timeout_seconds": 10,
            "endpoint": "POST /firewall/gate",
            "input_schema": {"question": "string", "answer": "string", "min_reliability_threshold": 80, "auto_repair": True},
            "output_schema": {"status": "string", "initial_reliability": "int", "final_reliability": "int", "safe_to_ship_answer": "string"}
        },
        {
            "name": "repair",
            "alias": "Challenge & Repair",
            "description": "Deconstructs an agent response into atomic factual claims, conducts independent multi-source research, detects contradictions and outdated facts, and returns an evidence-backed reliability autopsy with surgical diff repair.",
            "price_credits": 5,
            "timeout_seconds": 15,
            "endpoint": "POST /repair",
            "input_schema": {"question": "string", "answer": "string", "mode": "VERIFY"},
            "output_schema": {"reliability": "int", "verdict_summary": "string", "repaired_answer": "string", "claims": "array"}
        },
        {
            "name": "attack",
            "alias": "Adversarial Stress-Test",
            "description": "Actively attacks candidate propositions, hunting for numeric boundary violations, outdated specifications, and ungrounded marketing superlatives.",
            "price_credits": 5,
            "timeout_seconds": 15,
            "endpoint": "POST /attack",
            "input_schema": {"question": "string", "answer": "string", "mode": "ATTACK"},
            "output_schema": {"reliability": "int", "verdict_summary": "string", "repaired_answer": "string", "claims": "array"}
        }
    ]
}
