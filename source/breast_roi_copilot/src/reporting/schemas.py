"""Strict contracts for generated and reviewed executive reports."""

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class ReportAudience(str, Enum):
    EXECUTIVE = "Executive"
    CLINICAL = "Clinical"
    PAYER = "Payer"


class ReportStatus(str, Enum):
    DRAFT = "Draft"
    APPROVED = "Approved"


class EvidenceClaim(BaseModel):
    model_config = ConfigDict(extra="forbid")

    claim: str = Field(min_length=1)
    pmids: list[str] = Field(min_length=1)
    evidence_excerpt: str = Field(min_length=1)


class SimulationSnapshot(BaseModel):
    """Exact, fixed-schema copy of deterministic ROI output for Structured Outputs."""

    model_config = ConfigDict(extra="forbid")

    screening_modality: str
    population_size: int
    current_screening_rate: float
    target_screening_rate: float
    incremental_screening_rate: float
    additional_screened: float
    age_band: str
    breast_incidence_per_100k: float
    age_adjustment_factor: float
    detected_breast_cancer_cases: float
    lives_saved: float
    localized_share: float
    regional_share: float
    distant_share: float
    stage_distribution_method: str
    stage_shift_savings_per_case: float
    treatment_cost_avoided: float
    recalled_patients: float
    completed_followups: float
    screening_cost_total: float
    followup_cost_total: float
    screening_program_cost: float
    net_savings: float
    roi: float | None


class ExecutiveReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    audience: ReportAudience
    executive_summary: str = Field(min_length=1)
    clinical_impact: str = Field(min_length=1)
    financial_impact: str = Field(min_length=1)
    evidence_interpretation: str = Field(min_length=1)
    key_assumptions: list[str] = Field(min_length=1)
    limitations: list[str] = Field(min_length=1)
    recommended_actions: list[str] = Field(min_length=1)
    evidence_claims: list[EvidenceClaim]
    cited_pmids: list[str]
    # Exact machine-readable copy, validated against the ROI engine output.
    simulation_snapshot: SimulationSnapshot
