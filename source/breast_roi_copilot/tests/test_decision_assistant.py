import pytest
from pydantic import ValidationError

from src.decision_assistant.scenario_parser import ScenarioDraft


def test_scenario_contract_accepts_partial_hospital_input():
    draft = ScenarioDraft(
        population_size=100_000,
        current_screening_rate=55,
        target_screening_rate=70,
        average_age=None,
        screening_modality="DBT",
        cancer_detection_per_1000=None,
        recall_rate=None,
        missing_fields=["average_age", "cancer_detection_per_1000", "recall_rate"],
        assumptions=[],
        pubmed_query="DBT cancer detection rate per 1000 recall screening",
    )
    assert draft.target_screening_rate == 70


def test_scenario_contract_rejects_invalid_percentage():
    with pytest.raises(ValidationError):
        ScenarioDraft(
            population_size=100_000, current_screening_rate=120, target_screening_rate=70,
            average_age=55, screening_modality="DBT", cancer_detection_per_1000=None,
            recall_rate=None, missing_fields=[], assumptions=[], pubmed_query="DBT screening",
        )
