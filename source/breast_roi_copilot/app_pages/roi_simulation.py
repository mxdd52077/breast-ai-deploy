"""Deterministic breast screening ROI simulation page."""

from dataclasses import asdict
from pathlib import Path

import pandas as pd
import streamlit as st

from src.charts import cost_impact_chart, screening_reach_chart, sensitivity_chart
from src.copilot import ParameterDecisionRepository
from src.i18n import t
from src.models import MODEL_SCOPE_ZH, SUPPORTED_SCREENING_MODALITY, BreastROIInputs, calculate_breast_roi

st.caption(t("Configure a screening scenario and compare its clinical and financial value with the documented R-model baseline."))
st.info("调整三个业务参数，查看扩大乳腺筛查覆盖可能带来的临床与财务价值。", icon=":material/info:")
st.info(MODEL_SCOPE_ZH, icon=":material/verified:")

DATA_DIR = Path(__file__).parents[1] / "data"
decision_repository = ParameterDecisionRepository(
    DATA_DIR / "parameter_decisions.csv",
    DATA_DIR / "parameter_decision_audit.jsonl",
)
confirmed_decisions = decision_repository.latest_by_parameter()

default_inputs = BreastROIInputs()
assistant_snapshot = st.session_state.get("assistant_roi_inputs_snapshot")
approved_population = st.session_state.get("approved_population")
approved_metadata = st.session_state.get("approved_population_metadata") or {}

# A hospital upload normally contains population facts, not every ROI assumption.
# Only replace the three values that can be derived from the approved dataset;
# preserve the documented R-model defaults for costs and clinical assumptions.
seed_inputs = asdict(default_inputs)
seed_source = "r_defaults"
if assistant_snapshot:
    seed_inputs.update({key: value for key, value in assistant_snapshot.items() if key in seed_inputs})
    seed_source = "assistant_confirmed"
elif approved_population is not None and not approved_population.empty:
    seed_inputs["population_size"] = int(len(approved_population))
    if "age" in approved_population:
        seed_inputs["average_age"] = int(round(float(approved_population["age"].mean())))
    if "years_since_screen" in approved_population:
        seed_inputs["current_screening_rate"] = float(
            (approved_population["years_since_screen"] < default_inputs.screening_interval).mean() * 100
        )
    seed_source = (
        f"hospital:{approved_metadata.get('source_name', 'approved')}:{len(approved_population)}"
    )

seed_signature = f"{seed_source}:{repr(sorted(seed_inputs.items()))}"
if st.session_state.get("advanced_roi_seed_context") != seed_signature:
    for field_name, value in seed_inputs.items():
        st.session_state[f"advanced_roi_{field_name}"] = value
    st.session_state.advanced_roi_seed_context = seed_signature

parameter_decision_keys = {
    "followup_completion_rate": "advanced_roi_followup_completion_rate",
    "cancer_detection_per_1000": "advanced_roi_cancer_detection_per_1000",
    "lives_saved_per_1000": "advanced_roi_lives_saved_per_1000",
    "regional_to_local_shift": "advanced_roi_regional_to_local_shift",
    "distant_to_regional_shift": "advanced_roi_distant_to_regional_shift",
}
for parameter_name, decision in confirmed_decisions.items():
    state_key = parameter_decision_keys.get(parameter_name)
    if state_key:
        version_key = f"advanced_roi_decision_version_{parameter_name}"
        if st.session_state.get(version_key) != decision["updated_at"]:
            st.session_state[state_key] = float(decision["final_value"])
            st.session_state[version_key] = decision["updated_at"]

if confirmed_decisions:
    with st.container(horizontal=True):
        st.badge(
            f"{len(confirmed_decisions)} {t('confirmed parameter(s)')}",
            color="green",
            icon=":material/verified_user:",
        )
        st.badge(t("Deterministic calculation"), color="blue", icon=":material/calculate:")

if assistant_snapshot:
    st.success(
        "已载入AI决策助手中人工确认的医院场景。你在本页的调整只用于高级仿真，不会反向修改助手场景。",
        icon=":material/sync_alt:",
    )
elif approved_population is not None and not approved_population.empty:
    st.success(
        "已载入医院数据推导的人群规模、平均年龄和当前筛查率；其余参数继续使用原R模型默认值。",
        icon=":material/database:",
    )
else:
    st.caption("当前未发现AI助手确认场景，页面使用原R模型默认值作为演示起点。")

with st.sidebar:
    st.subheader("核心场景")
    st.caption("只调整最常用的三个业务参数，结果会立即更新。")
    population_size = st.number_input(
        "目标人群规模", min_value=1_000, step=1_000,
        key="advanced_roi_population_size",
    )
    current_rate = st.slider(
        "当前筛查率（%）", 0.0, 100.0,
        key="advanced_roi_current_screening_rate",
    )
    target_rate = st.slider(
        "目标筛查率（%）", 0.0, 100.0,
        key="advanced_roi_target_screening_rate",
    )
    st.caption(f"筛查方式：{SUPPORTED_SCREENING_MODALITY}（当前版本固定）")

