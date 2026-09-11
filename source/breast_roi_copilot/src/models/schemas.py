"""Typed inputs and outputs for the breast screening ROI model."""

from dataclasses import dataclass
from math import isfinite


SUPPORTED_SCREENING_MODALITY = "DBT / 3D mammography"
MODEL_SCOPE_ZH = "当前模型范围：40–74岁女性DBT筛查"


@dataclass(frozen=True)
class BreastROIInputs:
    population_size: int = 100_000
    current_screening_rate: float = 67.0
    target_screening_rate: float = 80.0
    average_age: int = 55
    screening_modality: str = SUPPORTED_SCREENING_MODALITY
    mammography_cost: float = 195.0
    screening_interval: float = 2.0
    recall_rate: float = 11.5
    followup_cost: float = 226.0
    followup_completion_rate: float = 80.0
    cancer_detection_per_1000: float = 6.2
    lives_saved_per_1000: float = 6.7
    redistribute_unknown_stage: bool = False
    localized_stage_percent: float = 63.0
    regional_stage_percent: float = 28.0
    distant_stage_percent: float = 6.0
    unknown_stage_percent: float = 3.0
    localized_stage_cost: float = 140_577.50
    regional_stage_cost: float = 323_283.25
    distant_stage_cost: float = 1_036_269.0
    regional_to_local_shift: float = 25.0
    distant_to_regional_shift: float = 25.0

    def validate(self) -> None:
        if self.screening_modality not in {SUPPORTED_SCREENING_MODALITY, "DBT"}:
            raise ValueError("The current ROI model supports DBT screening only.")
        numeric = {k: v for k, v in vars(self).items() if isinstance(v, (int, float)) and not isinstance(v, bool)}
        if any(not isfinite(float(v)) for v in numeric.values()):
            raise ValueError("All numeric inputs must be finite.")
        if self.population_size < 0:
            raise ValueError("population_size cannot be negative.")
        if self.screening_interval <= 0:
            raise ValueError("screening_interval must be greater than zero.")
        percent_fields = (
            "current_screening_rate", "target_screening_rate", "recall_rate",
            "followup_completion_rate", "localized_stage_percent",
            "regional_stage_percent", "distant_stage_percent",
            "unknown_stage_percent", "regional_to_local_shift",
            "distant_to_regional_shift",
        )
        if any(not 0 <= getattr(self, name) <= 100 for name in percent_fields):
            raise ValueError("Percentage inputs must be between 0 and 100.")
        nonnegative = (
            "mammography_cost", "followup_cost", "cancer_detection_per_1000",
            "lives_saved_per_1000", "localized_stage_cost",
            "regional_stage_cost", "distant_stage_cost",
        )
        if any(getattr(self, name) < 0 for name in nonnegative):
            raise ValueError("Cost and rate inputs cannot be negative.")


@dataclass(frozen=True)
class BreastROIResults:
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
