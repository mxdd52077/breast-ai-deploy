"""Structured output contract for evidence-grounded answers."""

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class EvidenceStatus(str, Enum):
    SUPPORTED = "Supported"
    PARTIALLY_SUPPORTED = "Partially supported"
    INSUFFICIENT = "Insufficient evidence"
    CONFLICTING = "Conflicting evidence"


class SupportingClaim(BaseModel):
    model_config = ConfigDict(extra="forbid")

    claim: str = Field(min_length=1)
    pmids: list[str] = Field(min_length=1)
    evidence_excerpt: str = Field(
        min_length=1,
        description="An exact excerpt copied from one of the cited PubMed abstracts.",
    )


class GroundedAnswer(BaseModel):
    model_config = ConfigDict(extra="forbid")

    answer: str = Field(min_length=1)
    evidence_status: EvidenceStatus
    supporting_claims: list[SupportingClaim]
    evidence_limitations: list[str] = Field(min_length=1)
    retrieved_pmids: list[str]
