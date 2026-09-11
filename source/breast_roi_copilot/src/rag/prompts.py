"""Prompt construction for a closed-context PubMed evidence analyst."""

from src.evidence.schemas import PubMedArticle


SYSTEM_PROMPT = """You are a cautious medical evidence analyst.
Answer only from the PubMed abstracts supplied in the user message.
Do not use outside medical knowledge, do not invent PMIDs, and do not calculate ROI.
Each supporting claim must cite one or more supplied PMIDs and include one exact,
verbatim excerpt from a cited abstract. Do not paraphrase the evidence_excerpt.
If the abstracts do not directly support an answer, return evidence_status
'Insufficient evidence', provide no supporting claims, and explain the evidence gap.
Distinguish association from causation and state study/population limitations.
Never convert a relative effect into an ROI parameter unless the evidence directly
reports the requested parameter in a compatible population and unit."""


def build_evidence_prompt(question: str, articles: list[PubMedArticle]) -> str:
    records = []
    for article in articles:
        records.append(
            "\n".join(
                [
                    f"PMID: {article.pmid}",
                    f"Title: {article.title}",
                    f"Year: {article.publication_year}",
                    f"Journal: {article.journal}",
                    f"Abstract: {article.abstract}",
                ]
            )
        )
    return (
        f"Question:\n{question.strip()}\n\n"
        "Retrieved PubMed evidence:\n\n"
        + "\n\n---\n\n".join(records)
        + "\n\nReturn a structured grounded answer. The retrieved_pmids field must "
        "contain every PMID supplied above and no others."
    )
