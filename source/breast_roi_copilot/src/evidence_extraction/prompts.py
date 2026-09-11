"""Closed-context prompt for structured effect-size extraction."""

from src.evidence.schemas import PubMedArticle


SYSTEM_PROMPT = """You extract structured medical evidence from one supplied PubMed abstract.
Use only the supplied metadata and abstract. Do not use outside knowledge.
The evidence_excerpt must be an exact, verbatim substring of the abstract.
Extract numerical effect values only when explicitly present in that excerpt.
Use null for missing values; never infer or calculate an unreported number.
Mark directly_usable false unless the reported value has the same population,
definition, unit, and time horizon as the candidate ROI parameter.
Relative risks, odds ratios, and hazard ratios are not directly usable as absolute
lives-saved-per-1,000 or stage-shift percentages without conversion inputs.
Set review_status to 'AI candidate'. The candidate must undergo human review."""


def build_extraction_prompt(article: PubMedArticle) -> str:
    return "\n".join(
        [
            f"PMID: {article.pmid}",
            f"Title: {article.title}",
            f"Authors: {', '.join(article.authors)}",
            f"Year: {article.publication_year}",
            f"Journal: {article.journal}",
            f"Abstract: {article.abstract}",
            "",
            "Extract one structured evidence candidate. If the abstract contains multiple "
            "effects, choose the effect most relevant to breast screening ROI and describe "
            "the selection in limitations.",
        ]
    )
