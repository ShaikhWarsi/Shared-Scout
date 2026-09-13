"""
Audit Scorer, Report Synthesizer & Autonomous Response Repair Engine
Computes overall reliability metrics, aggregation stats, actionable recommendations, and auto-repaired text.
"""

import re
from typing import List, Optional
from core.schemas import ClaimAudit, AuditStats, VerdictEnum, AuditResponse, AuditMode
from sharedos.manifest import SHAREDOS_PURPOSE_STRING


class AuditScorer:
    def __init__(self):
        pass

    def compute_audit(self, audit_id: str, claims: List[ClaimAudit], latency_ms: int, original_answer: str = "", mode: AuditMode = AuditMode.VERIFY) -> AuditResponse:
        total = len(claims)
        if total == 0:
            return AuditResponse(
                audit_id=audit_id,
                reliability=100,
                verdict_summary="NO_CLAIMS_TO_EVALUATE",
                mode=mode,
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

        # ---------------------------------------------------------
        # Generalized Multi-Domain Autonomous Repair Engine
        # ---------------------------------------------------------
        repaired = original_answer
        if original_answer and contradicted > 0:
            for c in claims:
                if c.verdict == VerdictEnum.CONTRADICTED and c.correction:
                    corr_text = c.correction.strip()
                    claim_str = c.claim_text.strip()
                    
                    # 1. Price / Currency replacement
                    price_pattern = r"((?:Rs\.?|INR|₹|\$|USD|EUR|€|GBP|£)\s*[\d,]+(?:\.\d+)?)"
                    corr_prices = re.findall(price_pattern, corr_text, re.IGNORECASE)
                    claim_prices = re.findall(price_pattern, claim_str, re.IGNORECASE)
                    if corr_prices and claim_prices:
                        wrong_p = claim_prices[0]
                        right_p = corr_prices[0]
                        if wrong_p in repaired and wrong_p.lower() != right_p.lower():
                            repaired = repaired.replace(wrong_p, right_p)
                            continue

                    # 2. Numeric + Unit Specification replacement (e.g. 40 hours -> 30 hours, 100W -> 65W, 5000mAh -> 4500mAh)
                    spec_pattern = r"(\d+(?:\.\d+)?)\s*(hours|hour|hrs|hr|db|mah|watts|watt|w|khz|mhz|ghz|hz|gb|tb|mb|nits|nit|meters|meter|km/s|km|cm|mm|grams|g|kg|lbs|k|tokens|token)\b"
                    corr_specs = re.findall(spec_pattern, corr_text, re.IGNORECASE)
                    claim_specs = re.findall(spec_pattern, claim_str, re.IGNORECASE)
                    
                    spec_replaced = False
                    if corr_specs and claim_specs:
                        for c_val, c_unit in claim_specs:
                            for r_val, r_unit in corr_specs:
                                if c_unit.lower() == r_unit.lower() and c_val != r_val:
                                    # Target wrong spec in text
                                    target_rx = re.compile(rf"\b{re.escape(c_val)}\s*{re.escape(c_unit)}\b", re.IGNORECASE)
                                    if target_rx.search(repaired):
                                        repaired = target_rx.sub(f"{r_val} {c_unit}", repaired)
                                        spec_replaced = True
                                        break
                    if spec_replaced:
                        continue

                    # 3. Historical Year / Date replacement (e.g. 1995 -> 1991, 1968 -> 1969)
                    year_pattern = r"\b(19\d\d|20\d\d)\b"
                    corr_years = re.findall(year_pattern, corr_text)
                    claim_years = re.findall(year_pattern, claim_str)
                    if corr_years and claim_years:
                        for cy in claim_years:
                            for ry in corr_years:
                                if cy != ry and cy in repaired:
                                    repaired = repaired.replace(cy, ry)
                                    spec_replaced = True
                    if spec_replaced:
                        continue

                    # 4. Direct Proposition or Keyword replacement
                    if "Verified is:" in corr_text or "Verified fact:" in corr_text or "Verified specification is" in corr_text:
                        clean_corr = re.sub(r"^(?:Verified is:|Verified fact:|Verified specification is|Actual verified price is)\s*", "", corr_text, flags=re.IGNORECASE).strip().rstrip(".")
                        # If claim exists verbatim in original answer, replace with clean correction
                        if claim_str in repaired:
                            repaired = repaired.replace(claim_str, clean_corr)

        return AuditResponse(
            audit_id=audit_id,
            reliability=reliability,
            verdict_summary=summary,
            mode=mode,
            stats=stats,
            claims=claims,
            recommendation=recommendation,
            repaired_answer=repaired,
            execution_latency_ms=latency_ms,
            sharedos_purpose=SHAREDOS_PURPOSE_STRING,
            credits_billed=5
        )
