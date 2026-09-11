"""Generate, validate, review, and approve an evidence-grounded report."""

import json
from pathlib import Path

import streamlit as st

from src.library import CareGapLibraryRepository
from src.i18n import is_zh, t
from src.models import BreastROIInputs, calculate_breast_roi
from src.reporting import (
    ExecutiveReport,
    ExecutiveReportRepository,
    ReportAudience,
    ReportGenerationError,
    ReportValidationError,
    generate_report_with_openai,
    validate_executive_report,
)
from src.reporting.demo_provider import build_demo_report

DATA_DIR = Path(__file__).parents[1] / "data"
library = CareGapLibraryRepository(
    DATA_DIR / "care_gap_value_library.csv",
    DATA_DIR / "care_gap_audit.jsonl",
)
reports = ExecutiveReportRepository(
    DATA_DIR / "executive_reports.json",
    DATA_DIR / "executive_report_audit.jsonl",
)

st.caption(t("Create an audience-ready decision brief from deterministic ROI outputs and human-approved PubMed evidence."))

default_inputs = BreastROIInputs()
default_result = calculate_breast_roi(default_inputs)
roi_inputs = st.session_state.get("roi_inputs_snapshot", vars(default_inputs))
roi_output = st.session_state.get("roi_results_snapshot", vars(default_result))
has_live_snapshot = "roi_results_snapshot" in st.session_state
approved_evidence = [
    row for row in library.list_records() if row.get("review_status") == "Approved"
]

if not has_live_snapshot:
    st.warning(
        "No current-session ROI snapshot was found, so the documented R-default scenario is shown. "
        "Visit ROI simulation first to report on your current scenario.",
        icon=":material/info:",
    )

with st.container(horizontal=True):
    st.badge(f"1 · {t('Scenario snapshot')}", color="green", icon=":material/check_circle:")
    st.badge(f"2 · {t('Generate draft')}", color="blue", icon=":material/auto_awesome:")
    st.badge(f"3 · {t('Human approval')}", color="gray", icon=":material/verified_user:")

st.subheader(t("Scenario snapshot"))
snapshot = st.columns(4)
snapshot[0].metric(t("Additional screened"), f"{float(roi_output['additional_screened']):,.0f}", border=True)
snapshot[1].metric(t("Detected cases"), f"{float(roi_output['detected_breast_cancer_cases']):,.1f}", border=True)
snapshot[2].metric(t("Net savings"), f"${float(roi_output['net_savings']):,.0f}", border=True)
with snapshot[3]:
    roi = roi_output.get("roi")
    st.metric(t("Modeled ROI"), "N/A" if roi is None else f"{float(roi):.1%}", border=True)

with st.container(horizontal=True):
    st.badge(
        f"{len(approved_evidence)} approved evidence record(s)",
        color="green" if approved_evidence else "orange",
        icon=":material/library_books:",
    )
    st.badge(t("ROI snapshot locked"), color="blue", icon=":material/lock:")

try:
    api_key = str(st.secrets.get("OPENAI_API_KEY", ""))
    model = str(st.secrets.get("OPENAI_MODEL", "gpt-5.6-luna"))
except Exception:
    api_key = ""
    model = "gpt-5.6-luna"

st.subheader(t("Generate report"))
with st.container(border=True):
    controls = st.columns([1, 1])
    mode = controls[0].segmented_control(
        t("Generation mode"),
        [t("Verified demo"), t("Live AI")],
        default=t("Verified demo"),
        key="report_generation_mode",
    )
    audience = controls[1].selectbox(
        t("Report audience"),
        [t(member.value) for member in ReportAudience],
        key="report_audience",
    )
    is_demo = mode == t("Verified demo")
    if is_demo:
        st.caption(t("Verified demo creates a deterministic sample report and makes no LLM API call."))
    elif not api_key:
        st.warning(
            "Live AI is not configured. Add OPENAI_API_KEY to .streamlit/secrets.toml and restart the app.",
            icon=":material/key:",
        )
    generate = st.button(
        t("Generate draft report"),
        type="primary",
        icon=":material/auto_awesome:",
        disabled=not is_demo and not api_key,
    )

if generate:
    try:
        audience_value = next(member.value for member in ReportAudience if t(member.value) == audience)
        output_language = "Chinese" if is_zh() else "English"
        if not is_demo:
            draft = generate_report_with_openai(
                audience,
                dict(roi_inputs),
                dict(roi_output),
                approved_evidence,
                api_key,
                model,
                output_language,
            )
        else:
            draft = build_demo_report(
                ReportAudience(audience_value), dict(roi_output), approved_evidence, output_language
            )
        validated = validate_executive_report(
            draft, dict(roi_output), approved_evidence, dict(roi_inputs)
        )
        st.session_state["executive_report_draft"] = validated.model_dump(mode="json")
        st.session_state["executive_report_source_mode"] = mode
        st.session_state["executive_report_language"] = st.session_state.get("app_language", "中文")
        st.success(t("Draft generated and passed ROI snapshot, PMID, and excerpt validation."))
    except (ValueError, ReportGenerationError, ReportValidationError) as exc:
        st.error(str(exc), icon=":material/error:")

