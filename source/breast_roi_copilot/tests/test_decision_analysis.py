from src.models import BreastROIInputs, calculate_breast_roi
from src.reporting import (
    build_management_recommendations,
    build_planning_scenarios,
    build_sensitivity_analysis,
)


def test_planning_scenarios_keep_base_result_and_inputs_unchanged():
    inputs = BreastROIInputs()
    scenarios = build_planning_scenarios(inputs)

    assert [row["情景"] for row in scenarios] == ["保守情景", "基准情景", "积极情景"]
    assert scenarios[1]["净节约"] == calculate_breast_roi(inputs).net_savings
    assert inputs == BreastROIInputs()


def test_sensitivity_analysis_is_ranked_and_uses_current_result():
    inputs = BreastROIInputs()
    base = calculate_breast_roi(inputs)
    rows = build_sensitivity_analysis(inputs)

    assert len(rows) == 5
    assert all(row["当前净节约"] == base.net_savings for row in rows)
    assert all(row["影响范围"] >= 0 for row in rows)
    assert [row["影响范围"] for row in rows] == sorted(
        [row["影响范围"] for row in rows], reverse=True
    )


def test_management_recommendations_name_top_driver():
    scenarios = build_planning_scenarios(BreastROIInputs())
    sensitivities = build_sensitivity_analysis(BreastROIInputs())
    actions = build_management_recommendations(scenarios, sensitivities)

    assert sensitivities[0]["参数"] in actions[0]
    assert any("试点" in action for action in actions)
