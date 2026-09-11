"""Source-backed patient care report page."""

import streamlit as st

from src.patient_companion.report import build_report
from src.patient_companion.ui_state import get_case, initialize_patient_state

initialize_patient_state()
case = get_case()
if case is None:
    st.warning("请先在“我的档案”上传资料或加载模拟病例。")
    st.stop()

report = build_report(case)
st.warning("本报告用于资料整理和就医准备，不构成诊断或治疗建议。")

with st.container(border=True):
    st.subheader("当前照护概览")
    st.write(report.overview)

left, right = st.columns(2)
with left:
    st.subheader("已确认的关键结果")
    if report.key_results:
        for item in report.key_results:
            st.markdown(f"- {item}")
    else:
        st.info("还没有已确认的关键结果。")
with right:
    st.subheader("当前安排")
    if report.current_arrangements:
        for item in report.current_arrangements:
            st.markdown(f"- {item}")
    else:
        st.info("确认医嘱或复诊信息后，这里会显示安排。")

st.subheader("仍需确认")
if report.needs_confirmation:
    for item in report.needs_confirmation:
        st.markdown(f"- {item}")
else:
    st.success("当前提取信息均已核对。")

st.subheader("下次就诊可以询问")
for question in report.visit_questions:
    st.markdown(f"- {question}")
