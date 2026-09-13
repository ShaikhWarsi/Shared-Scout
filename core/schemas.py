"""
AgentScout Data Schemas & Protocols
Strict Pydantic models for A2A requests, claim extraction, evidence retrieval, audit outputs, and repair.
"""

from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class VerdictEnum(str, Enum):
    SUPPORTED = "SUPPORTED"
    CONTRADICTED = "CONTRADICTED"
    UNVERIFIED = "UNVERIFIED"
    OUTDATED = "OUTDATED"


class EvidenceItem(BaseModel):
    source_url: str = Field(..., description="URL or origin of the corroborated evidence")
    source_title: str = Field("", description="Title of the source webpage or publication")
    snippet: str = Field(..., description="Exact textual excerpt supporting or refuting the claim")
    published_date: Optional[str] = Field(None, description="Publication or update date if detected")
    reliability_weight: float = Field(1.0, description="Source reliability weighting factor")


class ClaimAudit(BaseModel):
    claim_id: int = Field(..., description="Sequential claim index")
    claim_text: str = Field(..., description="Atomic factual statement isolated from the answer")
    verdict: VerdictEnum = Field(..., description="Verification outcome")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score for this verdict")
    evidence: List[EvidenceItem] = Field(default_factory=list, description="Gathered external evidence snippets")
    contradiction_details: Optional[str] = Field(None, description="Explanation if claim is contradicted or outdated")
    correction: Optional[str] = Field(None, description="Correct factual replacement if contradicted")


class AuditStats(BaseModel):
    total_claims: int = 0
    supported: int = 0
    contradicted: int = 0
    unverified: int = 0
    outdated: int = 0


class AuditRequest(BaseModel):
    question: str = Field(..., description="Original user prompt or research question", min_length=3)
    answer: str = Field(..., description="Generated answer from the AI agent to be verified", min_length=5)
    context: Optional[str] = Field(None, description="Optional background context or domain hints")
    max_claims: Optional[int] = Field(5, ge=1, le=10, description="Max atomic claims to audit in single run")


class AuditResponse(BaseModel):
    audit_id: str = Field(..., description="Unique SharedOS audit transaction ID")
    reliability: int = Field(..., ge=0, le=100, description="Reliability score from 0 to 100")
    verdict_summary: str = Field(..., description="High-level assessment")
    stats: AuditStats = Field(..., description="Aggregate breakdown of claim verdicts")
    claims: List[ClaimAudit] = Field(default_factory=list, description="Individual audited claims with evidence")
    recommendation: str = Field(..., description="Actionable advisory for calling agent before showing to user")
    repaired_answer: Optional[str] = Field(None, description="Automatically repaired answer text with factual corrections applied")
    execution_latency_ms: int = Field(..., description="Processing time in milliseconds")
    sharedos_purpose: str = Field(..., description="SharedOS verified purpose string")
    credits_billed: int = Field(5, description="Arena credits billed for this transaction")
    remaining_credits: Optional[int] = Field(None, description="Current caller Arena credits balance after deduction")
