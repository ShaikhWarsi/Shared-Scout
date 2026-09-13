"""
Claim Extractor Module
Deconstructs complex AI agent output into atomic, falsifiable factual propositions without breaking on abbreviations.
"""

import re
from typing import List


class ClaimExtractor:
    def __init__(self):
        pass

    def extract_claims(self, question: str, answer: str, max_claims: int = 5) -> List[str]:
        text = answer.strip()
        replacements = [
            (r'\bRs\.\s*', 'TOKEN_RS_CURRENCY_'),
            (r'\bi\.e\.\s*', 'TOKEN_IE_ABBR_'),
            (r'\be\.g\.\s*', 'TOKEN_EG_ABBR_'),
            (r'\bvs\.\s*', 'TOKEN_VS_ABBR_'),
            (r'\bNo\.\s*', 'TOKEN_NO_ABBR_')
        ]
        for pattern, token in replacements:
            text = re.sub(pattern, token, text, flags=re.IGNORECASE)

        raw_sentences = [s.strip() for s in re.split(r'[.!?]+\s+|\n+', text) if s.strip()]
        
        claims = []
        for s in raw_sentences:
            s = s.replace('TOKEN_RS_CURRENCY_', 'Rs. ')
            s = s.replace('TOKEN_IE_ABBR_', 'i.e. ')
            s = s.replace('TOKEN_EG_ABBR_', 'e.g. ')
            s = s.replace('TOKEN_VS_ABBR_', 'vs. ')
            s = s.replace('TOKEN_NO_ABBR_', 'No. ')
            
            # Normalize whitespace
            s = re.sub(r'\s+', ' ', s).strip()
            # Strip leading list bullets/numbers
            s = re.sub(r'^[*\-•\d\.\)\s]+', '', s).strip()
            
            if len(s) < 12:
                continue
            if re.match(r'^(sure|here is|in summary|overall|hope this helps|i think|as an ai)', s, re.IGNORECASE):
                continue
            
            if s not in claims:
                claims.append(s)

            if len(claims) >= max_claims:
                break

        if not claims:
            claims = [answer.strip()[:200]]

        return claims[:max_claims]
