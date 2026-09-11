"""Parameter recommendation and human decision contracts."""

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class EvidenceSufficiency(str, Enum):
    SUFFICIENT = "Sufficient for recommendation"
    INSUFFICIENT = "Relevant but insufficient"
    CONVERSION_REQUIRED = "Conversion required"
    NO_EVIDENCE = "No approved evidence"


class DecisionAction(str, Enum):
    KEEP = "Keep original"
    ACCEPT = "Accept recommendation"
    EDIT = "Edit manually"
    RESET = "Reset to default"


class ParameterRecommendation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    parameter_name: str
    display_name: str
    original_value: float
    unit: str
    recommended_value: float | None = None
    lower_bound: float | None = None
    upper_bound: float | None = None
    evidence_sufficiency: EvidenceSufficiency
    rationale: str
    pmids: list[str]
    can_accept: bool = False


class ParameterDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    parameter_name: str
    original_value: float
    recommended_value: float | None
    final_value: float
    unit: str
    action: DecisionAction
    pmids: list[str]
    decision_note: str = Field(min_length=1)
    updated_at: str
