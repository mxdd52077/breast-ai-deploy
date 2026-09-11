from dataclasses import replace

import pytest

from src.models import BreastROIInputs, calculate_breast_roi
from src.models.breast_roi import get_age_band


def test_default_results_match_r_formulas():
    result = calculate_breast_roi(BreastROIInputs())
    assert result.additional_screened == pytest.approx(13_000)
    assert result.age_band == "55-59"
    assert result.age_adjustment_factor == pytest.approx(273.1 / 239.8)
    assert result.detected_breast_cancer_cases == pytest.approx(13_000 * 6.2 / 1000 * (273.1 / 239.8))
    assert result.lives_saved == pytest.approx(87.1)
    assert result.recalled_patients == pytest.approx(1495)
    assert result.completed_followups == pytest.approx(1196)
    assert result.screening_cost_total == pytest.approx(1_267_500)
    assert result.followup_cost_total == pytest.approx(270_296)
    assert result.screening_program_cost == pytest.approx(1_537_796)
    expected_savings = .28 * .25 * (323_283.25 - 140_577.50) + .06 * .25 * (1_036_269 - 323_283.25)
    assert result.stage_shift_savings_per_case == pytest.approx(expected_savings)
    assert result.treatment_cost_avoided == pytest.approx(result.detected_breast_cancer_cases * expected_savings)
    assert result.roi == pytest.approx(result.net_savings / result.screening_program_cost)


def test_target_below_current_is_clamped_to_zero_like_r():
    result = calculate_breast_roi(BreastROIInputs(current_screening_rate=80, target_screening_rate=60))
    assert result.incremental_screening_rate == -20
    assert result.additional_screened == 0
    assert result.screening_program_cost == 0
    assert result.roi is None


def test_unknown_stage_redistribution_normalizes_known_stages():
    result = calculate_breast_roi(BreastROIInputs(redistribute_unknown_stage=True))
    assert result.localized_share + result.regional_share + result.distant_share == pytest.approx(1.0)
    assert result.localized_share == pytest.approx(63 / 97)


def test_zero_known_stage_inputs_use_r_fallback():
    inputs = replace(BreastROIInputs(), localized_stage_percent=0, regional_stage_percent=0, distant_stage_percent=0)
    result = calculate_breast_roi(inputs)
    assert (result.localized_share, result.regional_share, result.distant_share) == pytest.approx((.63, .28, .06))


@pytest.mark.parametrize("age,expected", [(40, "40-44"), (54, "50-54"), (74, "70-74"), (99, "50-54")])
def test_age_band_lookup(age, expected):
    assert get_age_band(age)[0] == expected


def test_invalid_screening_interval_is_rejected():
    with pytest.raises(ValueError):
        calculate_breast_roi(BreastROIInputs(screening_interval=0))


def test_current_model_rejects_non_dbt_screening_modalities():
    with pytest.raises(ValueError, match="supports DBT screening only"):
        calculate_breast_roi(BreastROIInputs(screening_modality="Digital mammography"))
