"""Offline AI evaluation and bad-case workbench."""

from pathlib import Path

import streamlit as st

from src.llm_evaluation import evaluate_cases, load_benchmark


DATA_PATH = Path(__file__).parents[1] / "data" / "llm_eval_benchmark_v1.json"


@st.cache_data
def benchmark():
    return load_benchmark(DATA_PATH)


st.caption("借鉴 Promptfoo 的测试集与版本实验流程，使用本项目自己的医疗安全评分规则。")
st.info(
    "当前为离线演示基线：答案、Token、成本与延迟是固定测试记录，不代表实时 API 实验。连接 API 后应使用同一测试集重新实测。",
    icon=":material/science:",
)

cases = benchmark()
with st.sidebar:
    st.subheader("实验设置")
    versions = st.multiselect("Prompt 版本", ["Prompt V1", "Prompt V3"], default=["Prompt V1", "Prompt V3"])
    categories = st.multiselect("案例类型", sorted({case["category"] for case in cases}), default=[])

selected = [case for case in cases if not categories or case["category"] in categories]
if not versions:
    st.warning("请至少选择一个 Prompt 版本。")
    st.stop()

results = evaluate_cases(selected, versions)
summary = results.groupby("prompt_version").agg(
    通过率=("passed", "mean"), PMID有效率=("pmid_valid", "mean"), 正确拒答率=("refusal_correct", "mean"),
    格式通过率=("format_valid", "mean"), 检索命中率=("retrieval_hit", "mean"),
    平均Token=("input_tokens", lambda s: (s + results.loc[s.index, "output_tokens"]).mean()),
    平均成本美元=("estimated_cost_usd", "mean"),
).reset_index().rename(columns={"prompt_version": "Prompt版本"})

st.subheader("版本实验结果")
with st.container(horizontal=True):
    for row in summary.to_dict("records"):
        with st.container(border=True):
            st.markdown(f"**{row['Prompt版本']}**")
            st.metric("全部规则通过率", f"{row['通过率']:.1%}")
            st.caption(f"PMID {row['PMID有效率']:.1%} · 拒答 {row['正确拒答率']:.1%} · 检索 {row['检索命中率']:.1%}")

st.dataframe(
    summary,
    hide_index=True,
    width="stretch",
    column_config={
        "通过率": st.column_config.ProgressColumn(format="percent", min_value=0, max_value=1),
        "PMID有效率": st.column_config.ProgressColumn(format="percent", min_value=0, max_value=1),
        "正确拒答率": st.column_config.ProgressColumn(format="percent", min_value=0, max_value=1),
        "格式通过率": st.column_config.ProgressColumn(format="percent", min_value=0, max_value=1),
        "检索命中率": st.column_config.ProgressColumn(format="percent", min_value=0, max_value=1),
        "平均成本美元": st.column_config.NumberColumn(format="$%.4f"),
    },
)

st.subheader("Bad Case 归因")
bad = results[~results["passed"]]
if bad.empty:
    st.success("当前筛选范围内没有失败案例。")
else:
    st.bar_chart(bad.groupby(["prompt_version", "error_type"]).size().reset_index(name="数量"), x="error_type", y="数量", color="prompt_version")
    for row in bad.to_dict("records"):
        with st.expander(f"{row['case_id']} · {row['prompt_version']} · {row['error_type']}"):
            st.markdown(f"**问题：** {row['question']}\n\n**模型回答：** {row['answer']}\n\n**预期状态：** {row['expected']}")
            st.markdown(f"**根因：** {row['root_cause'] or '待人工归因'}\n\n**修复策略：** {row['fix'] or '待制定'}")

with st.expander("查看黄金测试集", icon=":material/dataset:"):
    st.dataframe(
        [{"案例ID": c["case_id"], "类型": c["category"], "问题": c["question"], "预期状态": c["expected_status"], "应拒答": c["should_refuse"]} for c in selected],
        hide_index=True, width="stretch",
    )
    st.download_button("下载评测明细（CSV）", results.to_csv(index=False).encode("utf-8-sig"), "ai_evaluation_results_demo.csv", "text/csv", icon=":material/download:")
