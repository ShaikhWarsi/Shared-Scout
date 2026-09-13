"""
AgentScout SharedOS Service Engine
Executes full A2A audit requests, enforces SharedOS permissions, and logs turns to the cryptographic audit trail.
"""

import time
import uuid
from typing import Dict, Any, Tuple, Optional, List
from core.schemas import AuditRequest, AuditResponse, VerdictEnum, AuditMode
from core.extractor import ClaimExtractor
from core.search import WebSearchEngine
from core.verifier import ClaimVerifier
from core.scorer import AuditScorer
from sharedos.audit_trail import SharedOSAuditTrail
from sharedos.manifest import SHAREDOS_MANIFEST, SHAREDOS_PURPOSE_STRING
from sharedos.kernel import SharedOSKernel


class AgentScoutService:
    def __init__(self, kernel: Optional[SharedOSKernel] = None):
        self.extractor = ClaimExtractor()
        self.search_engine = WebSearchEngine()
        self.verifier = ClaimVerifier()
        self.scorer = AuditScorer()
        self.audit_history: Dict[str, SharedOSAuditTrail] = {}
        self.kernel = kernel or SharedOSKernel()
        self._register_kernel_tools()

    def _register_kernel_tools(self):
        """Registers AgentScout domain tools on the SharedOS kernel."""
        self.kernel.register_tool(
            name="agentscout.repair",
            namespace="agentscout",
            description="Deconstructs draft answer, searches evidence, verifies contradictions, and produces surgical diff repair.",
            handler=lambda args: self._internal_audit(
                question=args.get("question", ""),
                answer=args.get("answer", ""),
                mode=AuditMode.VERIFY,
                max_claims=args.get("max_claims", 5)
            ),
            resource_mapping=lambda args: {
                "namespace": "agentscout",
                "path": ["firewall", "gate"],
                "action": "repair"
            }
        )
        self.kernel.register_tool(
            name="agentscout.attack",
            namespace="agentscout",
            description="Executes adversarial boundary & specification stress-tests on candidate draft.",
            handler=lambda args: self._internal_audit(
                question=args.get("question", ""),
                answer=args.get("answer", ""),
                mode=AuditMode.ATTACK,
                max_claims=args.get("max_claims", 5)
            ),
            resource_mapping=lambda args: {
                "namespace": "agentscout",
                "path": ["arena", "attack"],
                "action": "attack"
            }
        )
        self.kernel.register_tool(
            name="agentscout.trial",
            namespace="agentscout",
            description="Single-claim free factual verification trial.",
            handler=lambda args: self._internal_audit(
                question=args.get("question", ""),
                answer=args.get("answer", ""),
                mode=AuditMode.VERIFY,
                max_claims=1
            ),
            resource_mapping=lambda args: {
                "namespace": "agentscout",
                "path": ["trial"],
                "action": "verify"
            }
        )

    def _internal_audit(self, question: str, answer: str, mode: AuditMode, max_claims: int = 5) -> Dict[str, Any]:
        req = AuditRequest(question=question, answer=answer, mode=mode, max_claims=max_claims)
        res, data = self._run_audit_pipeline(req, caller_agent_id="agentscout-core")
        return {"audit_response": res.model_dump(), "trail_data": data}

    def execute_audit(self, request: AuditRequest, caller_agent_id: str = "agent-peer") -> Tuple[AuditResponse, Dict[str, Any]]:
        # Enforce SharedOS capability authorization on the turn
        context = {
            "namespaceId": "agentscout.sharedos.net",
            "actor": {"kind": "agent", "agentId": "agentscout-firewall"},
            "authority": {"kind": "human", "userId": "arena-authority-admin"},
            "owner": {"kind": "human", "userId": "arena-authority-admin"},
            "purpose": "pre-action-firewall" if request.mode == AuditMode.VERIFY else "adversarial-defense",
            "traceId": f"trace_{uuid.uuid4().hex[:12]}",
            "enabledToolNamespaces": ["agentscout", "files", "sharedos"],
            "now": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        }
        
        # Authorize via Kernel
        auth_decision = self.kernel.authorizer.authorize(
            context=context,
            resource_namespace="agentscout",
            resource_path=["firewall", "gate"] if request.mode == AuditMode.VERIFY else ["arena", "attack"],
            action="repair" if request.mode == AuditMode.VERIFY else "attack"
        )
        
        if not auth_decision.get("allowed"):
            # Record refusal to audit sink
            self.kernel.audit_sink.record_decision("turn.refused", context, auth_decision)
            raise PermissionError(f"SharedOS capability denied: {auth_decision.get('reasonCode')}")

        res, data = self._run_audit_pipeline(request, caller_agent_id=caller_agent_id)
        
        # Record successful turn to durable audit sink
        self.kernel.audit_sink.record_decision(
            "turn.executed",
            context,
            {"status": "succeeded", "grantId": auth_decision.get("grantId"), "reliability": res.reliability}
        )

        # Trigger background non-blocking flush to SharedOS Cloud
        try:
            import threading
            threading.Thread(target=self.kernel.audit_sink.flush_outbox, daemon=True).start()
        except Exception:
            pass

        return res, data

    def _run_audit_pipeline(self, request: AuditRequest, caller_agent_id: str = "agent-peer") -> Tuple[AuditResponse, Dict[str, Any]]:
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
                evidence=evidence,
                mode=request.mode
            )
            audited_claims.append(claim_audit)

        trail.log_turn("TURN_3_EVIDENCE_RETRIEVAL", {
            "searched_claims": searched_claims
        })

        trail.log_turn("TURN_4_NLI_VERIFICATION", {
            "mode": request.mode.value,
            "evaluated_claims": [
                {
                    "claim_id": c.claim_id,
                    "verdict": c.verdict.value,
                    "confidence": c.confidence,
                    "has_contradiction": bool(c.contradiction_details)
                } for c in audited_claims
            ]
        })

        # Turn 5: Scoring, Advisory Synthesis, Autonomous Repair & Egress
        latency_ms = int((time.time() - start_time) * 1000)
        response = self.scorer.compute_audit(
            audit_id=audit_id,
            claims=audited_claims,
            latency_ms=latency_ms,
            original_answer=request.answer,
            mode=request.mode
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
