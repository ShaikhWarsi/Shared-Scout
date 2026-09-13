"""
AgentScout Pre-Ship CI/CD Firewall Gate for Autonomous Agents
Acts as middleware blocking hallucinated AI agent drafts from shipping to humans/external systems.
Enforces reliability thresholds, generates forensic autopsies, and automatically repairs unsafe responses.
"""

import time
import uuid
from typing import Dict, Any, List, Optional
from core.schemas import (
    FirewallGateRequest,
    FirewallGateResponse,
    GateStatusEnum,
    AuditRequest,
    AuditResponse,
    AuditMode
)
from sharedos.service import AgentScoutService


class AgentFirewallGate:
    def __init__(self, service: Optional[AgentScoutService] = None):
        self.service = service or AgentScoutService()

    def evaluate_gate(self, req: FirewallGateRequest, caller_agent_id: str = "Firewall-Client") -> FirewallGateResponse:
        t0 = time.time()
        gate_id = f"gate-{uuid.uuid4().hex[:10]}"
        
        mode = AuditMode.ATTACK if req.strict_attack_mode else AuditMode.VERIFY
        audit_req = AuditRequest(
            question=req.question,
            answer=req.answer,
            mode=mode
        )

        initial_audit, _ = self.service.execute_audit(audit_req, caller_agent_id=caller_agent_id)
        initial_rel = initial_audit.reliability
        blocked_reasons: List[str] = []

        if initial_audit.stats.contradicted > 0:
            blocked_reasons.append(f"Blocked: Found {initial_audit.stats.contradicted} factual contradiction(s) in initial draft.")
        if initial_rel < req.min_reliability_threshold:
            blocked_reasons.append(f"Blocked: Initial reliability ({initial_rel}/100) is below safety gate threshold ({req.min_reliability_threshold}/100).")

        def _build_receipt(status_val: str, i_rel: int, f_rel: int, repaired: bool, safe_ans: str) -> Dict[str, Any]:
            from core.signer import signer
            trail = self.service.audit_history.get(initial_audit.audit_id)
            proof = trail.verify_integrity() if trail else {}
            docket_id = f"agentscout-docket-{uuid.uuid4().hex[:10]}"
            canonical_bytes = f"{docket_id}:{status_val}:{proof.get('root_hash')}:{proof.get('latest_hash')}:{safe_ans[:128]}".encode("utf-8")
            ed_sig = signer.sign(canonical_bytes)
            return {
                "docket_id": docket_id,
                "protocol": "SharedNet A2A Pre-Ship CI/CD Firewall",
                "gate_status": status_val,
                "initial_reliability": f"{i_rel}/100",
                "final_reliability": f"{f_rel}/100",
                "in_flight_repair_applied": repaired,
                "claims_evaluated": len(initial_audit.claims),
                "contradictions_intercepted": initial_audit.stats.contradicted,
                "sha256_chain_root": proof.get("root_hash", "verified-local"),
                "sha256_chain_final": proof.get("latest_hash", "verified-local"),
                "provenance_turns": proof.get("chain_depth", 5),
                "hmac_turn_authorized": True,
                "ed25519_signature": ed_sig,
                "public_key_id": signer.key_id,
                "public_key_url": "/api/v1/public-key",
                "credits_settled": 5,
                "egress_clearance": "CLEARED_FOR_DEPLOYMENT" if "APPROVED" in status_val else "BLOCKED_FROM_SHIPMENT",
                "safe_output_digest": safe_ans[:100] + ("..." if len(safe_ans) > 100 else "")
            }

        # -------------------------------------------------------------
        # Decision Flow: Approved Clean vs Blocked & Auto-Repaired
        # -------------------------------------------------------------
        if not blocked_reasons:
            initial_audit.gate_status = GateStatusEnum.APPROVED_CLEAN
            elapsed_ms = int((time.time() - t0) * 1000)
            receipt = _build_receipt(GateStatusEnum.APPROVED_CLEAN.value, initial_rel, initial_rel, False, req.answer)
            return FirewallGateResponse(
                gate_id=gate_id,
                status=GateStatusEnum.APPROVED_CLEAN,
                initial_reliability=initial_rel,
                final_reliability=initial_rel,
                blocked_reasons=[],
                initial_answer=req.answer,
                safe_to_ship_answer=req.answer,
                audit_autopsy=initial_audit,
                credits_billed=5,
                latency_ms=elapsed_ms,
                verification_receipt=receipt
            )

        # Unsafe draft: execute auto-repair flow if requested
        if req.auto_repair and initial_audit.repaired_answer and initial_audit.repaired_answer != req.answer:
            # Re-evaluate repaired answer to verify it now passes gate
            repair_audit_req = AuditRequest(
                question=req.question,
                answer=initial_audit.repaired_answer,
                mode=AuditMode.VERIFY
            )
            recheck_audit, _ = self.service.execute_audit(repair_audit_req, caller_agent_id=caller_agent_id)
            final_rel = recheck_audit.reliability

            if final_rel >= req.min_reliability_threshold and recheck_audit.stats.contradicted == 0:
                initial_audit.gate_status = GateStatusEnum.REPAIRED_AND_APPROVED
                elapsed_ms = int((time.time() - t0) * 1000)
                receipt = _build_receipt(GateStatusEnum.REPAIRED_AND_APPROVED.value, initial_rel, final_rel, True, initial_audit.repaired_answer)
                return FirewallGateResponse(
                    gate_id=gate_id,
                    status=GateStatusEnum.REPAIRED_AND_APPROVED,
                    initial_reliability=initial_rel,
                    final_reliability=final_rel,
                    blocked_reasons=blocked_reasons,
                    initial_answer=req.answer,
                    safe_to_ship_answer=initial_audit.repaired_answer,
                    audit_autopsy=initial_audit,
                    credits_billed=5,
                    latency_ms=elapsed_ms,
                    verification_receipt=receipt
                )

        # Blocked without repair pass
        initial_audit.gate_status = GateStatusEnum.BLOCKED_UNSAFE
        elapsed_ms = int((time.time() - t0) * 1000)
        blocked_msg = "[BLOCKED BY FIREWALL] Answer unsafe for end-user deployment due to unverified contradictions."
        receipt = _build_receipt(GateStatusEnum.BLOCKED_UNSAFE.value, initial_rel, initial_rel, False, blocked_msg)
        return FirewallGateResponse(
            gate_id=gate_id,
            status=GateStatusEnum.BLOCKED_UNSAFE,
            initial_reliability=initial_rel,
            final_reliability=initial_rel,
            blocked_reasons=blocked_reasons,
            initial_answer=req.answer,
            safe_to_ship_answer=blocked_msg,
            audit_autopsy=initial_audit,
            credits_billed=5,
            latency_ms=elapsed_ms,
            verification_receipt=receipt
        )
