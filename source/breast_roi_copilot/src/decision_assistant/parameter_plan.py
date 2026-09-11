"""Build a hospital-first parameter plan before any external evidence lookup."""

from dataclasses import dataclass

import pandas as pd

from src.models import BreastROIInputs


@dataclass(frozen=True)
class PlannedParameter:
    key: str
    label: str
    value: object | None
    source_type: str
    source_detail: str
    lookup_route: str | None = None


LOOKUP_ROUTES = {
    "cancer_detection_per_1000": "PubMed系统综述/Meta分析",
    "recall_rate": "医院影像系统；缺失时查PubMed系统综述",
    "localized_stage_percent": "SEER官方癌症登记数据",
    "regional_stage_percent": "SEER官方癌症登记数据",
    "distant_stage_percent": "SEER官方癌症登记数据",
    "mammography_cost": "医院财务数据；缺失时参考CMS",
    "followup_cost": "医院财务数据；缺失时参考CMS",
    "regional_to_local_shift": "PubMed长期研究；证据不足时作为敏感性假设",
    "distant_to_regional_shift": "PubMed长期研究；证据不足时作为敏感性假设",
}


def build_parameter_plan(
    scenario: dict,
    approved_population: pd.DataFrame | None = None,
) -> list[PlannedParameter]:
    defaults = BreastROIInputs()
    hospital_values: dict[str, object] = {}
    hospital_detail = "医院场景描述"
    if approved_population is not None and not approved_population.empty:
        hospital_detail = "当前会话已批准医院数据集"
        hospital_values["population_size"] = int(len(approved_population))
        if "age" in approved_population:
            hospital_values["average_age"] = int(round(float(approved_population["age"].mean())))
        if "years_since_screen" in approved_population:
            hospital_values["current_screening_rate"] = float(
                (approved_population["years_since_screen"] < defaults.screening_interval).mean() * 100
            )

    definitions = (
        ("population_size", "目标人群规模"),
        ("current_screening_rate", "当前筛查率（%）"),
        ("target_screening_rate", "目标筛查率（%）"),
        ("average_age", "平均年龄"),
        ("screening_modality", "筛查方式"),
        ("cancer_detection_per_1000", "癌症检出率（每千次筛查）"),
        ("recall_rate", "召回率（%）"),
    )
    plan: list[PlannedParameter] = []
    for key, label in definitions:
        if key in hospital_values:
            plan.append(PlannedParameter(key, label, hospital_values[key], "医院数据", hospital_detail))
        elif scenario.get(key) is not None:
            plan.append(PlannedParameter(key, label, scenario[key], "医院输入", "用户提供的医院场景"))
        elif key in {"cancer_detection_per_1000", "recall_rate"}:
            plan.append(PlannedParameter(key, label, None, "缺失", "尚未提供", LOOKUP_ROUTES[key]))
        else:
            plan.append(PlannedParameter(
                key, label, getattr(defaults, key), "R模型默认值",
                "原R模型迁移默认值；运行前需确认",
            ))
    return plan
