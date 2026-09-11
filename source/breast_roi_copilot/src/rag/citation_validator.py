"""Deterministic PMID and evidence-excerpt validation."""

import re

from src.evidence.schemas import PubMedArticle

from .schemas import EvidenceStatus, GroundedAnswer


class CitationValidationError(ValueError):
    """Raised when an LLM answer is not grounded in the retrieved evidence."""


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().casefold()


def validate_grounded_answer(
    answer: GroundedAnswer,
    articles: list[PubMedArticle],
) -> GroundedAnswer:
    """Reject invented PMIDs, uncited claims, and excerpts absent from abstracts."""
    article_by_pmid = {article.pmid: article for article in articles}
    allowed_pmids = set(article_by_pmid)

    if set(answer.retrieved_pmids) != allowed_pmids:
        raise CitationValidationError(
            "The answer's retrieved PMID list does not match the current evidence set."
        )

    if answer.evidence_status == EvidenceStatus.INSUFFICIENT:
        if answer.supporting_claims:
            raise CitationValidationError(
                "An insufficient-evidence answer cannot contain supporting claims."
            )
        return answer

    if not answer.supporting_claims:
        raise CitationValidationError("A supported answer must contain supporting claims.")

    for index, claim in enumerate(answer.supporting_claims, start=1):
        cited_pmids = set(claim.pmids)
        invalid_pmids = cited_pmids - allowed_pmids
        if invalid_pmids:
            raise CitationValidationError(
                f"Claim {index} cites PMID(s) outside the current search: "
                f"{', '.join(sorted(invalid_pmids))}."
            )
        if not all(pmid.isdigit() for pmid in cited_pmids):
            raise CitationValidationError(f"Claim {index} contains an invalid PMID format.")

        excerpt = _normalize(claim.evidence_excerpt)
        if not any(excerpt in _normalize(article_by_pmid[pmid].abstract) for pmid in cited_pmids):
            raise CitationValidationError(
                f"Claim {index}'s evidence excerpt was not found in its cited abstract(s)."
            )

    return answer
