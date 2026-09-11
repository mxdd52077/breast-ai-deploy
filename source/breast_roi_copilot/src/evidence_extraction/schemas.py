"""AI candidate evidence and human review contracts."""

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ReviewStatus(str, Enum):
    AI_CANDIDATE = "AI candidate"
    NEEDS_REVIEW = "Needs review"
    APPROVED = "Approved"
    REJECTED = "Rejected"
    SUPERSEDED = "Superseded"


class ExtractedEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pmid: str
    title: str
    study_design: str
    population: str
    sample_size: int | None = Field(default=None, ge=1)
    intervention: str
    comparator: str
    outcome: str
    effect_measure: str | None = None
    effect_value: float | None = None
    confidence_interval_low: float | None = None
    confidence_interval_high: float | None = None
    unit: str | None = None
    time_horizon: str | None = None
    evidence_excerpt: str
    candidate_roi_parameter: str | None = None
    directly_usable: bool = False
    conversion_required: bool = False
    evidence_strength: str
    limitations: list[str] = Field(min_length=1)
    review_status: ReviewStatus = ReviewStatus.AI_CANDIDATE

    @model_validator(mode="after")
    def validate_numeric_bundle(self):
        if self.effect_value is None and any(
            value is not None
            for value in (self.confidence_interval_low, self.confidence_interval_high)
        ):
            raise ValueError("Confidence intervals require an effect value.")
        if (
            self.confidence_interval_low is not None
            and self.confidence_interval_high is not None
            and self.confidence_interval_low > self.confidence_interval_high
        ):
            raise ValueError("Confidence interval lower bound exceeds upper bound.")
        return self
