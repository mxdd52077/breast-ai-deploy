"""Evidence-gated, human-confirmed ROI parameter decisions."""

import json
from pathlib import Path

import pandas as pd
import streamlit as st

from src.copilot import (
    DecisionAction,
    ParameterDecisionRepository,
    build_parameter_recommendations,
)
from src.library import CareGapLibraryRepository
from src.i18n import t

DATA_DIR = Path(__file__).parents[1] / "data"
library = CareGapLibraryRepository(
    DATA_DIR / "care_gap_value_library.csv",
    DATA_DIR / "care_gap_audit.jsonl",
)
decisions = ParameterDecisionRepository(
    DATA_DIR / "parameter_decisions.csv",
    DATA_DIR / "parameter_decision_audit.jsonl",
)
recommendations = build_parameter_recommendations(library.list_records())
latest = decisions.latest_by_parameter()

st.caption(t("Review evidence-gated suggestions before they reach the deterministic ROI model. The Copilot never changes a parameter without an explicit decision."))

summary = []
for rec in recommendations:
    saved = latest.get(rec.parameter_name, {})
    summary.append(
        {
            "Parameter": rec.display_name,
            "Original": rec.original_value,
            "Recommendation": rec.recommended_value if rec.recommended_value is not None else "—",
            "Evidence gate": rec.evidence_sufficiency.value,
            "PMIDs": ", ".join(rec.pmids) or "—",
            "Final confirmed": saved.get("final_value", "Not confirmed"),
            "Decision": saved.get("action", "Pending"),
        }
    )
st.dataframe(pd.DataFrame(summary).astype(str), hide_index=True, width="stretch")

st.subheader(t("Parameter review"))
for rec in recommendations:
    saved = latest.get(rec.parameter_name)
    status_icon = ":material/check_circle:" if rec.can_accept else ":material/info:"
    with st.expander(f"{rec.display_name} — {rec.evidence_sufficiency.value}", icon=status_icon):
        with st.container(horizontal=True):
            st.metric(t("Original"), f"{rec.original_value:g} {rec.unit}", border=True)
            st.metric(
                t("AI recommendation"),
                f"{rec.recommended_value:g} {rec.unit}" if rec.recommended_value is not None else "No numeric recommendation",
                border=True,
            )
            st.metric(t("Approved sources"), len(rec.pmids), border=True)
        st.write(rec.rationale)
        if rec.pmids:
            st.markdown(
                "Evidence: "
                + " · ".join(
                    f"[PMID {pmid}](https://pubmed.ncbi.nlm.nih.gov/{pmid}/)"
                    for pmid in rec.pmids
                )
            )
        if saved:
            st.success(
                f"Latest decision: {saved['action']} → {saved['final_value']} {rec.unit}. Note: {saved['decision_note']}",
                icon=":material/history:",
            )

        options = [DecisionAction.KEEP.value, DecisionAction.EDIT.value, DecisionAction.RESET.value]
        if rec.can_accept:
            options.insert(1, DecisionAction.ACCEPT.value)
        with st.form(f"decision_{rec.parameter_name}", border=True):
            action_value = st.selectbox(t("Decision"), options, key=f"action_{rec.parameter_name}")
            action = DecisionAction(action_value)
            default_final = (
                rec.recommended_value
                if action == DecisionAction.ACCEPT and rec.recommended_value is not None
                else rec.original_value
            )
            final_value = st.number_input(
                t("Final confirmed value"),
                min_value=0.0,
                max_value=100.0 if rec.unit == "%" else None,
                value=float(default_final),
                disabled=action != DecisionAction.EDIT,
                key=f"final_{rec.parameter_name}_{action.value}",
            )
            note = st.text_area(
                t("Decision note"),
                placeholder="Explain why you kept, accepted, edited, or reset this parameter.",
                key=f"note_{rec.parameter_name}",
            )
            submit = st.form_submit_button(t("Confirm decision"), type="primary", icon=":material/save:")
        if submit:
            try:
                decision = decisions.save_decision(rec, action, float(final_value), note)
                # Update current-session ROI widget immediately; the persisted file
                # also reapplies the decision after an app restart.
                st.session_state[f"roi_{rec.parameter_name}"] = decision.final_value
                st.toast(f"Confirmed {rec.display_name}: {decision.final_value:g} {rec.unit}")
                st.rerun()
            except ValueError as exc:
                st.error(str(exc), icon=":material/error:")

st.warning(
    "Evidence approval and parameter acceptance are separate controls. Cost parameters remain workbook assumptions unless an appropriate external source is reviewed.",
    icon=":material/policy:",
)
