"""Unified evidence search, extraction review, and value-library page."""

import json
from pathlib import Path

import pandas as pd
import streamlit as st

from src.evidence import PubMedArticle, PubMedClient, PubMedError
from src.evidence_extraction import ExtractionValidationError, ReviewStatus, validate_extraction
from src.evidence_extraction.extractor import extract_with_openai
from src.library import CareGapLibraryRepository
from src.rag.answer_generator import EvidenceGenerationError


DATA_DIR = Path(__file__).parents[1] / "data"
repository = CareGapLibraryRepository(
    DATA_DIR / "care_gap_value_library.csv", DATA_DIR / "care_gap_audit.jsonl"
)


def safe_secret(name: str, default: str = "") -> str:
    try:
        return str(st.secrets.get(name, default))
    except Exception:
        return default


@st.cache_data(ttl="1h", max_entries=30, show_spinner=False)
def search_pubmed(query: str, limit: int = 10) -> list[PubMedArticle]:
    return PubMedClient().search(query, limit)


def render_candidate(candidate) -> None:
    st.dataframe(
        pd.DataFrame([
            {"字段": "研究设计", "提取结果": candidate.study_design},
            {"字段": "研究人群", "提取结果": candidate.population},
            {"字段": "干预", "提取结果": candidate.intervention},
            {"字段": "对照", "提取结果": candidate.comparator},
            {"字段": "结局", "提取结果": candidate.outcome},
            {"字段": "效应指标", "提取结果": candidate.effect_measure or "未报告"},
            {"字段": "效应值", "提取结果": candidate.effect_value if candidate.effect_value is not None else "未报告"},
            {"字段": "候选ROI参数", "提取结果": candidate.candidate_roi_parameter or "未映射"},
            {"字段": "可直接使用", "提取结果": "是" if candidate.directly_usable else "否"},
            {"字段": "证据强度", "提取结果": candidate.evidence_strength},
        ]),
        hide_index=True,
        width="stretch",
    )
    st.markdown(f"**已校验原文**\n\n> {candidate.evidence_excerpt}")
    if candidate.limitations:
        st.markdown("**局限性**")
        for limitation in candidate.limitations:
            st.write(f"- {limitation}")


st.caption("一个页面完成：检索真实PubMed记录 → AI提取效应量 → 人工审核 → 保存到Care Gap Value Library。")
st.info("文献不会自动修改ROI。只有通过原文校验并经人工审核的记录才会进入价值库。", icon=":material/verified_user:")

step = st.segmented_control(
    "当前步骤",
    ["1. 检索文献", "2. 提取与审核", "3. 查看价值库"],
    default="1. 检索文献",
    key="evidence_library_step",
)

if step == "1. 检索文献":
    st.subheader("检索与模型参数直接相关的研究")
    with st.form("unified_evidence_search", border=True):
        topic = st.selectbox(
            "需要补充哪类证据？",
            ["癌症检出率", "召回率", "Stage shift / 分期前移", "筛查临床效果", "自定义"],
        )
        templates = {
            "癌症检出率": '("digital breast tomosynthesis" OR DBT) AND breast screening AND "cancer detection rate" AND (meta-analysis OR systematic review)',
            "召回率": '("digital breast tomosynthesis" OR DBT) AND breast screening AND "recall rate" AND (meta-analysis OR systematic review)',
            "Stage shift / 分期前移": 'breast cancer screening AND ("stage shift" OR "stage distribution" OR "advanced stage incidence")',
            "筛查临床效果": 'breast cancer screening AND (mortality OR early detection) AND (meta-analysis OR systematic review)',
            "自定义": "",
        }
        query = st.text_area("PubMed检索式", value=templates[topic], height=100)
        submitted = st.form_submit_button("检索PubMed", type="primary", icon=":material/search:")
    if submitted:
        if not query.strip():
            st.error("请输入检索词。")
        else:
            try:
                with st.spinner("正在检索PubMed……"):
                    st.session_state.evidence_articles = search_pubmed(query.strip(), 10)
                st.session_state.evidence_source = "live"
            except PubMedError as exc:
                st.error(str(exc), icon=":material/cloud_off:")
    articles = st.session_state.get("evidence_articles", [])
    if articles:
        st.success(f"找到 {len(articles)} 篇真实PubMed记录。选择合适文献后进入第2步。")
        for article in articles:
            with st.expander(f"PMID {article.pmid} · {article.title}"):
                st.write(article.abstract)
                st.link_button("打开PubMed", article.pubmed_url, icon=":material/open_in_new:")

