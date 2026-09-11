"""Deterministic scenario and sensitivity analysis for management reports."""

from dataclasses import replace

from src.models import BreastROIInputs, calculate_breast_roi


def _pct(value: float) -> float:
    return min(100.0, max(0.0, value))


def _scenario_row(label: str, description: str, inputs: BreastROIInputs) -> dict[str, float | str | None]:
    result = calculate_breast_roi(inputs)
    return {
        "情景": label,
        "假设说明": description,
        "新增筛查人数": result.additional_screened,
        "预计检出病例": result.detected_breast_cancer_cases,
        "项目总成本": result.screening_program_cost,
        "避免治疗成本": result.treatment_cost_avoided,
        "净节约": result.net_savings,
        "ROI": result.roi,
    }


def build_planning_scenarios(inputs: BreastROIInputs) -> list[dict[str, float | str | None]]:
    """Build transparent downside/base/upside stress scenarios.

    These are planning stress tests, not statistical confidence intervals.
    The base inputs are never mutated.
    """
    cautious = replace(
        inputs,
        cancer_detection_per_1000=inputs.cancer_detection_per_1000 * 0.9,
        mammography_cost=inputs.mammography_cost * 1.1,
        recall_rate=_pct(inputs.recall_rate * 1.1),
        followup_cost=inputs.followup_cost * 1.1,
        regional_to_local_shift=_pct(inputs.regional_to_local_shift * 0.8),
        distant_to_regional_shift=_pct(inputs.distant_to_regional_shift * 0.8),
    )
    optimistic = replace(
        inputs,
        cancer_detection_per_1000=inputs.cancer_detection_per_1000 * 1.1,
        mammography_cost=inputs.mammography_cost * 0.9,
        recall_rate=_pct(inputs.recall_rate * 0.9),
        followup_cost=inputs.followup_cost * 0.9,
        regional_to_local_shift=_pct(inputs.regional_to_local_shift * 1.2),
        distant_to_regional_shift=_pct(inputs.distant_to_regional_shift * 1.2),
    )
    return [
        _scenario_row("保守情景", "检出率与分期改善较低，筛查及随访成本较高", cautious),
        _scenario_row("基准情景", "采用当前已确认参数", inputs),
        _scenario_row("积极情景", "检出率与分期改善较高，筛查及随访成本较低", optimistic),
    ]


def build_sensitivity_analysis(inputs: BreastROIInputs) -> list[dict[str, float | str]]:
    """Run one-at-a-time ±20% sensitivity checks and rank decision drivers."""
    base = calculate_breast_roi(inputs)
    specs = [
        ("癌症检出率", lambda factor: replace(
            inputs, cancer_detection_per_1000=inputs.cancer_detection_per_1000 * factor
        )),
        ("单次筛查成本", lambda factor: replace(
            inputs, mammography_cost=inputs.mammography_cost * factor
        )),
        ("召回率", lambda factor: replace(
            inputs, recall_rate=_pct(inputs.recall_rate * factor)
        )),
        ("单次随访成本", lambda factor: replace(
            inputs, followup_cost=inputs.followup_cost * factor
        )),
        ("分期改善假设", lambda factor: replace(
            inputs,
            regional_to_local_shift=_pct(inputs.regional_to_local_shift * factor),
            distant_to_regional_shift=_pct(inputs.distant_to_regional_shift * factor),
        )),
    ]
    rows: list[dict[str, float | str]] = []
    for label, builder in specs:
        low = calculate_breast_roi(builder(0.8))
        high = calculate_breast_roi(builder(1.2))
        minimum = min(low.net_savings, high.net_savings)
        maximum = max(low.net_savings, high.net_savings)
        rows.append({
            "参数": label,
            "参数下调20%时净节约": low.net_savings,
            "当前净节约": base.net_savings,
            "参数上调20%时净节约": high.net_savings,
            "最低净节约": minimum,
            "最高净节约": maximum,
            "影响范围": maximum - minimum,
        })
    return sorted(rows, key=lambda row: float(row["影响范围"]), reverse=True)


def build_management_recommendations(
    scenarios: list[dict[str, float | str | None]],
    sensitivities: list[dict[str, float | str]],
) -> list[str]:
    """Turn deterministic analyses into bounded, decision-oriented actions."""
    actions: list[str] = []
    if sensitivities:
        actions.append(
            f"决策前优先核实“{sensitivities[0]['参数']}”，它是当前压力测试中对净节约影响最大的参数。"
        )
    conservative = next((row for row in scenarios if row["情景"] == "保守情景"), None)
    if conservative and float(conservative["净节约"] or 0) > 0:
        actions.append("三个规划情景均显示正向净节约，可考虑先开展小范围试点，再按真实完成率和成本决定是否扩容。")
    else:
        actions.append("保守情景下价值可能转负，建议先设定停止/继续阈值，通过小范围试点验证后再决定扩容。")
    actions.append("试点期间按月跟踪实际筛查完成率、召回人数、随访完成率和单人成本，并与模型假设逐项对照。")
    return actions
