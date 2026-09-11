"""Pure Python migration of the R Shiny breast cancer value model."""

from .schemas import BreastROIInputs, BreastROIResults

AGE_INCIDENCE = (
    (40, 44, "40-44", 135.8),
    (45, 49, "45-49", 204.7),
    (50, 54, "50-54", 239.8),
    (55, 59, "55-59", 273.1),
    (60, 64, "60-64", 341.6),
    (65, 69, "65-69", 425.1),
    (70, 74, "70-74", 479.3),
)
REFERENCE_INCIDENCE = 239.8


def get_age_band(age: int) -> tuple[str, float]:
    """Match the R lookup; invalid/out-of-range ages fall back to age 50."""
    selected_age = age if isinstance(age, (int, float)) and 40 <= age <= 74 else 50
    for minimum, maximum, band, incidence in AGE_INCIDENCE:
        if minimum <= selected_age <= maximum:
            return band, incidence
    return "50-54", REFERENCE_INCIDENCE


def _stage_distribution(inputs: BreastROIInputs) -> tuple[float, float, float, str]:
    localized = inputs.localized_stage_percent
    regional = inputs.regional_stage_percent
    distant = inputs.distant_stage_percent
    unknown = inputs.unknown_stage_percent
    known_total = localized + regional + distant

    # Exact R fallback when every known-stage input is zero.
    if known_total <= 0:
        localized, regional, distant, unknown = 63.0, 28.0, 6.0, 3.0
        known_total = 97.0

    if inputs.redistribute_unknown_stage:
        adjusted = tuple(x + unknown * x / known_total for x in (localized, regional, distant))
        total = sum(adjusted)
        return *(x / total for x in adjusted), "Unknown redistributed"

    # R divides by 100 here; if inputs do not sum to 100, they intentionally
    # remain non-normalized.
    return localized / 100, regional / 100, distant / 100, "Unknown excluded"


def calculate_breast_roi(inputs: BreastROIInputs) -> BreastROIResults:
    """Calculate clinical and financial outputs without UI or LLM involvement."""
    inputs.validate()
    age_band, incidence = get_age_band(inputs.average_age)
    age_factor = incidence / REFERENCE_INCIDENCE
    localized, regional, distant, method = _stage_distribution(inputs)

    regional_savings = regional * inputs.regional_to_local_shift / 100 * (
        inputs.regional_stage_cost - inputs.localized_stage_cost
    )
    distant_savings = distant * inputs.distant_to_regional_shift / 100 * (
        inputs.distant_stage_cost - inputs.regional_stage_cost
    )
    savings_per_case = regional_savings + distant_savings

    incremental_rate = inputs.target_screening_rate - inputs.current_screening_rate
    additional_screened = max(inputs.population_size * incremental_rate / 100, 0.0)
    detected_cases = additional_screened * inputs.cancer_detection_per_1000 / 1000 * age_factor
    lives_saved = additional_screened * inputs.lives_saved_per_1000 / 1000
    treatment_cost_avoided = detected_cases * savings_per_case
    screening_cost = additional_screened * inputs.mammography_cost / inputs.screening_interval
    recalled = additional_screened * inputs.recall_rate / 100
    completed_followups = recalled * inputs.followup_completion_rate / 100
    followup_cost = completed_followups * inputs.followup_cost
    program_cost = screening_cost + followup_cost
    net_savings = treatment_cost_avoided - program_cost

    return BreastROIResults(
        screening_modality=inputs.screening_modality,
        population_size=inputs.population_size,
        current_screening_rate=inputs.current_screening_rate,
        target_screening_rate=inputs.target_screening_rate,
        incremental_screening_rate=incremental_rate,
        additional_screened=additional_screened,
        age_band=age_band,
        breast_incidence_per_100k=incidence,
        age_adjustment_factor=age_factor,
        detected_breast_cancer_cases=detected_cases,
        lives_saved=lives_saved,
        localized_share=localized,
        regional_share=regional,
        distant_share=distant,
        stage_distribution_method=method,
        stage_shift_savings_per_case=savings_per_case,
        treatment_cost_avoided=treatment_cost_avoided,
        recalled_patients=recalled,
        completed_followups=completed_followups,
        screening_cost_total=screening_cost,
        followup_cost_total=followup_cost,
        screening_program_cost=program_cost,
        net_savings=net_savings,
        roi=net_savings / program_cost if program_cost > 0 else None,
    )