elif step == "2. 提取与审核":
    articles = st.session_state.get("evidence_articles", [])
    if not articles:
        st.warning("当前没有检索结果。请先返回第1步检索文献。", icon=":material/search:")
        st.stop()
    options = {f"PMID {article.pmid} — {article.title}": article for article in articles}
    selected_label = st.selectbox("选择一篇文献", list(options))
    selected_article = options[selected_label]
    with st.expander("查看摘要"):
        st.write(selected_article.abstract)
    if st.button("AI提取效应量", type="primary", icon=":material/data_object:"):
        try:
            with st.spinner("AI正在提取，并执行PMID、原文和数字校验……"):
                unvalidated = extract_with_openai(
                    selected_article,
                    safe_secret("OPENAI_API_KEY"),
                    safe_secret("OPENAI_MODEL", "gpt-5.6-luna"),
                )
                st.session_state.extraction_candidate = validate_extraction(unvalidated, selected_article)
                st.session_state.extraction_article = selected_article
            st.success("候选结果已通过本地校验。")
        except (ExtractionValidationError, EvidenceGenerationError, ValueError) as exc:
            st.session_state.pop("extraction_candidate", None)
            st.error(str(exc), icon=":material/shield:")
    candidate = st.session_state.get("extraction_candidate")
    candidate_article = st.session_state.get("extraction_article")
    if candidate and candidate_article and candidate_article.pmid == selected_article.pmid:
        st.subheader("待人工审核的AI候选结果")
        render_candidate(candidate)
        reviewer_note = st.text_area("审核说明（必填）", placeholder="说明为什么批准或拒绝，以及适用范围。")
        with st.container(horizontal=True):
            approve = st.button("批准并存入价值库", type="primary", icon=":material/check_circle:")
            reject = st.button("拒绝候选结果", icon=":material/cancel:")
        if approve or reject:
            try:
                status = ReviewStatus.APPROVED if approve else ReviewStatus.REJECTED
                repository.save_review(candidate, status, reviewer_note)
                st.session_state.pop("extraction_candidate", None)
                st.toast("审核记录已保存。", icon=":material/save:")
                st.rerun()
            except ValueError as exc:
                st.error(str(exc))

else:
    records = repository.list_records()
    if not records:
        st.info("价值库目前为空。完成第2步人工审核后，记录会出现在这里。")
    else:
        frame = pd.DataFrame(records)
        approved = int((frame["review_status"] == "Approved").sum())
        with st.container(horizontal=True):
            st.metric("已审核记录", len(frame), border=True)
            st.metric("已批准", approved, border=True)
            st.metric("已拒绝", len(frame) - approved, border=True)
        display = frame[[
            "pmid", "outcome", "effect_measure", "effect_value", "unit",
            "candidate_roi_parameter", "evidence_strength", "review_status",
            "reviewer_note", "updated_at",
        ]].rename(columns={
            "pmid": "PMID", "outcome": "结局", "effect_measure": "效应指标",
            "effect_value": "效应值", "unit": "单位",
            "candidate_roi_parameter": "候选ROI参数", "evidence_strength": "证据强度",
            "review_status": "审核状态", "reviewer_note": "审核说明", "updated_at": "更新时间",
        })
        st.dataframe(display, hide_index=True, width="stretch")
        selected = st.selectbox("查看记录详情", frame["record_id"].tolist())
        record = frame.loc[frame["record_id"] == selected].iloc[-1]
        with st.container(border=True):
            st.subheader(record["title"])
            st.markdown(f"**已校验原文**\n\n> {record['evidence_excerpt']}")
            limitations = json.loads(record["limitations"]) if record["limitations"] else []
            for limitation in limitations:
                st.write(f"- {limitation}")
            st.link_button("打开PubMed", f"https://pubmed.ncbi.nlm.nih.gov/{record['pmid']}/", icon=":material/open_in_new:")