draft_data = (
    st.session_state.get("executive_report_draft")
    if st.session_state.get("executive_report_language")
    == st.session_state.get("app_language", "中文")
    else None
)
if draft_data:
    st.subheader(t("Review draft"))
    with st.container(horizontal=True):
        st.badge(t("AI-generated draft"), color="blue", icon=":material/auto_awesome:")
        st.badge(t("Numeric fidelity passed"), color="green", icon=":material/check:")
        st.badge(t("Citation validation passed"), color="green", icon=":material/check:")
        st.badge(t("Human review pending"), color="orange", icon=":material/pending:")
    st.caption(t("Edit the narrative if needed. Approval reruns every deterministic validation."))
    with st.form("executive_report_review", border=True):
        narrative, evidence_panel = st.columns([1.65, 1], gap="large")
        with narrative:
            st.markdown(f"#### {t('Decision brief')}")
            executive_summary = st.text_area(
                t("Executive summary"), value=draft_data["executive_summary"], height=120
            )
            clinical_impact = st.text_area(
                t("Clinical impact"), value=draft_data["clinical_impact"], height=100
            )
            financial_impact = st.text_area(
                t("Financial impact"), value=draft_data["financial_impact"], height=100
            )
            evidence_interpretation = st.text_area(
                t("Evidence interpretation"),
                value=draft_data["evidence_interpretation"],
                height=100,
            )
        with evidence_panel:
            st.markdown(f"#### {t('Evidence and controls')}")
            st.markdown(f"**{t('Evidence claims')}**")
            if draft_data["evidence_claims"]:
                for claim in draft_data["evidence_claims"]:
                    pmid_links = ", ".join(
                        f"[PMID {pmid}](https://pubmed.ncbi.nlm.nih.gov/{pmid}/)"
                        for pmid in claim["pmids"]
                    )
                    st.write(f"{claim['claim']} — {pmid_links}")
                    st.caption(f"{t('Verified excerpt')}: {claim['evidence_excerpt']}")
            else:
                st.warning(t("Insufficient evidence. No evidence claim is included."))
            with st.expander(t("Key assumptions"), icon=":material/checklist:"):
                for item in draft_data["key_assumptions"]:
                    st.write(f"- {item}")
            with st.expander(t("Limitations"), icon=":material/warning:"):
                for item in draft_data["limitations"]:
                    st.write(f"- {item}")
            with st.expander(t("Recommended actions"), icon=":material/task_alt:"):
                for item in draft_data["recommended_actions"]:
                    st.write(f"- {item}")
        reviewer_note = st.text_area(
            t("Human approval note"),
            placeholder="Explain why this report is suitable for decision-support use.",
        )
        approve = st.form_submit_button(
            t("Approve report"), type="primary", icon=":material/verified:"
        )

    if approve:
        try:
            edited = dict(draft_data)
            edited.update(
                {
                    "executive_summary": executive_summary,
                    "clinical_impact": clinical_impact,
                    "financial_impact": financial_impact,
                    "evidence_interpretation": evidence_interpretation,
                }
            )
            report = ExecutiveReport.model_validate(edited)
            validate_executive_report(
                report, dict(roi_output), approved_evidence, dict(roi_inputs)
            )
            record = reports.save_approved(
                report,
                reviewer_note,
                st.session_state.get("executive_report_source_mode", "Unknown"),
            )
            st.session_state["approved_executive_report"] = record
            st.success(
                f"Approved as {record['report_id']}. The report and audit event were saved.",
                icon=":material/check_circle:",
            )
        except (ValueError, ReportValidationError) as exc:
            st.error(str(exc), icon=":material/error:")

approved = st.session_state.get("approved_executive_report")
if approved:
    st.download_button(
        t("Download approved report (JSON)"),
        data=json.dumps(approved, ensure_ascii=False, indent=2),
        file_name=f"{approved['report_id']}.json",
        mime="application/json",
        icon=":material/download:",
    )

with st.expander(t("Governance and prompt rules"), icon=":material/policy:"):
    st.markdown(
        """
        - ROI values are copied from the deterministic simulation and validated exactly.
        - Medical claims may cite only human-approved Care Gap Library records.
        - Every cited excerpt must exist in its approved record.
        - The LLM cannot apply parameters, recalculate ROI, or approve its own report.
        - Approved reports require a reviewer note and create an audit event.
        """
    )
