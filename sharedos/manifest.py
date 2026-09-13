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
            "name": "audit",
            "alias": "Challenge an Answer",
            "description": "Deconstructs an agent response into atomic factual claims, conducts independent multi-source research, detects contradictions and outdated facts, and returns an evidence-backed reliability autopsy.",
            "price_credits": 5,
            "timeout_seconds": 30,
            "max_input_chars": 4000
        }
    ]
}
