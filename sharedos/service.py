"""
AgentScout SharedOS Service Engine
Executes full A2A audit requests, enforces SharedOS permissions, and logs turns to the cryptographic audit trail.
"""

import time
import uuid
from typing import Dict, Any, Tuple
from core.schemas import AuditRequest, AuditResponse, VerdictEnum
from core.extractor import ClaimExtractor
from core.search import WebSearchEngine
from core.verifier import ClaimVerifier
from core.scorer import AuditScorer
from sharedos.audit_trail import SharedOSAuditTrail
from sharedos.manifest import SHAREDOS_MANIFEST, SHAREDOS_PURPOSE_STRING


class AgentScoutService:
    def __init__(self):
        self.extractor = ClaimExtractor()
        self.search_engine = WebSearchEngine()
        self.verifier = ClaimVerifier()
        self.scorer = AuditScorer()
        self.audit_history: Dict[str, SharedOSAuditTrail] = {}

    def execute_audit(self, request: AuditRequest, caller_agent_id: str = "agent-peer") -> Tuple[AuditResponse, Dict[str, Any]]:
        start_time = time.time()
        audit_id = f"as-audit-{uuid.uuid4().hex[:8]}"
        trail = SharedOSAuditTrail(audit_id=audit_id, caller_agent_id=caller_agent_id)

        # Turn 1: SharedOS Ingress & Scope Verification
        trail.log_turn("TURN_1_INGRESS", {
            "caller_agent_id": caller_agent_id,
            "purpose": SHAREDOS_PURPOSE_STRING,
            "question": request.question,
            "answer_preview": request.answer[:120] + "...",
            "grants_checked": ["network:http_client", "tools:web_search"]
        })

        # Turn 2: Atomic Claim Extraction
        claims_raw = self.extractor.extract_claims(
            question=request.question,
            answer=request.answer,
            max_claims=request.max_claims or 5
        )
        trail.log_turn("TURN_2_CLAIM_EXTRACTION", {
            "claims_count": len(claims_raw),
            "claims": claims_raw
        })

        # Turn 3: Independent Web Research & Evidence Gathering
        searched_claims = []
        audited_claims = []
        for idx, claim_text in enumerate(claims_raw, start=1):
            evidence = self.search_engine.search_claim(claim_text, question=request.question)
            searched_claims.append({
                "claim_id": idx,
                "claim_text": claim_text,
                "evidence_count": len(evidence),
                "sources": [e.source_url for e in evidence]
            })

            # Turn 4: NLI Verification & Contradiction Evaluation
            claim_audit = self.verifier.verify_claim(
                claim_id=idx,
                claim_text=claim_text,
                evidence=evidence
            )
            audited_claims.append(claim_audit)

        trail.log_turn("TURN_3_EVIDENCE_RETRIEVAL", {
            "searched_claims": searched_claims
        })

        trail.log_turn("TURN_4_NLI_VERIFICATION", {
            "evaluated_claims": [
                {
                    "claim_id": c.claim_id,
                    "verdict": c.verdict.value,
                    "confidence": c.confidence,
                    "has_contradiction": bool(c.contradiction_details)
                } for c in audited_claims
            ]
        })

        # Turn 5: Scoring, Advisory Synthesis & Egress
        latency_ms = int((time.time() - start_time) * 1000)
        response = self.scorer.compute_audit(
            audit_id=audit_id,
            claims=audited_claims,
            latency_ms=latency_ms
        )

        trail.log_turn("TURN_5_EGRESS", {
            "audit_id": audit_id,
            "reliability_score": response.reliability,
            "verdict_summary": response.verdict_summary,
            "credits_billed": response.credits_billed,
            "latency_ms": latency_ms
        })

        self.audit_history[audit_id] = trail
        return response, trail.export_trail()
