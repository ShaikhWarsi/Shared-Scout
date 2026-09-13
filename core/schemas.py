"""
AgentScout Data Schemas & Protocols
Strict Pydantic models for A2A requests, claim extraction, evidence retrieval,
adversarial attack audits, multi-agent committee consensus, and Pre-Ship Firewall Gates.
"""

from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class VerdictEnum(str, Enum):
    SUPPORTED = "SUPPORTED"
    CONTRADICTED = "CONTRADICTED"
    UNVERIFIED = "UNVERIFIED"
    OUTDATED = "OUTDATED"


class AuditMode(str, Enum):
    VERIFY = "VERIFY"
    ATTACK = "ATTACK"


class GateStatusEnum(str, Enum):
    APPROVED_CLEAN = "APPROVED_CLEAN"
    BLOCKED_UNSAFE = "BLOCKED_UNSAFE"
    REPAIRED_AND_APPROVED = "REPAIRED_AND_APPROVED"


class EvidenceItem(BaseModel):
    source_url: str = Field(..., description="URL or origin of the corroborated evidence")
    source_title: str = Field("", description="Title of the source webpage or publication")
    snippet: str = Field(..., description="Exact textual excerpt supporting or refuting the claim")
    published_date: Optional[str] = Field(None, description="Publication or update date if detected")
    reliability_weight: float = Field(1.0, description="Source authority/reliability weighting factor (0.0 to 1.0)")
    freshness_days: Optional[int] = Field(None, description="Estimated age of citation in days")
    authority_score: float = Field(0.90, description="Domain authority rating (0.0 to 1.0)")


class SourceConflict(BaseModel):
    has_conflict: bool = False
    conflicting_sources: List[str] = Field(default_factory=list)
    resolution_rationale: Optional[str] = None
    winning_source: Optional[str] = None


class CommitteeVote(BaseModel):
    agent_name: str = Field(..., description="Name of the committee agent (Researcher, Skeptic, SourceJudge)")
    role: str = Field(..., description="Role in verification committee")
    verdict: VerdictEnum
    confidence: float = 0.90
    argument: str


class ClaimAudit(BaseModel):
    claim_id: int = Field(..., description="Sequential claim index")
    claim_text: str = Field(..., description="Atomic factual statement isolated from the answer")
    verdict: VerdictEnum = Field(..., description="Verification outcome")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score for this verdict")
    evidence: List[EvidenceItem] = Field(default_factory=list, description="Gathered external evidence snippets")
    contradiction_details: Optional[str] = Field(None, description="Explanation if claim is contradicted or outdated")
    correction: Optional[str] = Field(None, description="Correct factual replacement if contradicted")
    source_conflict: Optional[SourceConflict] = None
    committee_votes: List[CommitteeVote] = Field(default_factory=list, description="Votes from Researcher, Skeptic, and Judge agents")
    knowledge_decay_risk: str = Field("LOW", description="Knowledge decay risk rating: LOW, MEDIUM, HIGH")


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
    mode: AuditMode = Field(AuditMode.VERIFY, description="Audit mode: 'VERIFY' (standard) or 'ATTACK' (adversarial contradiction hunting)")


class AuditResponse(BaseModel):
    audit_id: str = Field(..., description="Unique SharedOS audit transaction ID")
    reliability: int = Field(..., ge=0, le=100, description="Reliability score from 0 to 100")
    verdict_summary: str = Field(..., description="High-level assessment")
    mode: AuditMode = Field(AuditMode.VERIFY, description="Mode executed ('VERIFY' or 'ATTACK')")
    stats: AuditStats = Field(..., description="Aggregate breakdown of claim verdicts")
    claims: List[ClaimAudit] = Field(default_factory=list, description="Individual audited claims with evidence")
    recommendation: str = Field(..., description="Actionable advisory for calling agent before showing to user")
    repaired_answer: Optional[str] = Field(None, description="Automatically repaired answer text with factual corrections applied")
    execution_latency_ms: int = Field(..., description="Processing time in milliseconds")
    sharedos_purpose: str = Field(..., description="SharedOS verified purpose string")
    credits_billed: int = Field(5, description="Arena credits billed for this transaction")
    remaining_credits: Optional[int] = Field(None, description="Current caller Arena credits balance after deduction")
    gate_status: Optional[GateStatusEnum] = Field(None, description="Firewall Pre-Ship Gate decision status")


class FirewallGateRequest(BaseModel):
    question: str
    answer: str
    min_reliability_threshold: int = Field(80, ge=50, le=100, description="Minimum reliability score required to pass gate")
    auto_repair: bool = Field(True, description="Whether to automatically repair and re-evaluate if initial draft is blocked")
    strict_attack_mode: bool = Field(False, description="Run adversarial attack mode during gate inspection")


class FirewallGateResponse(BaseModel):
    gate_id: str = Field(..., description="Unique Firewall Gate Evaluation ID")
    status: GateStatusEnum = Field(..., description="Pre-Ship Gate status: APPROVED_CLEAN, BLOCKED_UNSAFE, REPAIRED_AND_APPROVED")
    initial_reliability: int
    final_reliability: int
    blocked_reasons: List[str] = Field(default_factory=list)
    initial_answer: str
    safe_to_ship_answer: str
    audit_autopsy: AuditResponse
    credits_billed: int = 5
    latency_ms: int
    verification_receipt: Optional[Dict[str, Any]] = Field(default=None, description="Cryptographically anchored AgentScout Verification & Clearance Receipt")
