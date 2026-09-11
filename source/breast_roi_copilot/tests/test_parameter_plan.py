import pandas as pd

from src.decision_assistant.parameter_plan import build_parameter_plan


def scenario():
    return {
        "population_size": 100_000, "current_screening_rate": 55,
        "target_screening_rate": 70, "average_age": None,
        "screening_modality": "DBT", "cancer_detection_per_1000": None,
        "recall_rate": None,
    }


def test_plan_uses_hospital_input_and_flags_only_missing_clinical_parameters():
    plan = build_parameter_plan(scenario())
    mapping = {item.key: item for item in plan}
    assert mapping["population_size"].source_type == "医院输入"
    assert mapping["average_age"].source_type == "R模型默认值"
    assert mapping["cancer_detection_per_1000"].source_type == "缺失"


def test_approved_dataset_overrides_population_and_derives_current_rate():
    data = pd.DataFrame({"age": [50, 60], "years_since_screen": [1.0, 3.0]})
    mapping = {item.key: item for item in build_parameter_plan(scenario(), data)}
    assert mapping["population_size"].value == 2
    assert mapping["average_age"].value == 55
    assert mapping["current_screening_rate"].value == 50.0
    assert mapping["population_size"].source_type == "医院数据"
    assert mapping["target_screening_rate"].value == 70