# Keep the interview demo intentionally simple. These values still feed the
# unchanged R-model migration, but are not exposed as business-user controls.
average_age = int(st.session_state["advanced_roi_average_age"])
mammography_cost = float(st.session_state["advanced_roi_mammography_cost"])
screening_interval = float(st.session_state["advanced_roi_screening_interval"])
recall_rate = float(st.session_state["advanced_roi_recall_rate"])
followup_cost = float(st.session_state["advanced_roi_followup_cost"])
followup_completion = float(st.session_state["advanced_roi_followup_completion_rate"])
detection_rate = float(st.session_state["advanced_roi_cancer_detection_per_1000"])
lives_saved_rate = float(st.session_state["advanced_roi_lives_saved_per_1000"])
localized = float(st.session_state["advanced_roi_localized_stage_percent"])
regional = float(st.session_state["advanced_roi_regional_stage_percent"])
distant = float(st.session_state["advanced_roi_distant_stage_percent"])
unknown = float(st.session_state["advanced_roi_unknown_stage_percent"])
redistribute = bool(st.session_state["advanced_roi_redistribute_unknown_stage"])
localized_cost = float(st.session_state["advanced_roi_localized_stage_cost"])
regional_cost = float(st.session_state["advanced_roi_regional_stage_cost"])
distant_cost = float(st.session_state["advanced_roi_distant_stage_cost"])
regional_shift = float(st.session_state["advanced_roi_regional_to_local_shift"])
distant_shift = float(st.session_state["advanced_roi_distant_to_regional_shift"])

st.caption("其余临床与成本假设沿用原R模型默认值，不需要在演示中逐项配置。")

inputs = BreastROIInputs(
    population_size=int(population_size), current_screening_rate=current_rate,
    target_screening_rate=target_rate, average_age=average_age,
    mammography_cost=mammography_cost, screening_interval=screening_interval,
    recall_rate=recall_rate, followup_cost=followup_cost,
    followup_completion_rate=followup_completion,
    cancer_detection_per_1000=detection_rate, lives_saved_per_1000=lives_saved_rate,
    redistribute_unknown_stage=redistribute, localized_stage_percent=localized,
    regional_stage_percent=regional, distant_stage_percent=distant,
    unknown_stage_percent=unknown, localized_stage_cost=localized_cost,
    regional_stage_cost=regional_cost, distant_stage_cost=distant_cost,
    regional_to_local_shift=regional_shift, distant_to_regional_shift=distant_shift,
)
result = calculate_breast_roi(inputs)
baseline = calculate_breast_roi(BreastROIInputs())

# Share the exact deterministic model snapshot with downstream report pages.
# The LLM receives these outputs; it never recomputes them.
st.session_state["roi_inputs_snapshot"] = asdict(inputs)
st.session_state["roi_results_snapshot"] = asdict(result)

if target_rate < current_rate:
    st.warning(t("Target rate is below the current rate. As in the R model, additional screening volume is set to zero."))

def money(value): return f"${value:,.0f}"
def delta(value, base, suffix=""): return f"{value - base:+,.1f}{suffix} vs R defaults"

st.subheader(t("Scenario value"))
cols = st.columns(4)
cols[0].metric(t("Additional screened"), f"{result.additional_screened:,.0f}", delta(result.additional_screened, baseline.additional_screened), border=True)
cols[1].metric(t("Detected cases"), f"{result.detected_breast_cancer_cases:,.1f}", delta(result.detected_breast_cancer_cases, baseline.detected_breast_cancer_cases), border=True)
cols[2].metric(t("Net savings"), money(result.net_savings), money(result.net_savings - baseline.net_savings), border=True)
cols[3].metric(t("Modeled ROI"), "N/A" if result.roi is None else f"{result.roi:.1%}", t("Net savings / program cost"), border=True)

with st.container(border=True):
    st.markdown(f"**{t('Clinical outcome detail')}**")
    clinical = st.columns(3)
    clinical[0].metric(t("Lives saved"), f"{result.lives_saved:,.1f}")
    clinical[1].metric(t("Recalled patients"), f"{result.recalled_patients:,.0f}")
    clinical[2].metric(t("Completed follow-ups"), f"{result.completed_followups:,.0f}")

left, right = st.columns(2)
with left.container(border=True, height="stretch"):
    st.markdown(f"**{t('Financial impact')}**")
    st.plotly_chart(cost_impact_chart(result), width="stretch")
with right.container(border=True, height="stretch"):
    st.markdown(f"**{t('Screening reach')}**")
    st.plotly_chart(screening_reach_chart(result), width="stretch")

with st.expander("技术细节（面试演示无需展开）", icon=":material/functions:"):
    st.subheader(t("Sensitivity analysis"))
    st.caption(t("One-way sensitivity of modeled net savings to the target screening rate."))
    st.plotly_chart(sensitivity_chart(inputs, "target_screening_rate", list(range(60, 96, 5))), width="stretch")
    st.markdown(
        "**Calculation boundary:** Parameter Copilot can supply only human-confirmed inputs. "
        "All outcomes below are calculated by the Python migration of the original R formulas; the LLM performs no mathematics."
    )
    output = asdict(result)
    st.dataframe(
        pd.DataFrame({t("Metric"): output.keys(), t("Value"): [str(value) for value in output.values()]}),
        hide_index=True,
    )
