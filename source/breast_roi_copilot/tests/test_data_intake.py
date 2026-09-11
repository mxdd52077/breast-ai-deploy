import pandas as pd
import pytest

from src.data_intake import DerivationConfig, deidentify_patient_ids, validate_population_dataset
from src.models import BreastROIInputs
from src.population import SyntheticPopulationConfig, generate_synthetic_population


def _hospital_data():
    return pd.DataFrame(
        {
            "patient_id": ["SYN-1", "SYN-2", "SYN-3", "SYN-4"],
            "is_synthetic": [True] * 4,
            "as_of_date": ["2026-08-01"] * 4,
            "age": [45, 55, 65, 74],
            "last_screen_date": ["2023-08-01", "2025-08-01", None, "2020-08-01"],
            "never_screened": [False, False, True, False],
            "has_active_appointment": [False, False, False, True],
            "outreach_consent": [True, True, True, True],
            "prior_abnormal": [False, True, False, False],
            "family_history": [False, False, True, False],
        }
    )


def _legacy_data(size=200):
    data = generate_synthetic_population(SyntheticPopulationConfig(population_size=size, seed=9))
    data.insert(1, "is_synthetic", True)
    return data


def test_hospital_raw_dataset_derives_downstream_fields():
    normalized, report = validate_population_dataset(_hospital_data())
    assert report.passed and report.is_synthetic and report.input_schema == "hospital_raw"
    assert normalized["ground_truth_gap"].tolist() == [True, False, True, False]
    assert normalized.loc[2, "years_since_screen"] == 20
    assert set(("years_since_screen", "care_gap_score", "completion_probability", "detection_probability")).issubset(normalized.columns)


def test_detection_probability_uses_r_rate_and_age_adjustment():
    inputs = BreastROIInputs(cancer_detection_per_1000=10.0)
    normalized, _ = validate_population_dataset(_hospital_data(), DerivationConfig(roi_inputs=inputs))
    assert normalized.loc[1, "detection_probability"] == pytest.approx(0.01 * 273.1 / 239.8, abs=1e-6)


def test_appointment_and_no_consent_exclude_outreach_gap():
    data = _hospital_data()
    data.loc[0, "outreach_consent"] = False
    normalized, _ = validate_population_dataset(data)
    assert not normalized.loc[0, "ground_truth_gap"]
    assert not normalized.loc[3, "ground_truth_gap"]


def test_invalid_hospital_date_blocks_derivation():
    data = _hospital_data()
    data.loc[0, "last_screen_date"] = "2030-01-01"
    normalized, report = validate_population_dataset(data)
    assert not report.passed
    assert "ground_truth_gap" not in normalized


def test_legacy_dataset_remains_compatible():
    normalized, report = validate_population_dataset(_legacy_data())
    assert report.passed and report.input_schema == "legacy_derived"
    assert "care_gap_score" in normalized


def test_missing_required_hospital_and_legacy_fields_blocks_approval():
    _, report = validate_population_dataset(pd.DataFrame({"patient_id": ["x"], "age": [50]}))
    assert not report.passed


def test_unmarked_dataset_is_warned_and_hashable():
    data = _hospital_data().drop(columns=["is_synthetic"])
    normalized, report = validate_population_dataset(data)
    assert report.passed and not report.is_synthetic
    hashed = deidentify_patient_ids(normalized, salt="test")
    assert hashed["patient_id"].str.startswith("HASH-").all()
