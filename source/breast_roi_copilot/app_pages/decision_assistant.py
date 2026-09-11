"""Hospital-first decision assistant with lookup only for missing parameters."""

from dataclasses import asdict
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from src.decision_assistant.parameter_plan import LOOKUP_ROUTES, build_parameter_plan
from src.library import CareGapLibraryRepository
from src.models import (
    MODEL_SCOPE_ZH,
    SUPPORTED_SCREENING_MODALITY,
    BreastROIInputs,
    calculate_breast_roi,
)
from src.reporting import (
    ReportAudience,
    build_demo_report,
    build_management_recommendations,
    build_planning_scenarios,
    build_sensitivity_analysis,
    generate_report_with_openai,
    validate_executive_report,
)


DATA_DIR = Path(__file__).parents[1] / "data"
SOURCE_LINKS = {
    "SEER": "https://seer.cancer.gov/statistics-network/explorer/",
    "CMS": "https://www.cms.gov/medicare/payment/fee-schedules",
    "USPSTF": "https://www.uspreventiveservicestaskforce.org/uspstf/recommendation/breast-cancer-screening",
    "PubMed": "https://pubmed.ncbi.nlm.nih.gov/",
}


def safe_secret(name: str, default: str = "") -> str:
    try:
        return str(st.secrets.get(name, default))
    except Exception:
        return default


def approved_evidence() -> list[dict[str, str]]:
    repo = CareGapLibraryRepository(DATA_DIR / "care_gap_value_library.csv", DATA_DIR / "care_gap_audit.jsonl")
    return [row for row in repo.list_records() if row.get("review_status") == "Approved"]


st.caption("先使用医院数据；只有缺失参数才查外部依据。AI不计算ROI，也不会自动改参数。")
st.info(MODEL_SCOPE_ZH, icon=":material/verified:")
st.info(
    "正确顺序：医院材料 → 缺失项检查 → 按参数补充来源 → 人工确认 → 原R公式计算 → 报告。",
    icon=":material/route:",
)

for key, default in {
    "assistant_scenario": None, "assistant_result": None, "assistant_report": None,
    "assistant_parameter_sources": {}, "assistant_report_notice": None,
}.items():
    st.session_state.setdefault(key, default)

st.subheader("1. 提供医院情况")
approved_population = st.session_state.get("approved_population")
metadata = st.session_state.get("approved_population_metadata")
if approved_population is None:
    # A clean start must never display or reuse the historical demo scenario.
    for key in (
        "assistant_scenario", "assistant_result", "assistant_report",
        "assistant_report_notice",
        "assistant_parameter_sources", "assistant_detection_value",
        "assistant_recall_value", "assistant_dataset_signature",
    ):
        st.session_state.pop(key, None)
    st.warning("当前没有医院数据。请先从顶部进入“数据接入”，上传并应用 CSV 数据集。")
    st.info("上传后回到本页，系统会自动读取人群规模、平均年龄和当前筛查率。这里不会显示或使用任何演示医院数据。")
