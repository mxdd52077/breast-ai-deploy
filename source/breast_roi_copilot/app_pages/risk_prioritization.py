"""Limited-capacity outreach prioritization simulation."""

from dataclasses import asdict

import pandas as pd
import streamlit as st

from src.i18n import t
from src.models import BreastROIInputs, calculate_breast_roi
from src.population import SyntheticPopulationConfig, generate_synthetic_population
from src.prioritization import OutreachEconomics, simulate_prioritization


@st.cache_data(max_entries=20)
def load_population(size: int, seed: int, noise: float) -> pd.DataFrame:
    return generate_synthetic_population(SyntheticPopulationConfig(size, seed, noise))


st.caption("当医院联系名额有限时，比较“随机联系”与“优先联系最需要的人”哪种方式更有效。")
st.info(
    "业务问题：如果只能联系一部分患者，怎样把有限的短信、电话和运营人力用在更需要筛查的人身上？",
    icon=":material/contact_phone:",
)
approved_population = st.session_state.get("approved_population")
approved_metadata = st.session_state.get("approved_population_metadata", {})
if approved_population is None:
    st.warning(
        "当前使用10,000名虚拟患者进行产品演示，结果属于场景估算，不是真实医院运营结果。",
        icon=":material/science:",
    )
else:
    st.success(
        f"已读取医院数据：{approved_metadata.get('source_name', '已上传数据')} · {len(approved_population):,}人",
        icon=":material/verified:",
    )

saved = st.session_state.get("synthetic_population_settings", {})
population_size = (
    len(approved_population)
    if approved_population is not None
    else int(st.session_state.get("priority_population_size", saved.get("population_size", 10_000)))
)
with st.sidebar:
    st.subheader("外展计划")
    st.metric("当前可分析人群", f"{population_size:,}人")
    outreach_capacity = st.number_input(
        "本轮最多联系人数", 100, int(population_size), min(2_000, int(population_size)), 100,
        help="医院本轮能够通过短信、电话或人工随访主动联系的最大人数。",
    )
    cost_per_outreach = st.number_input(
        "每联系一人的成本（美元）", 0.0, 500.0, 12.0, 1.0,
        help="包含短信、电话、人工时间或外展系统成本。",
    )

with st.expander("技术设置（演示时无需修改）", icon=":material/settings:"):
    st.caption("这些设置只用于让模拟结果可重复、可比较，不是医院业务参数。")
    if approved_population is None:
        population_size = st.number_input(
            "虚拟患者人数", 1_000, 100_000, int(population_size), 1_000,
            key="priority_population_size",
        )
    random_trials = st.slider(
        "随机方案重复比较次数", 20, 500, 100, 20,
        help="系统多次随机选择患者并取平均值，避免单次抽样过于偶然。",
    )
    if approved_population is None:
        model_noise = st.slider(
            "虚拟数据不确定性", 0.20, 2.00, float(saved.get("model_noise", 0.85)), 0.05,
            key="priority_model_noise",
            help="只控制演示数据的随机差异，不是医学指标。",
        )
    seed = st.number_input(
        "可重复实验编号", 0, 100_000, int(saved.get("seed", 42)), 1,
        key="priority_seed",
        help="保持同一编号可得到相同模拟结果。",
    )

roi_input_values = st.session_state.get("roi_inputs_snapshot", asdict(BreastROIInputs()))
roi_inputs = BreastROIInputs(**roi_input_values)
roi_results = calculate_breast_roi(roi_inputs)
economics = OutreachEconomics(
    cost_per_outreach=float(cost_per_outreach),
    annualized_screening_cost=roi_inputs.mammography_cost / roi_inputs.screening_interval,
    expected_followup_cost_per_screen=(
        roi_inputs.recall_rate / 100 * roi_inputs.followup_completion_rate / 100 * roi_inputs.followup_cost
    ),
    stage_shift_savings_per_case=roi_results.stage_shift_savings_per_case,
)
population = (
    approved_population.copy()
    if approved_population is not None
    else load_population(int(population_size), int(seed), float(model_noise))
)
comparison = simulate_prioritization(
    population, int(outreach_capacity), economics, int(random_trials), int(seed)
)

random_result = comparison.random
priority_result = comparison.prioritized
uplift = lambda better, base: better - base

