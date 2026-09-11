"""Display the reviewed Care Gap Value Library and governance status."""

import json
from pathlib import Path

import pandas as pd
import streamlit as st

from src.library import CareGapLibraryRepository
from src.i18n import t

DATA_DIR = Path(__file__).parents[1] / "data"
repository = CareGapLibraryRepository(
    DATA_DIR / "care_gap_value_library.csv",
    DATA_DIR / "care_gap_audit.jsonl",
)
records = repository.list_records()

st.caption(t("Human-reviewed evidence records for preventive-care parameters. Approved does not mean automatically applied to the ROI model."))

if not records:
    st.info(
        "The library is empty. Extract evidence and approve or reject a candidate to create the first audited record.",
        icon=":material/library_add:",
    )
else:
    frame = pd.DataFrame(records)
    approved = int((frame["review_status"] == "Approved").sum())
    rejected = int((frame["review_status"] == "Rejected").sum())
    with st.container(horizontal=True):
        st.metric(t("Reviewed records"), len(frame), border=True)
        st.metric(t("Approved"), approved, border=True)
        st.metric(t("Rejected"), rejected, border=True)
        st.metric(t("Directly usable"), int((frame["directly_usable"].astype(str).str.lower() == "true").sum()), border=True)

    display_columns = [
        "pmid_link", "outcome", "effect_measure", "effect_value", "unit",
        "candidate_roi_parameter", "directly_usable", "conversion_required",
        "evidence_strength", "review_status", "reviewer_note", "updated_at",
    ]
    frame["pmid_link"] = frame["pmid"].map(
        lambda pmid: f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
    )
    st.dataframe(
        frame[display_columns],
        hide_index=True,
        width="stretch",
        column_config={
            "pmid_link": st.column_config.LinkColumn(
                "PMID",
                display_text=r"https://pubmed\.ncbi\.nlm\.nih\.gov/(\d+)/",
            ),
        },
    )

    selected_pmid = st.selectbox(t("Inspect record"), frame["pmid"].tolist())
    record = frame.loc[frame["pmid"] == selected_pmid].iloc[-1].to_dict()
    with st.container(border=True):
        st.subheader(record["title"])
        st.markdown(f"**{t('Outcome')}:** {record['outcome']}")
        st.markdown(f"**{t('Verified excerpt')}:**  \n> {record['evidence_excerpt']}")
        limitations = json.loads(record["limitations"]) if record["limitations"] else []
        st.markdown(f"**{t('Limitations')}**")
        for limitation in limitations:
            st.markdown(f"- {limitation}")
        st.markdown(f"**{t('Human review')}:** {record['review_status']} — {record['reviewer_note']}")

st.warning(
    "Governance rule: only Approved records may inform a future Parameter Copilot, and users must still explicitly accept any recommendation.",
    icon=":material/policy:",
)
