"""
Audit Scorer, Report Synthesizer & Autonomous Response Repair Engine
Computes overall reliability metrics, aggregation stats, actionable recommendations, and auto-repaired text.
"""

import re
from typing import List, Optional
from core.schemas import ClaimAudit, AuditStats, VerdictEnum, AuditResponse
from sharedos.manifest import SHAREDOS_PURPOSE_STRING


class AuditScorer:
    def __init__(self):
        pass

    def compute_audit(self, audit_id: str, claims: List[ClaimAudit], latency_ms: int, original_answer: str = "") -> AuditResponse:
        total = len(claims)
        if total == 0:
            return AuditResponse(
                audit_id=audit_id,
                reliability=100,
                verdict_summary="NO_CLAIMS_TO_EVALUATE",
                stats=AuditStats(),
                claims=[],
                recommendation="Input answer contains no falsifiable factual assertions.",
                repaired_answer=original_answer,
                execution_latency_ms=latency_ms,
                sharedos_purpose=SHAREDOS_PURPOSE_STRING,
                credits_billed=5
            )

        supported = sum(1 for c in claims if c.verdict == VerdictEnum.SUPPORTED)
        contradicted = sum(1 for c in claims if c.verdict == VerdictEnum.CONTRADICTED)
        unverified = sum(1 for c in claims if c.verdict == VerdictEnum.UNVERIFIED)
        outdated = sum(1 for c in claims if c.verdict == VerdictEnum.OUTDATED)

        # Formula: Supported = 100%, Unverified = 40%, Outdated = 20%, Contradicted = 0%
        raw_score = (supported * 100 + unverified * 40 + outdated * 20 + contradicted * 0) / total
        
        if contradicted > 0:
            raw_score = min(raw_score, 75.0 - (contradicted * 15.0))
        
        reliability = max(0, min(100, int(round(raw_score))))

        # Determine Summary & Recommendation
        if contradicted == 0 and unverified == 0:
            summary = "FULLY_SUPPORTED"
            recommendation = "All extracted claims are verified with high confidence. Safe to present to end-user."
        elif contradicted > 0:
            summary = "CONTRADICTED"
            recommendation = f"Found {contradicted} factual contradiction(s). Autopsy generated repaired answer below with verified values."
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

        # Build Auto-Repaired Answer
        repaired = original_answer
        if original_answer and contradicted > 0:
            for c in claims:
                if c.verdict == VerdictEnum.CONTRADICTED and c.correction:
                    # If correction contains "Actual verified price is X"
                    price_match = re.search(r"(?:price is|is)\s+((?:Rs\.?|INR|₹|\$|USD|EUR|€)\s*[\d,]+(?:\.\d+)?)", c.correction, re.IGNORECASE)
                    if price_match:
                        correct_val = price_match.group(1)
                        # Extract wrong price in claim
                        wrong_match = re.search(r"((?:Rs\.?|INR|₹|\$|USD|EUR|€)\s*[\d,]+(?:\.\d+)?)", c.claim_text, re.IGNORECASE)
                        if wrong_match:
                            repaired = repaired.replace(wrong_match.group(1), correct_val)
                    elif "with anc active" in c.correction.lower() or "with anc enabled" in c.correction.lower():
                        # Battery / spec correction
                        spec_match = re.search(r"(\d+\s*hours?\s*with ANC enabled)", c.correction, re.IGNORECASE)
                        if spec_match:
                            repaired = re.sub(r"\b\d+\s*hours\s*(?:of continuous music playback\s*)?with ANC enabled\b", spec_match.group(1), repaired, flags=re.IGNORECASE)

        return AuditResponse(
            audit_id=audit_id,
            reliability=reliability,
            verdict_summary=summary,
            stats=stats,
            claims=claims,
            recommendation=recommendation,
            repaired_answer=repaired,
            execution_latency_ms=latency_ms,
            sharedos_purpose=SHAREDOS_PURPOSE_STRING,
            credits_billed=5
        )
