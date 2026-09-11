"""AI candidate extraction with deterministic validation and human review."""

import json
import os
from pathlib import Path

import streamlit as st

from src.evidence import PubMedArticle
from src.i18n import t
from src.evidence_extraction import ExtractionValidationError, ReviewStatus, validate_extraction
from src.evidence_extraction.demo_provider import load_demo_extractions
from src.evidence_extraction.extractor import extract_with_openai
from src.library import CareGapLibraryRepository
from src.rag.answer_generator import EvidenceGenerationError

DATA_DIR = Path(__file__).parents[1] / "data"


@st.cache_data
def demo_articles() -> list[PubMedArticle]:
    with (DATA_DIR / "sample_pubmed_articles.json").open(encoding="utf-8") as stream:
        return [PubMedArticle.from_dict(item) for item in json.load(stream)]


@st.cache_data
def demo_candidates():
    return load_demo_extractions(DATA_DIR / "sample_extractions.json")


def get_secret(name: str, default: str = "") -> str:
    value = os.getenv(name)
    if value:
        return value
    try:
        return str(st.secrets.get(name, default))
    except (FileNotFoundError, KeyError):
        return default


def render_candidate(candidate) -> None:
    st.badge(candidate.review_status.value, color="orange")
    basics = {
        t("Study design"): candidate.study_design,
        t("Population"): candidate.population,
        t("Intervention"): candidate.intervention,
        t("Comparator"): candidate.comparator,
        t("Outcome"): candidate.outcome,
        t("Effect measure"): candidate.effect_measure or t("Not reported"),
        t("Effect value"): candidate.effect_value if candidate.effect_value is not None else t("Not reported"),
        "95% CI": (
            f"{candidate.confidence_interval_low} to {candidate.confidence_interval_high}"
            if candidate.confidence_interval_low is not None and candidate.confidence_interval_high is not None
            else "Not reported"
        ),
        t("Candidate ROI parameter"): candidate.candidate_roi_parameter or t("Not mapped"),
        t("Directly usable"): t("Yes") if candidate.directly_usable else t("No"),
        t("Conversion required"): t("Yes") if candidate.conversion_required else t("No"),
        t("Evidence strength"): candidate.evidence_strength,
    }
    st.dataframe(
        [{"Field": key, "Extracted value": str(value)} for key, value in basics.items()],
        hide_index=True,
        width="stretch",
    )
    st.markdown(f"**{t('Verified excerpt')}**  \n> {candidate.evidence_excerpt}")
    st.markdown(f"**{t('Limitations')}**")
    for limitation in candidate.limitations:
        st.markdown(f"- {limitation}")


st.caption(t("Extract structured effect sizes from one PubMed abstract. AI creates a candidate; deterministic validation and human review control what enters the library."))

mode = st.segmented_control(
    t("Extraction mode"),
    [t("Verified demo"), t("Live AI")],
    default=t("Verified demo"),
)

if mode == t("Verified demo"):
    articles = demo_articles()
    candidates = demo_candidates()
    st.info(t("Demo mode uses fixed real PubMed records and prevalidated candidate extractions."), icon=":material/science:")
else:
    articles = st.session_state.get("evidence_articles", []) if st.session_state.get("evidence_source") == "live" else []
    candidates = {}
    if not articles:
        st.warning(t("Run a live PubMed search first."), icon=":material/search:")

article_options = {f"PMID {article.pmid} — {article.title}": article for article in articles}
selected_label = st.selectbox(t("Select a PubMed article"), options=list(article_options)) if article_options else None
selected_article = article_options.get(selected_label) if selected_label else None

extract = st.button(
    t("Extract structured evidence"),
    type="primary",
    icon=":material/data_object:",
    disabled=selected_article is None,
)

if extract and selected_article:
    try:
        if mode == t("Verified demo"):
            unvalidated = candidates[selected_article.pmid]
        else:
            api_key = get_secret("OPENAI_API_KEY")
            if not api_key:
                raise ValueError("Configure OPENAI_API_KEY before using Live AI extraction.")
            with st.spinner("Extracting evidence candidate..."):
                unvalidated = extract_with_openai(
                    selected_article,
                    api_key,
                    get_secret("OPENAI_MODEL", "gpt-5.6-luna"),
                )
        st.session_state.extraction_candidate = validate_extraction(unvalidated, selected_article)
        st.session_state.extraction_article = selected_article
        st.success(t("Candidate passed PMID, excerpt, and numeric validation."), icon=":material/verified:")
    except (ExtractionValidationError, EvidenceGenerationError, ValueError, KeyError) as exc:
        st.session_state.pop("extraction_candidate", None)
        st.error(str(exc), icon=":material/shield:")

candidate = st.session_state.get("extraction_candidate")
candidate_article = st.session_state.get("extraction_article")
if candidate and candidate_article:
    st.subheader(t("Validated AI candidate"))
    render_candidate(candidate)

    st.subheader(t("Human review"))
    reviewer_note = st.text_area(
        t("Reviewer note"),
        placeholder="Explain why this evidence should be approved or rejected.",
        key="extraction_reviewer_note",
    )
    with st.container(horizontal=True):
        approve = st.button(t("Approve for library"), type="primary", icon=":material/check_circle:")
        reject = st.button(t("Reject candidate"), icon=":material/cancel:")

    if approve or reject:
        try:
            status = ReviewStatus.APPROVED if approve else ReviewStatus.REJECTED
            record_id = CareGapLibraryRepository(
                DATA_DIR / "care_gap_value_library.csv",
                DATA_DIR / "care_gap_audit.jsonl",
            ).save_review(candidate, status, reviewer_note)
            st.toast(f"{status.value}: {record_id}", icon=":material/save:")
            st.session_state.pop("extraction_candidate", None)
            st.rerun()
        except ValueError as exc:
            st.error(str(exc), icon=":material/error:")

st.caption(t("AI candidates never update ROI parameters automatically. Only reviewed records are persisted."))
