"""
Audit Scorer & Report Synthesizer
Computes overall reliability metrics, aggregation stats, and actionable advisory recommendations.
"""

from typing import List
from core.schemas import ClaimAudit, AuditStats, VerdictEnum, AuditResponse
from sharedos.manifest import SHAREDOS_PURPOSE_STRING


class AuditScorer:
    def __init__(self):
        pass

    def compute_audit(self, audit_id: str, claims: List[ClaimAudit], latency_ms: int) -> AuditResponse:
        total = len(claims)
        if total == 0:
            return AuditResponse(
                audit_id=audit_id,
                reliability=100,
                verdict_summary="NO_CLAIMS_TO_EVALUATE",
                stats=AuditStats(),
                claims=[],
                recommendation="Input answer contains no falsifiable factual assertions.",
                execution_latency_ms=latency_ms,
                sharedos_purpose=SHAREDOS_PURPOSE_STRING,
                credits_billed=5
            )

        supported = sum(1 for c in claims if c.verdict == VerdictEnum.SUPPORTED)
        contradicted = sum(1 for c in claims if c.verdict == VerdictEnum.CONTRADICTED)
        unverified = sum(1 for c in claims if c.verdict == VerdictEnum.UNVERIFIED)
        outdated = sum(1 for c in claims if c.verdict == VerdictEnum.OUTDATED)

        # Formula: Supported = 100%, Unverified = 40%, Outdated = 20%, Contradicted = 0%
        # Severe penalty for direct contradictions
        raw_score = (supported * 100 + unverified * 40 + outdated * 20 + contradicted * 0) / total
        
        # Additional penalty if at least one contradiction exists
        if contradicted > 0:
            raw_score = min(raw_score, 75.0 - (contradicted * 15.0))
        
        reliability = max(0, min(100, int(round(raw_score))))

        # Determine Summary
        if contradicted == 0 and unverified == 0:
            summary = "FULLY_SUPPORTED"
            recommendation = "All extracted claims are verified with high confidence. Safe to present to end-user."
        elif contradicted > 0:
            summary = "CONTRADICTED"
            recommendation = f"Found {contradicted} factual contradiction(s). Review and substitute corrected values before showing to user."
        elif outdated > 0:
            summary = "OUTDATED_FACTS"
            recommendation = "Response includes superseded or outdated factual details."
        else:
            summary = "PARTIALLY_SUPPORTED"
            recommendation = "Most claims verified, but some claims lack independent third-party confirmation."

        stats = AuditStats(
            total_claims=total,
            supported=supported,
            contradicted=contradicted,
            unverified=unverified,
            outdated=outdated
        )

        return AuditResponse(
            audit_id=audit_id,
            reliability=reliability,
            verdict_summary=summary,
            stats=stats,
            claims=claims,
            recommendation=recommendation,
            execution_latency_ms=latency_ms,
            sharedos_purpose=SHAREDOS_PURPOSE_STRING,
            credits_billed=5
        )