else:
    dataset_signature = None
    dataset_signature = f"{metadata.get('source_name', '')}:{len(approved_population)}"
    if st.session_state.get("assistant_dataset_signature") != dataset_signature:
        # Never allow an old manual/demo scenario to survive a dataset change.
        st.session_state.assistant_scenario = None
        st.session_state.assistant_result = None
        st.session_state.assistant_report = None
        st.session_state.assistant_report_notice = None
        st.session_state.assistant_parameter_sources = {}
        st.session_state.assistant_dataset_signature = dataset_signature
        for widget_key in ("assistant_detection_value", "assistant_recall_value"):
            st.session_state.pop(widget_key, None)

    st.success(
        f"已读取当前会话医院数据：{metadata.get('source_name', '已批准数据集')}，"
        f"{len(approved_population):,} 行。",
        icon=":material/database:",
    )

    if st.session_state.assistant_scenario is None:
        st.write("医院数据已经提供了人群规模、年龄和当前筛查情况。请只补充数据集中没有的目标筛查率：")
        with st.form("dataset_scenario_setup", border=True):
            target_from_hospital = st.number_input("目标筛查率（%）", 0.0, 100.0, 70.0, step=1.0)
            st.markdown(f"**筛查方式：** {SUPPORTED_SCREENING_MODALITY}（当前版本固定）")
            setup_dataset = st.form_submit_button("使用医院数据建立分析场景", type="primary", icon=":material/arrow_forward:")
        if setup_dataset:
            st.session_state.assistant_scenario = {
                "population_size": None,
                "current_screening_rate": None,
                "target_screening_rate": float(target_from_hospital),
                "average_age": None,
                "screening_modality": SUPPORTED_SCREENING_MODALITY,
                "cancer_detection_per_1000": None,
                "recall_rate": None,
                "missing_fields": ["cancer_detection_per_1000", "recall_rate"],
                "assumptions": ["人群规模、平均年龄和当前筛查率由已批准医院数据集推导。"],
                "pubmed_query": "DBT breast screening cancer detection recall meta-analysis",
            }
            st.rerun()

    if st.session_state.assistant_scenario is not None:
        draft = st.session_state.assistant_scenario
        plan = build_parameter_plan(draft, approved_population)

        st.subheader("2. 系统检查已知与缺失参数")
        rows = []
        for item in plan:
            rows.append({
                "参数": item.label,
                "当前值": "待补充" if item.value is None else str(item.value),
                "来源类型": item.source_type,
                "来源说明": item.source_detail,
                "缺失时去哪里找": item.lookup_route or "—",
            })
        st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")

        missing = [item for item in plan if item.value is None]
        if not missing:
            st.success("运行ROI所需的基础参数已齐全。你可以直接进入确认步骤。", icon=":material/check_circle:")
        else:
            st.warning(f"发现 {len(missing)} 个缺失参数。只需要处理这些项目，不必先搜索一批随机文献。")

        st.subheader("3. 只补充缺失参数")
        defaults = BreastROIInputs()
        source_records = st.session_state.assistant_parameter_sources
        for item in missing:
            with st.container(border=True):
                st.markdown(f"**{item.label}**")
                st.write(f"建议来源：{item.lookup_route}")
                if item.key == "cancer_detection_per_1000":
                    st.link_button("打开PubMed定向检索", SOURCE_LINKS["PubMed"] + "?term=%28digital+breast+tomosynthesis+OR+DBT%29+AND+breast+screening+AND+cancer+detection+rate+AND+meta-analysis", icon=":material/open_in_new:")
                    default_value = defaults.cancer_detection_per_1000
                else:
                    st.link_button("打开PubMed定向检索", SOURCE_LINKS["PubMed"] + "?term=%28digital+breast+tomosynthesis+OR+DBT%29+AND+breast+screening+AND+recall+rate+AND+meta-analysis", icon=":material/open_in_new:")
                    default_value = defaults.recall_rate
                with st.form(f"missing_{item.key}", border=False):
                    value = st.number_input("填写候选值", min_value=0.0, value=float(default_value), step=0.1)
                    source_kind = st.selectbox("来源", ["R模型默认值", "医院数据", "PubMed文献", "其他官方来源", "情景假设"])
                    source_detail = st.text_input("来源说明", placeholder="例如：PMID、医院报表名称、SEER年份或假设理由")
                    save = st.form_submit_button("保存该参数及来源", type="primary", icon=":material/save:")
                if save:
                    source_records[item.key] = {"value": float(value), "source": source_kind, "detail": source_detail or "未补充详细说明"}
                    st.session_state.assistant_parameter_sources = source_records
                    st.rerun()
                if item.key in source_records:
                    saved = source_records[item.key]
                    st.success(f"已保存：{saved['value']:g}；来源：{saved['source']}；{saved['detail']}")

        with st.expander("其他模型参数来自哪里？", icon=":material/source:"):
            st.write("发病率和分期分布优先使用SEER；成本优先使用医院财务数据，缺失时参考CMS；筛查年龄与频率参考官方指南；Stage shift证据不足时应作为敏感性假设。")
            with st.container(horizontal=True):
                for label in ("SEER", "CMS", "USPSTF", "PubMed"):
                    st.link_button(label, SOURCE_LINKS[label], icon=":material/open_in_new:")

        st.subheader("4. 人工确认并运行原R模型公式")
        plan_map = {item.key: item.value for item in plan}
        detection_record = source_records.get("cancer_detection_per_1000")
        recall_record = source_records.get("recall_rate")
        st.session_state.setdefault("assistant_detection_value", float(detection_record["value"] if detection_record else defaults.cancer_detection_per_1000))
        st.session_state.setdefault("assistant_recall_value", float(recall_record["value"] if recall_record else defaults.recall_rate))

        with st.form("hospital_first_confirmation", border=True):
            population = st.number_input("目标人群规模", min_value=1_000, value=int(plan_map["population_size"]), step=1_000)
            current_rate = st.number_input("当前筛查率（%）", 0.0, 100.0, float(plan_map["current_screening_rate"]))
            target_rate = st.number_input("目标筛查率（%）", 0.0, 100.0, float(plan_map["target_screening_rate"]))
            average_age = st.number_input("平均年龄", 40, 74, int(plan_map["average_age"]))
            st.markdown(f"**筛查方式：** {SUPPORTED_SCREENING_MODALITY}（当前版本固定）")
            detection = st.number_input("癌症检出率（每千次筛查）", min_value=0.0, step=0.1, key="assistant_detection_value")
            recall = st.number_input("召回率（%）", 0.0, 100.0, step=0.1, key="assistant_recall_value")
            acknowledge = st.checkbox("我已检查参数值及来源；缺乏证据的数值已明确标记为默认值或情景假设。")
            confirmed = st.form_submit_button("确认并运行ROI", type="primary", icon=":material/calculate:")

        if confirmed:
            if not acknowledge:
                st.error("请先确认参数来源。")
            else:
                inputs = BreastROIInputs(**{
                    **asdict(defaults), "population_size": int(population),
                    "current_screening_rate": float(current_rate), "target_screening_rate": float(target_rate),
                    "average_age": int(average_age), "screening_modality": SUPPORTED_SCREENING_MODALITY,
                    "cancer_detection_per_1000": float(detection), "recall_rate": float(recall),
                })
                result = calculate_breast_roi(inputs)
                st.session_state.roi_inputs_snapshot = asdict(inputs)
                st.session_state.assistant_roi_inputs_snapshot = asdict(inputs)
                st.session_state.roi_results_snapshot = asdict(result)
                st.session_state.assistant_result = asdict(result)
                st.session_state.assistant_report = None

        if st.session_state.assistant_result:
            result = st.session_state.assistant_result
            st.subheader("5. ROI结果")
            with st.container(horizontal=True):
                st.metric("新增筛查", f"{result['additional_screened']:,.0f}", border=True)
                st.metric("预计检出病例", f"{result['detected_breast_cancer_cases']:.1f}", border=True)
                st.metric("模型净节约", f"${result['net_savings']:,.0f}", border=True)
                st.metric("模型ROI", "N/A" if result["roi"] is None else f"{result['roi']:.1%}", border=True)
            with st.expander("查看计算过程", icon=":material/functions:"):
                st.caption("以下结果来自确定性ROI模型，不是大模型计算结果。")
                st.dataframe(pd.DataFrame({"指标": result.keys(), "数值": [str(v) for v in result.values()]}), hide_index=True, width="stretch")

            st.subheader("6. 生成管理层报告")
            live_report = st.checkbox("使用AI撰写报告", value=True)
            if st.button("生成报告", type="primary", icon=":material/description:"):
                evidence = approved_evidence()
                try:
                    if live_report:
                        report = generate_report_with_openai(
                            "Executive", st.session_state.roi_inputs_snapshot, result, evidence,
                            safe_secret("OPENAI_API_KEY"), safe_secret("OPENAI_MODEL", "gpt-5.6-luna"), "Chinese",
                        )
                    else:
                        report = build_demo_report(ReportAudience.EXECUTIVE, result, evidence, "Chinese")
                    st.session_state.assistant_report = validate_executive_report(
                        report, result, evidence, st.session_state.roi_inputs_snapshot
                    ).model_dump(mode="json")
                    st.session_state.assistant_report_notice = None
                except Exception as exc:
                    if live_report:
                        # Never leave the user with an empty report. If a live draft fails the
                        # strict number/citation gate, fall back to the deterministic template,
                        # which uses the same ROI output and still provides actionable next steps.
                        try:
                            fallback = build_demo_report(
                                ReportAudience.EXECUTIVE, result, evidence, "Chinese"
                            )
                            st.session_state.assistant_report = validate_executive_report(
                                fallback, result, evidence, st.session_state.roi_inputs_snapshot
                            ).model_dump(mode="json")
                            st.session_state.assistant_report_notice = (
                                "AI草稿中的数字或引用未通过安全校验，系统已自动切换为经过校验的规则版决策简报。"
                            )
                        except Exception as fallback_exc:
                            st.error(f"报告生成或校验失败：{fallback_exc}")
                    else:
                        st.error(f"报告生成或校验失败：{exc}")

        if st.session_state.assistant_report:
            report = st.session_state.assistant_report

            if st.session_state.get("assistant_report_notice"):
                st.warning(st.session_state.assistant_report_notice, icon=":material/shield:")

            def display_report_text(value: str) -> None:
                """Render report prose without treating currency signs as LaTeX."""
                st.markdown(str(value).replace("$", r"\$"))

            result = st.session_state.assistant_result
            analysis_inputs = BreastROIInputs(**st.session_state.assistant_roi_inputs_snapshot)
            planning_scenarios = build_planning_scenarios(analysis_inputs)
            sensitivity_rows = build_sensitivity_analysis(analysis_inputs)
            management_actions = build_management_recommendations(
                planning_scenarios, sensitivity_rows
            )
            st.subheader("管理层决策简报")
            st.caption("先看结论、压力测试和行动建议，再按需查看模型假设与证据附录。")

            with st.container(border=True):
                st.markdown("### 决策结论")
                display_report_text(report["executive_summary"])

            with st.container(horizontal=True, horizontal_alignment="distribute"):
                st.metric("新增筛查", f"{result['additional_screened']:,.0f}", border=True)
                st.metric("预计检出", f"{result['detected_breast_cancer_cases']:.1f}", border=True)
                st.metric("模型净节约", f"${result['net_savings']:,.0f}", border=True)
                st.metric("模型ROI", "N/A" if result["roi"] is None else f"{result['roi']:.1%}", border=True)

            st.markdown("### 一眼看懂场景变化")
            chart_left, chart_right = st.columns(2)
            with chart_left.container(border=True):
                st.markdown("**筛查覆盖率：当前 vs 目标**")
                coverage = pd.DataFrame({
                    "场景": ["当前", "目标"],
                    "筛查率（%）": [result["current_screening_rate"], result["target_screening_rate"]],
                })
                st.bar_chart(coverage, x="场景", y="筛查率（%）", horizontal=True)
            with chart_right.container(border=True):
                st.markdown("**投入与价值（美元）**")
                value = pd.DataFrame({
                    "项目": ["项目总成本", "避免治疗成本", "净节约"],
                    "金额": [result["screening_program_cost"], result["treatment_cost_avoided"], result["net_savings"]],
                })
                st.bar_chart(value, x="项目", y="金额", horizontal=True)

            st.markdown("### AI分析")
            analysis_left, analysis_right = st.columns(2)
            with analysis_left.container(border=True):
                st.markdown("**业务与临床影响**")
                display_report_text(report["clinical_impact"])
                st.caption(
                    f"预计召回 {result['recalled_patients']:,.0f} 人，完成随访 {result['completed_followups']:,.0f} 人；"
                    "这代表落地时需要准备的运营承接量。"
                )
            with analysis_right.container(border=True):
                st.markdown("**财务影响**")
                display_report_text(report["financial_impact"])

            st.markdown("### 运营承接量")
            st.caption("如果按当前目标推进，运营团队需要提前准备以下工作量。")
            with st.container(horizontal=True, horizontal_alignment="distribute"):
                st.metric("新增筛查", f"{result['additional_screened']:,.0f}", border=True)
                st.metric("预计召回", f"{result['recalled_patients']:,.0f}", border=True)
                st.metric("完成随访", f"{result['completed_followups']:,.0f}", border=True)
                st.metric("预计检出", f"{result['detected_breast_cancer_cases']:.1f}", border=True)

            st.markdown("### 三档规划情景")
            st.caption(
                "这是管理层压力测试，不是统计置信区间：保守和积极情景分别让关键效果与成本假设向不利或有利方向变化。"
            )
            with st.expander("三种情景具体怎么算？（点击查看）", icon=":material/help:"):
                st.markdown(
                    """
                    **先用一句话理解：**基准情景使用当前确认参数；保守情景假设效果更弱、成本更高；
                    积极情景假设效果更强、成本更低。三种情景最后都使用同一套 ROI 公式重新计算。

                    **“分期改善假设”是什么？**它表示模型假设筛查使部分乳腺癌更早被发现：
                    一部分区域期病例提前到局限期，一部分远处期病例提前到区域期。
                    这是压力测试使用的场景假设，不是由上传的患者 CSV 自动推断出来的结论。
                    """
                )

                base_detection = analysis_inputs.cancer_detection_per_1000
                base_screening_cost = analysis_inputs.mammography_cost
                base_recall_rate = analysis_inputs.recall_rate
                base_followup_cost = analysis_inputs.followup_cost
                base_regional_shift = analysis_inputs.regional_to_local_shift
                base_distant_shift = analysis_inputs.distant_to_regional_shift
                scenario_assumptions = pd.DataFrame(
                    [
                        {
                            "参数": "癌症检出率（每千次筛查）",
                            "保守情景": f"{base_detection * 0.9:.2f}（降低10%）",
                            "基准情景": f"{base_detection:.2f}",
                            "积极情景": f"{base_detection * 1.1:.2f}（提高10%）",
                        },
                        {
                            "参数": "区域期→局限期改善比例",
                            "保守情景": f"{base_regional_shift * 0.8:.1f}%（降低20%）",
                            "基准情景": f"{base_regional_shift:.1f}%",
                            "积极情景": f"{base_regional_shift * 1.2:.1f}%（提高20%）",
                        },
                        {
                            "参数": "远处期→区域期改善比例",
                            "保守情景": f"{base_distant_shift * 0.8:.1f}%（降低20%）",
                            "基准情景": f"{base_distant_shift:.1f}%",
                            "积极情景": f"{base_distant_shift * 1.2:.1f}%（提高20%）",
                        },
                        {
                            "参数": "单次筛查成本",
                            "保守情景": f"${base_screening_cost * 1.1:,.2f}（提高10%）",
                            "基准情景": f"${base_screening_cost:,.2f}",
                            "积极情景": f"${base_screening_cost * 0.9:,.2f}（降低10%）",
                        },
                        {
                            "参数": "召回率",
                            "保守情景": f"{min(base_recall_rate * 1.1, 100):.1f}%（提高10%）",
                            "基准情景": f"{base_recall_rate:.1f}%",
                            "积极情景": f"{max(base_recall_rate * 0.9, 0):.1f}%（降低10%）",
                        },
                        {
                            "参数": "单次随访成本",
                            "保守情景": f"${base_followup_cost * 1.1:,.2f}（提高10%）",
                            "基准情景": f"${base_followup_cost:,.2f}",
                            "积极情景": f"${base_followup_cost * 0.9:,.2f}（降低10%）",
                        },
                    ]
                )
                st.dataframe(scenario_assumptions, hide_index=True, width="stretch")
                st.caption(
                    "计算方法：系统把以上三组参数分别代入同一套由原 R 模型迁移的确定性公式，重新计算项目总成本、避免治疗成本、净节约和 ROI。"
                    "它不是在预测哪一种情景一定发生，也不是统计置信区间。"
                )
            scenario_df = pd.DataFrame(planning_scenarios)
            scenario_chart = px.bar(
                scenario_df,
                x="情景",
                y=["项目总成本", "避免治疗成本", "净节约"],
                barmode="group",
                labels={"value": "金额（美元）", "variable": "指标"},
                color_discrete_sequence=["#f59e0b", "#0f766e", "#2563eb"],
            )
            scenario_chart.update_layout(margin=dict(l=0, r=0, t=20, b=0), legend_title_text="")
            st.plotly_chart(scenario_chart, width="stretch")
            scenario_display_df = scenario_df.copy()
            scenario_display_df["ROI（%）"] = scenario_display_df["ROI"].map(
                lambda value: None if value is None else value * 100
            )
            scenario_display_df = scenario_display_df.drop(columns=["ROI"])
            st.dataframe(
                scenario_display_df,
                hide_index=True,
                width="stretch",
                column_config={
                    "新增筛查人数": st.column_config.NumberColumn(format="%.0f"),
                    "预计检出病例": st.column_config.NumberColumn(format="%.1f"),
                    "项目总成本": st.column_config.NumberColumn(format="$%.0f"),
                    "避免治疗成本": st.column_config.NumberColumn(format="$%.0f"),
                    "净节约": st.column_config.NumberColumn(format="$%.0f"),
                    "ROI（%）": st.column_config.NumberColumn(format="%.1f%%"),
                },
            )

            st.markdown("### 哪个参数最值得先核实？")
            st.caption(
                "敏感性分析就是一次只把一个参数上下调整20%，观察净节约变化。变化越大，说明管理层越应该优先核实该参数。"
            )
            top_driver = sensitivity_rows[0]
            st.info(
                f"当前最关键的决策变量是“{top_driver['参数']}”。在本次压力测试中，它带来的净节约波动约为 "
                f"${float(top_driver['影响范围']):,.0f}。",
                icon=":material/priority_high:",
            )
            sensitivity_df = pd.DataFrame(sensitivity_rows).sort_values("影响范围")
            sensitivity_chart = px.bar(
                sensitivity_df,
                x="影响范围",
                y="参数",
                orientation="h",
                custom_data=["最低净节约", "最高净节约"],
                labels={"影响范围": "净节约波动范围（美元）"},
                color_discrete_sequence=["#0f766e"],
            )
            sensitivity_chart.update_traces(
                hovertemplate="%{y}<br>波动范围：$%{x:,.0f}<br>最低净节约：$%{customdata[0]:,.0f}<br>最高净节约：$%{customdata[1]:,.0f}<extra></extra>"
            )
            sensitivity_chart.update_layout(margin=dict(l=0, r=0, t=20, b=0))
            st.plotly_chart(sensitivity_chart, width="stretch")
            with st.expander("查看敏感性分析明细", icon=":material/table_chart:"):
                st.dataframe(
                    pd.DataFrame(sensitivity_rows),
                    hide_index=True,
                    width="stretch",
                    column_config={
                        key: st.column_config.NumberColumn(format="$%.0f")
                        for key in (
                            "参数下调20%时净节约", "当前净节约", "参数上调20%时净节约",
                            "最低净节约", "最高净节约", "影响范围",
                        )
                    },
                )

            with st.container(border=True):
                st.markdown("### 建议的下一步行动")
                combined_actions = []
                for item in management_actions + report["recommended_actions"]:
                    if item not in combined_actions:
                        combined_actions.append(item)
                for index, item in enumerate(combined_actions, start=1):
                    display_report_text(f"{index}. {item}")

            with st.expander("查看关键假设与风险", icon=":material/tune:"):
                st.markdown("**关键假设**")
                for item in report["key_assumptions"]:
                    display_report_text(f"- {item}")
                st.markdown("**可能影响决策的局限**")
                for item in report["limitations"]:
                    display_report_text(f"- {item}")

            if report.get("evidence_claims") or report.get("evidence_interpretation"):
                with st.expander("查看证据附录（不直接影响当前主结论）", icon=":material/library_books:"):
                    display_report_text(report["evidence_interpretation"])
                    for claim in report.get("evidence_claims", []):
                        pmids = "、".join(claim.get("pmids", []))
                        display_report_text(f"- {claim.get('claim', '')}（PMID：{pmids}）")
