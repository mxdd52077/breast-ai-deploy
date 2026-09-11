"""Patient document intake and confirmation page."""

import streamlit as st

from src.patient_companion.documents import DocumentParseError, parse_document
from src.patient_companion.provider import PatientAIError, extract_case_with_openai
from src.patient_companion.review import apply_fact_review
from src.patient_companion.schemas import ConfirmationStatus
from src.patient_companion.ui_state import (
    get_case,
    get_patient_api_key,
    get_patient_model,
    initialize_patient_state,
)

initialize_patient_state()


def _clear_case_when_upload_changes() -> None:
    st.session_state.patient_case = None
    st.session_state.patient_task_status = {}


def _set_all_fact_review(fact_ids: list[str], status: ConfirmationStatus) -> None:
    for fact_id in fact_ids:
        st.session_state[f"patient_fact_{fact_id}"] = status.value


st.info(
    "这是照护导航演示，不提供诊断或治疗建议。请只上传脱敏资料；扫描件和医学影像暂不支持。",
    icon=":material/privacy_tip:",
)

with st.container(border=True):
    st.subheader("从资料建立个人照护档案")
    uploads = st.file_uploader(
        "上传文字型 PDF、DOCX 或 TXT",
        type=["pdf", "docx", "txt"],
        accept_multiple_files=True,
        key="patient_uploads",
        on_change=_clear_case_when_upload_changes,
    )
    configured_api_key = get_patient_api_key()
    patient_model = get_patient_model()
    model_label = {
        "gpt-5.6-sol": "GPT-5.6 Sol",
        "gpt-5.6-terra": "GPT-5.6 Terra",
        "gpt-5.6-luna": "GPT-5.6 Luna",
    }.get(patient_model, patient_model)
    session_api_key = ""
    if not configured_api_key:
        with st.expander("连接患者 AI", expanded=True, icon=":material/key:"):
            session_api_key = st.text_input(
                "OpenAI API Key",
                type="password",
                placeholder="sk-…",
                key="patient_api_key_input",
                help="仅保存在当前浏览器会话，不写入项目文件。",
            )
            st.caption("无需按 Enter 或保存；上传文件后直接点击分析。Key 不会写入项目文件。")
    else:
        st.caption(":material/verified_user: 患者 AI 已由服务端配置")
    actions = st.container(horizontal=True)
    analyze = actions.button(
        f"使用 {model_label} 分析",
        type="primary",
        icon=":material/auto_awesome:",
        disabled=not uploads,
    )

if analyze:
    documents = []
    try:
        for upload in uploads:
            documents.append(parse_document(upload.name, upload.getvalue()))
        api_key = session_api_key.strip() or get_patient_api_key()
        if not api_key:
            raise PatientAIError(
                "尚未配置 PATIENT_OPENAI_API_KEY，无法分析已上传资料。"
                "请先在“连接患者 AI”中填写 OpenAI API Key。"
            )
        with st.spinner("正在提取来源可追溯的字段…"):
            st.session_state.patient_case = extract_case_with_openai(
                documents,
                api_key=api_key,
                model=patient_model,
            )
        st.session_state.patient_task_status = {}
    except (DocumentParseError, PatientAIError, ValueError) as exc:
        st.error(str(exc))

case = get_case()
if case is None:
    st.caption("尚未建立档案。请上传脱敏资料并完成分析。")
else:
    st.subheader("请确认 AI 提取的事实")
    st.caption("逐条核对来源，最后保存。只有已确认的医嘱或安排才能进入任务清单。")
    fact_ids = [fact.id for fact in case.facts]
    for fact in case.facts:
        st.session_state.setdefault(
            f"patient_fact_{fact.id}",
            fact.confirmation_status.value,
        )
    bulk_actions = st.container(horizontal=True, vertical_alignment="center")
    bulk_actions.caption("批量设置")
    bulk_actions.button(
        "全部确认",
        icon=":material/check_circle:",
        on_click=_set_all_fact_review,
        args=(fact_ids, ConfirmationStatus.CONFIRMED),
    )
    bulk_actions.button(
        "全部待确认",
        icon=":material/pending:",
        on_click=_set_all_fact_review,
        args=(fact_ids, ConfirmationStatus.NEEDS_CONFIRMATION),
    )
    bulk_actions.button(
        "全部排除",
        icon=":material/block:",
        on_click=_set_all_fact_review,
        args=(fact_ids, ConfirmationStatus.REJECTED),
    )
    choices: dict[str, str | None] = {}
    with st.form("patient_fact_review", border=False):
        for fact in case.facts:
            with st.container(border=True):
                fact_col, source_col, status_col = st.columns(
                    [5.4, 1.2, 2.4],
                    vertical_alignment="center",
                )
                fact_col.markdown(f"**{fact.category}** · {fact.value}")
                with source_col.popover(
                    "来源",
                    icon=":material/description:",
                    type="tertiary",
                ):
                    st.caption(f"{fact.source_document_id} · 第 {fact.source_page} 页")
                    st.markdown(f"> {fact.original_text}")
                choices[fact.id] = status_col.selectbox(
                    f"{fact.category}核对结果",
                    [status.value for status in ConfirmationStatus],
                    key=f"patient_fact_{fact.id}",
                    label_visibility="collapsed",
                    width="stretch",
                )
        saved = st.form_submit_button(
            "保存核对结果",
            type="primary",
            icon=":material/save:",
        )

    if saved:
        try:
            case = apply_fact_review(case, choices)
            st.session_state.patient_case = case
            st.session_state.patient_task_status = {}
            st.success("核对结果已保存，照护报告和任务清单已同步更新。")
        except ValueError as exc:
            st.error(str(exc))

    confirmed = sum(f.confirmation_status is ConfirmationStatus.CONFIRMED for f in case.facts)
    actionable_events = sum(
        event.confirmation_status is ConfirmationStatus.CONFIRMED
        for event in case.events
    )
    st.success(
        f"已确认 {confirmed}/{len(case.facts)} 条，已整理出 {actionable_events} 项照护安排。"
    )
    if confirmed:
        st.subheader("下一步")
        st.caption("确认结果已经生效。你可以继续查看报告，或进入任务清单追踪安排。")
        with st.container(horizontal=True):
            st.page_link("app_pages/patient_report.py", label="查看照护报告", icon=":material/assignment:")
            st.page_link("app_pages/patient_tasks.py", label=f"查看照护日历（{actionable_events}）", icon=":material/calendar_month:")
