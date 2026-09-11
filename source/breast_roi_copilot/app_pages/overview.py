"""Product overview and end-to-end workflow status."""

import json
from pathlib import Path

import pandas as pd
import streamlit as st

from src.copilot import ParameterDecisionRepository
from src.i18n import t
from src.library import CareGapLibraryRepository
from src.models import BreastROIInputs, calculate_breast_roi

DATA_DIR = Path(__file__).parents[1] / "data"
library = CareGapLibraryRepository(
    DATA_DIR / "care_gap_value_library.csv", DATA_DIR / "care_gap_audit.jsonl"
)
decisions = ParameterDecisionRepository(
    DATA_DIR / "parameter_decisions.csv", DATA_DIR / "parameter_decision_audit.jsonl"
)

records = library.list_records()
approved_records = [row for row in records if row.get("review_status") == "Approved"]
confirmed_decisions = decisions.list_decisions()
roi_output = st.session_state.get("roi_results_snapshot")
if roi_output is None:
    roi_output = vars(calculate_breast_roi(BreastROIInputs()))

report_path = DATA_DIR / "executive_reports.json"
approved_reports = []
if report_path.exists():
    try:
        approved_reports = json.loads(report_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        approved_reports = []

st.markdown(
    t("Evidence-grounded decision support for breast screening strategy, combining human-reviewed PubMed evidence with a deterministic ROI simulation.")
)

with st.container(horizontal=True):
    st.badge(t("Human-in-the-loop"), color="blue", icon=":material/verified_user:")
    st.badge(t("PMID traceable"), color="green", icon=":material/link:")
    st.badge(t("Deterministic ROI"), color="gray", icon=":material/calculate:")

st.subheader(t("Decision snapshot"))
snapshot = st.columns(4)
snapshot[0].metric(t("Approved evidence"), len(approved_records), border=True)
snapshot[1].metric(t("Confirmed parameters"), len(confirmed_decisions), border=True)
snapshot[2].metric(t("Modeled net savings"), f"${float(roi_output['net_savings']):,.0f}", border=True)
roi = roi_output.get("roi")
snapshot[3].metric(t("Modeled ROI"), "N/A" if roi is None else f"{float(roi):.1%}", border=True)

st.subheader(t("Evidence-to-decision workflow"))
steps = [
    ("1", "Find evidence", "Search real PubMed records and retain source metadata.", "Search", "app_pages/evidence_search.py", len(st.session_state.get("evidence_articles", [])) > 0),
    ("2", "Review evidence", "Validate AI extraction before adding evidence to the library.", "Review", "app_pages/evidence_extraction.py", len(approved_records) > 0),
    ("3", "Confirm parameters", "Keep humans in control of every value entering the model.", "Decide", "app_pages/parameter_copilot.py", len(confirmed_decisions) > 0),
    ("4", "Simulate value", "Run the migrated R formulas for clinical and financial outcomes.", "Simulate", "app_pages/roi_simulation.py", "roi_results_snapshot" in st.session_state),
    ("5", "Approve report", "Generate a grounded draft, validate it, then approve and export.", "Report", "app_pages/executive_report.py", len(approved_reports) > 0),
]
for row in (steps[:3], steps[3:]):
    columns = st.columns(len(row))
    for column, (number, title, description, action, target, complete) in zip(columns, row):
        with column.container(border=True, height="stretch"):
            with st.container(horizontal=True, vertical_alignment="center"):
                st.badge(f"{t('Step')} {number}" if t("Step") != "Step" else f"Step {number}", color="green" if complete else "gray")
                st.badge(t("Complete") if complete else t("Ready"), color="green" if complete else "blue")
            st.subheader(t(title))
            st.caption(t(description))
            st.page_link(target, label=t(action), icon=":material/arrow_forward:")

st.subheader(t("Current scenario"))
with st.container(border=True):
    scenario = pd.DataFrame(
        [
            {t("Outcome"): t("Additional screened"), t("Value"): f"{float(roi_output['additional_screened']):,.0f}"},
            {t("Outcome"): t("Detected cases"), t("Value"): f"{float(roi_output['detected_breast_cancer_cases']):,.1f}"},
            {t("Outcome"): t("Lives saved"), t("Value"): f"{float(roi_output['lives_saved']):,.1f}"},
            {t("Outcome"): t("Program cost"), t("Value"): f"${float(roi_output['screening_program_cost']):,.0f}"},
        ]
    )
    st.dataframe(scenario, hide_index=True, width="stretch")
    st.caption(t("Modeled outputs are scenario estimates, not guaranteed clinical or financial outcomes."))
