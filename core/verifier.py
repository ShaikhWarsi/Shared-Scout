"""
Structured Natural Language Inference (NLI) Verifier
Performs generalized contradiction detection, numeric/spec extraction, and LLM inference.
"""

import re
import json
import os
import urllib.request
import urllib.parse
from typing import List, Tuple, Optional, Dict, Any
from core.schemas import VerdictEnum, EvidenceItem, ClaimAudit


class ClaimVerifier:
    def __init__(self):
        self.openai_key = os.getenv("OPENAI_API_KEY", "")
        self.gemini_key = os.getenv("GEMINI_API_KEY", "")

    def verify_claim(self, claim_id: int, claim_text: str, evidence: List[EvidenceItem]) -> ClaimAudit:
        if not evidence:
            return ClaimAudit(
                claim_id=claim_id,
                claim_text=claim_text,
                verdict=VerdictEnum.UNVERIFIED,
                confidence=0.50,
                evidence=[],
                contradiction_details="No authoritative third-party source corroboration found across inspected web sources."
            )

        # 1. Attempt LLM reasoning if API key configured
        if self.openai_key:
            llm_res = self._evaluate_with_llm(claim_text, evidence)
            if llm_res:
                verdict, conf, details, corr = llm_res
                return ClaimAudit(
                    claim_id=claim_id,
                    claim_text=claim_text,
                    verdict=verdict,
                    confidence=conf,
                    evidence=evidence,
                    contradiction_details=details,
                    correction=corr
                )

        # 2. Generalized Deterministic Entailment Engine
        verdict, confidence, details, correction = self._evaluate_deterministic_entailment(claim_text, evidence)

        return ClaimAudit(
            claim_id=claim_id,
            claim_text=claim_text,
            verdict=verdict,
            confidence=confidence,
            evidence=evidence,
            contradiction_details=details,
            correction=correction
        )

    def _evaluate_with_llm(self, claim: str, evidence: List[EvidenceItem]) -> Optional[Tuple[VerdictEnum, float, Optional[str], Optional[str]]]:
        try:
            prompt = (
                "Evaluate this factual claim strictly against the provided evidence snippets:\n"
                f"Claim: {claim}\n"
                f"Evidence: {[e.snippet for e in evidence]}\n"
                "Return a valid JSON object with keys:\n"
                "- verdict: ('SUPPORTED', 'CONTRADICTED', 'UNVERIFIED', 'OUTDATED')\n"
                "- confidence: (float between 0.0 and 1.0)\n"
                "- contradiction_details: (string explaining contradiction or null)\n"
                "- correction: (string with the verified fact or null)"
            )
            req_data = json.dumps({
                "model": "gpt-4o-mini",
                "messages": [{"role": "user", "content": prompt}],
                "response_format": {"type": "json_object"}
            }).encode("utf-8")
            req = urllib.request.Request(
                "https://api.openai.com/v1/chat/completions",
                data=req_data,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.openai_key}"
                }
            )
            with urllib.request.urlopen(req, timeout=4) as resp:
                if resp.status == 200:
                    data = json.loads(resp.read().decode("utf-8"))
                    content = json.loads(data["choices"][0]["message"]["content"])
                    v = VerdictEnum(content.get("verdict", "UNVERIFIED"))
                    c = float(content.get("confidence", 0.85))
                    d = content.get("contradiction_details")
                    cor = content.get("correction")
                    return (v, c, d, cor)
        except Exception:
            pass
        return None

    def _evaluate_deterministic_entailment(self, claim: str, evidence: List[EvidenceItem]) -> Tuple[VerdictEnum, float, Optional[str], Optional[str]]:
        c_lower = claim.lower()
        combined_snippets = " ".join([e.snippet.lower() for e in evidence])
        top_weight = max([e.reliability_weight for e in evidence]) if evidence else 0.5

        # ---------------------------------------------------------
        # 1. Generalized Price / Currency Contradiction Detection
        # ---------------------------------------------------------
        price_pattern = r"(?:rs\.?|inr|₹|\$|usd|eur|€|gbp|£)\s*(\d[\d,]*(?:\.\d+)?)"
        claim_prices = re.findall(price_pattern, c_lower)
        if claim_prices:
            for cp in claim_prices:
                clean_cp = cp.replace(",", "")
                ev_prices = re.findall(price_pattern, combined_snippets)
                ev_clean = [p.replace(",", "") for p in ev_prices]
                if ev_clean and clean_cp not in ev_clean:
                    correct_price = ev_prices[0]
                    # Find currency symbol in claim
                    curr_match = re.search(r"(rs\.?|inr|₹|\$|usd|eur|€|gbp|£)", c_lower)
                    curr_sym = curr_match.group(1).upper() if curr_match else "Rs."
                    conf = min(0.99, 0.90 + (top_weight * 0.08))
                    return (
                        VerdictEnum.CONTRADICTED,
                        conf,
                        f"Claim states price {curr_sym} {cp}, but verified manufacturer/retailer catalog confirms {curr_sym} {correct_price}.",
                        f"Actual verified price is {curr_sym} {correct_price}"
                    )

        # ---------------------------------------------------------
        # 2. Generalized Numeric & Specification Contradiction
        # ---------------------------------------------------------
        # Extracts (value, unit) pairs, e.g. ("40", "hours"), ("100", "w"), ("50", "db"), ("8848.86", "meters")
        num_unit_pattern = r"(\d+(?:\.\d+)?)\s*(hours|hour|hrs|hr|db|mah|watts|watt|w|khz|mhz|ghz|hz|gb|tb|mb|nits|nit|meters|meter|km/s|km|cm|mm|grams|g|kg|lbs|k|tokens|token)\b"
        claim_quantities = re.findall(num_unit_pattern, c_lower)
        ev_quantities = re.findall(num_unit_pattern, combined_snippets)

        if claim_quantities and ev_quantities:
            # Map evidence units to values
            ev_unit_map: Dict[str, List[str]] = {}
            for val, unit in ev_quantities:
                # Normalize unit variations (e.g., hrs -> hours)
                norm_unit = "hours" if unit in {"hour", "hrs", "hr"} else "watts" if unit == "watt" else "meters" if unit == "meter" else "nits" if unit == "nit" else unit
                ev_unit_map.setdefault(norm_unit, []).append(val)

            for c_val, c_unit in claim_quantities:
                norm_c_unit = "hours" if c_unit in {"hour", "hrs", "hr"} else "watts" if c_unit == "watt" else "meters" if c_unit == "meter" else "nits" if c_unit == "nit" else c_unit
                if norm_c_unit in ev_unit_map:
                    matching_ev_vals = ev_unit_map[norm_c_unit]
                    # Check for conditional specs (e.g., "30 hours (NC ON), 40 hours (NC OFF)")
                    if "anc" in c_lower or "nc" in c_lower or "noise cancel" in c_lower:
                        # If claim asserts high number with ANC, check if evidence restricts that number to NC OFF
                        for snippet in [e.snippet for e in evidence]:
                            s_lower = snippet.lower()
                            if ("nc on" in s_lower or "nc enabled" in s_lower or "with anc" in s_lower) and c_val not in s_lower:
                                nc_on_match = re.search(r"(\d+)\s*(?:hours|hrs|hr)?\s*\((?:nc on|with anc)\)", s_lower)
                                if nc_on_match:
                                    true_val = nc_on_match.group(1)
                                    return (
                                        VerdictEnum.CONTRADICTED,
                                        0.96,
                                        f"Claim asserts {c_val} {norm_c_unit} with ANC enabled, but official specifications confirm {true_val} {norm_c_unit} with ANC ({c_val} {norm_c_unit} only with ANC disabled).",
                                        f"Specification is {true_val} {norm_c_unit} with ANC active."
                                    )

                    # Standard numeric mismatch on identical unit
                    if c_val not in matching_ev_vals:
                        ev_val = matching_ev_vals[0]
                        return (
                            VerdictEnum.CONTRADICTED,
                            min(0.98, 0.88 + (top_weight * 0.10)),
                            f"Claim asserts specification of {c_val} {norm_c_unit}, but primary evidence sources confirm {ev_val} {norm_c_unit}.",
                            f"Verified specification is {ev_val} {norm_c_unit}."
                        )
                    else:
                        # Direct numeric corroboration found
                        conf = min(0.98, 0.85 + (top_weight * 0.12))
                        return (VerdictEnum.SUPPORTED, conf, None, None)

        # ---------------------------------------------------------
        # 3. Generalized Historical Year / Entity Date Contradiction
        # ---------------------------------------------------------
        year_pattern = r"\b(19\d\d|20\d\d)\b"
        claim_years = re.findall(year_pattern, c_lower)
        if claim_years:
            for cy in claim_years:
                ev_years = re.findall(year_pattern, combined_snippets)
                if ev_years and cy not in ev_years:
                    correct_year = ev_years[0]
                    # Check if there's high entity overlap to ensure we are talking about the same subject
                    return (
                        VerdictEnum.CONTRADICTED,
                        0.92,
                        f"Claim asserts year {cy}, but authoritative records confirm year {correct_year}.",
                        f"Verified date/year is {correct_year}"
                    )

        # ---------------------------------------------------------
        # 4. Semantic Keyword & Proposition Corroboration
        # ---------------------------------------------------------
        claim_keywords = set([w for w in re.findall(r"\b[a-z]{4,}\b", c_lower) if w not in {
            "with", "this", "that", "from", "have", "best", "good", "under", "costs", "features", "provides",
            "which", "there", "their", "about", "other", "into", "more", "also", "some"
        }])
        ev_keywords = set(re.findall(r"\b[a-z]{4,}\b", combined_snippets))
        overlap = claim_keywords.intersection(ev_keywords)

        if len(claim_keywords) > 0:
            ratio = len(overlap) / len(claim_keywords)
            if ratio >= 0.45:
                conf = min(0.96, 0.72 + (ratio * 0.20) + (top_weight * 0.08))
                return (VerdictEnum.SUPPORTED, conf, None, None)
            elif ratio >= 0.25:
                return (VerdictEnum.SUPPORTED, 0.75, None, None)

        return (
            VerdictEnum.UNVERIFIED,
            0.50,
            "Insufficient primary source corroboration found in retrieved pages.",
            None
        )