st.subheader("风险优先策略带来的增量价值")
st.caption(f"在同样联系{int(outreach_capacity):,}人的情况下，与随机联系相比：")
with st.container(horizontal=True):
    st.metric(
        "多覆盖应筛未筛人群",
        f"{uplift(priority_result.true_gaps_reached, random_result.true_gaps_reached):,.0f}",
        "人", border=True,
    )
    st.metric(
        "预计新增完成筛查",
        f"{uplift(priority_result.expected_completed_screenings, random_result.expected_completed_screenings):,.0f}",
        "人（期望值）", border=True,
    )
    st.metric(
        "预计额外检出病例",
        f"{uplift(priority_result.expected_detected_cases, random_result.expected_detected_cases):,.1f}",
        "例（期望值）", border=True,
    )
    st.metric(
        "预计增加的模型净节约",
        f"${uplift(priority_result.net_savings, random_result.net_savings):,.0f}",
        "相同联系名额", border=True,
    )

labels = {"Random": t("Random outreach"), "Risk-prioritized": t("Risk-prioritized outreach")}
rows = []
for result in (random_result, priority_result):
    rows.append(
        {
            t("Strategy"): labels[result.strategy],
            t("True gaps reached"): result.true_gaps_reached,
            t("Expected completed screenings"): result.expected_completed_screenings,
            t("Expected detected cases"): result.expected_detected_cases,
            t("Program cost"): result.program_cost,
            t("Net savings"): result.net_savings,
            t("Modeled ROI"): result.roi,
        }
    )
strategy_table = pd.DataFrame(rows)

left, right = st.columns([1.25, 1])
with left.container(border=True, height="stretch"):
    st.subheader("两种联系策略对比")
    simple_table = strategy_table[[
        t("Strategy"), t("True gaps reached"),
        t("Expected completed screenings"), t("Expected detected cases"),
    ]].rename(columns={
        t("Strategy"): "联系策略",
        t("True gaps reached"): "覆盖应筛未筛人群",
        t("Expected completed screenings"): "预计完成筛查",
        t("Expected detected cases"): "预计检出病例",
    })
    st.dataframe(
        simple_table,
        hide_index=True,
        column_config={
            "覆盖应筛未筛人群": st.column_config.NumberColumn(format="%.0f 人"),
            "预计完成筛查": st.column_config.NumberColumn(format="%.0f 人"),
            "预计检出病例": st.column_config.NumberColumn(format="%.1f 例"),
        },
        width="stretch",
    )
    chart = simple_table[["联系策略", "覆盖应筛未筛人群", "预计完成筛查"]]
    st.bar_chart(chart, x="联系策略", y=["覆盖应筛未筛人群", "预计完成筛查"], stack=False)

with right.container(border=True, height="stretch"):
    st.subheader("系统怎么选择优先联系对象？")
    st.markdown(
        "系统不会判断谁一定会患癌，而是优先寻找：\n\n"
        "- **目前应该筛查但尚未完成的人**\n"
        "- **距离上次筛查时间更久的人**\n"
        "- **收到提醒后更可能完成筛查的人**\n\n"
        "系统只给出建议名单，不会自动联系患者；最终名额和执行方式由医院运营人员决定。"
    )
    with st.expander("查看排序规则", icon=":material/rule:"):
        st.write("筛查缺口信号占60%，距上次筛查时间占25%，预计完成概率占15%。")

with st.expander("查看计算假设与ROI连接", icon=":material/account_tree:"):
    st.markdown(
        t("This simulation reuses the active deterministic ROI model. The LLM does not calculate these values.")
    )
    assumptions = pd.DataFrame(
        [
            {t("Assumption"): t("Annualized screening cost"), t("Value"): f"${economics.annualized_screening_cost:,.2f}"},
            {t("Assumption"): t("Expected follow-up cost per completed screen"), t("Value"): f"${economics.expected_followup_cost_per_screen:,.2f}"},
            {t("Assumption"): t("Stage-shift savings per detected case"), t("Value"): f"${economics.stage_shift_savings_per_case:,.2f}"},
            {t("Assumption"): t("Random benchmark"), t("Value"): f"{random_trials} {t('Monte Carlo trials')}"},
        ]
    )
    st.dataframe(assumptions, hide_index=True, width="stretch")

with st.expander("分析师查看：优先联系人群明细", icon=":material/groups:"):
    display = population.copy()
    display["priority_score"] = comparison.priority_score
    display["selected_for_priority_outreach"] = display["patient_id"].isin(comparison.selected_prioritized_ids)
    st.dataframe(display.sort_values("priority_score", ascending=False).head(200), hide_index=True, width="stretch")
