"""Citation-grounded PubMed evidence analysis with demo and live modes."""

import json
import os
from pathlib import Path

import streamlit as st

from src.evidence import PubMedArticle
from src.i18n import t
from src.rag.answer_generator import EvidenceGenerationError, generate_with_openai
from src.rag.citation_validator import CitationValidationError, validate_grounded_answer
from src.rag.demo_provider import load_demo_answers
from src.rag.schemas import EvidenceStatus, GroundedAnswer

DATA_DIR = Path(__file__).parents[1] / "data"


@st.cache_data
def load_demo_articles() -> list[PubMedArticle]:
    with (DATA_DIR / "sample_pubmed_articles.json").open(encoding="utf-8") as stream:
        return [PubMedArticle.from_dict(item) for item in json.load(stream)]


@st.cache_data
def demo_answers() -> dict[str, GroundedAnswer]:
    return load_demo_answers(DATA_DIR / "sample_grounded_answers.json")


def get_secret(name: str, default: str = "") -> str:
    value = os.getenv(name)
    if value:
        return value
    try:
        return str(st.secrets.get(name, default))
    except (FileNotFoundError, KeyError):
        return default


def render_answer(answer: GroundedAnswer) -> None:
    colors = {
        EvidenceStatus.SUPPORTED: "green",
        EvidenceStatus.PARTIALLY_SUPPORTED: "orange",
        EvidenceStatus.INSUFFICIENT: "gray",
        EvidenceStatus.CONFLICTING: "red",
    }
    st.badge(answer.evidence_status.value, color=colors[answer.evidence_status])
    st.markdown(answer.answer)

    if answer.supporting_claims:
        st.subheader(t("Supporting claims"))
        for index, claim in enumerate(answer.supporting_claims, start=1):
            with st.container(border=True):
                st.markdown(f"**{index}. {claim.claim}**")
                links = " · ".join(
                    f"[PMID {pmid}](https://pubmed.ncbi.nlm.nih.gov/{pmid}/)"
                    for pmid in claim.pmids
                )
                st.markdown(links)
                st.caption(f'{t("Verified excerpt")}: “{claim.evidence_excerpt}”')

    st.subheader(t("Evidence limitations"))
    for limitation in answer.evidence_limitations:
        st.markdown(f"- {limitation}")


st.caption(t("Ask questions about retrieved PubMed abstracts. Every displayed live answer must pass local PMID and excerpt validation."))

mode = st.segmented_control(
    t("Analysis mode"),
    options=[t("Verified demo"), t("Live AI")],
    default=t("Verified demo"),
    help="Demo mode requires no API key. Live AI uses your locally configured OpenAI key.",
)

if mode == t("Verified demo"):
    evidence = load_demo_articles()
    answers = demo_answers()
    st.info(
        "Demo mode uses three fixed real PubMed records and prevalidated answers. No API call is made.",
        icon=":material/science:",
    )
    question = st.selectbox(t("Evidence question"), options=list(answers))
    analyze = st.button(t("Analyze evidence"), type="primary", icon=":material/fact_check:")
    if analyze:
        try:
            st.session_state.analyst_answer = validate_grounded_answer(answers[question], evidence)
            st.session_state.analyst_mode = "demo"
        except CitationValidationError as exc:
            st.error(f"Demo validation failed: {exc}", icon=":material/error:")
else:
    evidence = st.session_state.get("evidence_articles", [])
    source = st.session_state.get("evidence_source")
    api_key = get_secret("OPENAI_API_KEY")
    model = get_secret("OPENAI_MODEL", "gpt-5.6-luna")

    if source != "live" or not evidence:
        st.warning(
            "Run a live search on the Evidence search page first. Offline demo articles are not used for live AI analysis.",
            icon=":material/search:",
        )
    else:
        st.success(f"{t('Using')} {len(evidence)} {t('live PubMed abstracts.')}", icon=":material/check_circle:")

    if not api_key:
        st.warning(
            "Live AI is not configured. Add OPENAI_API_KEY to .streamlit/secrets.toml, then restart the app.",
            icon=":material/key:",
        )
        with st.expander(t("Show safe API key setup")):
            st.code('OPENAI_API_KEY = "your-key-here"\nOPENAI_MODEL = "gpt-5.6-luna"', language="toml")
            st.caption(t("Never commit secrets.toml to GitHub. This project already ignores it in .gitignore."))

    with st.form("live_evidence_question", border=True):
        question = st.text_area(
            t("Question about the retrieved evidence"),
            value="Does mammography screening shift breast cancers toward earlier stages?",
        )
        analyze = st.form_submit_button(
            t("Analyze evidence"),
            type="primary",
            icon=":material/fact_check:",
            disabled=not (api_key and evidence and source == "live"),
        )

    if analyze:
        try:
            with st.spinner("Analyzing retrieved abstracts..."):
                unvalidated = generate_with_openai(question, evidence, api_key, model)
                validated = validate_grounded_answer(unvalidated, evidence)
            st.session_state.analyst_answer = validated
            st.session_state.analyst_mode = "live"
        except (EvidenceGenerationError, CitationValidationError, ValueError) as exc:
            st.session_state.pop("analyst_answer", None)
            st.error(str(exc), icon=":material/shield:")

answer = st.session_state.get("analyst_answer")
answer_mode = st.session_state.get("analyst_mode")
if answer and ((mode == t("Verified demo") and answer_mode == "demo") or (mode == t("Live AI") and answer_mode == "live")):
    st.subheader(t("Validated answer"))
    render_answer(answer)

st.caption(
    "Evidence synthesis only — not medical advice. LLM output never changes the deterministic ROI model."
)
