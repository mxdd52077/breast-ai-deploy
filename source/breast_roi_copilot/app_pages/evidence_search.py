"""Search and display real PubMed evidence without LLM generation."""

import json
from pathlib import Path

import streamlit as st

from src.evidence import PubMedArticle, PubMedClient, PubMedError
from src.i18n import t

SAMPLE_PATH = Path(__file__).parents[1] / "data" / "sample_pubmed_articles.json"


@st.cache_data(ttl="1h", max_entries=50, show_spinner=False)
def search_pubmed(query: str, limit: int = 5) -> list[PubMedArticle]:
    return PubMedClient().search(query, limit)


@st.cache_data
def load_demo_articles() -> list[PubMedArticle]:
    with SAMPLE_PATH.open(encoding="utf-8") as stream:
        return [PubMedArticle.from_dict(item) for item in json.load(stream)]


def render_article(article: PubMedArticle) -> None:
    with st.container(border=True):
        st.subheader(article.title)
        author_text = ", ".join(article.authors) if article.authors else "Authors unavailable"
        st.caption(f"{author_text} · {article.journal} · {article.publication_year} · PMID {article.pmid}")
        st.write(article.abstract)
        st.link_button(
            t("Open in PubMed"),
            article.pubmed_url,
            icon=":material/open_in_new:",
        )


st.caption(t("Search real PubMed records through the official NCBI E-utilities API. No LLM is used."))

with st.form("pubmed_search_form", border=True):
    query = st.text_input(
        t("Medical question or keywords"),
        value="mammography screening stage distribution women 50-74",
        help="PubMed search syntax is supported, including quoted terms and field tags.",
    )
    use_demo = st.checkbox(
        t("Use offline demo articles instead of contacting PubMed"),
        help="Demo articles are fixed real PubMed records and are clearly labeled below.",
    )
    submitted = st.form_submit_button(
        t("Search PubMed"),
        type="primary",
        icon=":material/search:",
    )

if submitted:
    if use_demo:
        st.session_state.evidence_articles = load_demo_articles()
        st.session_state.evidence_source = "demo"
    elif not query.strip():
        st.error("Enter a medical question or keywords before searching.", icon=":material/error:")
    else:
        try:
            with st.spinner("Searching PubMed..."):
                st.session_state.evidence_articles = search_pubmed(query.strip())
            st.session_state.evidence_source = "live"
        except PubMedError as exc:
            st.session_state.evidence_articles = []
            st.session_state.evidence_source = "error"
            st.error(str(exc), icon=":material/cloud_off:")

articles = st.session_state.get("evidence_articles", [])
source = st.session_state.get("evidence_source")

if source == "demo":
    st.warning(
        "Offline demo mode: these are fixed real PubMed records, not results for the current query.",
        icon=":material/science:",
    )
elif source == "live" and not articles:
    st.info(t("PubMed returned no results. Try broader or fewer keywords."), icon=":material/info:")

if articles:
    st.subheader(f"{t('Results')} ({len(articles)})")
    for article in articles:
        render_article(article)

st.caption(
    "Source: NCBI PubMed. Abstracts may be copyrighted. Results are for evidence review and do not constitute medical advice."
)
