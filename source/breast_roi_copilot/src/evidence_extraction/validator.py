"""Deterministic checks for AI-extracted medical evidence."""

import re

from src.evidence.schemas import PubMedArticle

from .schemas import ExtractedEvidence, ReviewStatus


class ExtractionValidationError(ValueError):
    """Raised when an extraction is not grounded in its PubMed record."""


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().casefold()


def _number_appears(value: float, excerpt: str) -> bool:
    candidates = {str(value), f"{value:g}", f"{value:.2f}"}
    return any(candidate in excerpt for candidate in candidates)


def validate_extraction(
    extraction: ExtractedEvidence,
    article: PubMedArticle,
) -> ExtractedEvidence:
    if extraction.pmid != article.pmid:
        raise ExtractionValidationError("The extracted PMID does not match the selected article.")
    if _normalize(extraction.title) != _normalize(article.title):
        raise ExtractionValidationError("The extracted title does not match the selected article.")
    if _normalize(extraction.evidence_excerpt) not in _normalize(article.abstract):
        raise ExtractionValidationError("The evidence excerpt was not found in the PubMed abstract.")

    excerpt = extraction.evidence_excerpt
    for label, value in (
        ("effect value", extraction.effect_value),
        ("confidence interval lower bound", extraction.confidence_interval_low),
        ("confidence interval upper bound", extraction.confidence_interval_high),
    ):
        if value is not None and not _number_appears(value, excerpt):
            raise ExtractionValidationError(f"The {label} does not appear in the evidence excerpt.")

    if (
        extraction.effect_value is not None
        and extraction.confidence_interval_low is not None
        and extraction.confidence_interval_high is not None
        and not (
            extraction.confidence_interval_low
            <= extraction.effect_value
            <= extraction.confidence_interval_high
        )
    ):
        raise ExtractionValidationError("The effect value lies outside its confidence interval.")

    relative_measures = {"relative risk", "risk ratio", "odds ratio", "hazard ratio", "rr", "or", "hr"}
    absolute_parameters = {"lives_saved_per_1000", "regional_to_local_shift", "distant_to_regional_shift"}
    if (
        extraction.directly_usable
        and (extraction.effect_measure or "").casefold() in relative_measures
        and extraction.candidate_roi_parameter in absolute_parameters
    ):
        raise ExtractionValidationError(
            "A relative effect cannot be directly used as an absolute ROI parameter."
        )
    if extraction.review_status not in {ReviewStatus.AI_CANDIDATE, ReviewStatus.NEEDS_REVIEW}:
        raise ExtractionValidationError("AI extraction cannot pre-approve its own evidence.")
    return extraction
