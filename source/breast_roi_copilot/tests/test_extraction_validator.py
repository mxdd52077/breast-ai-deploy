import pytest

from src.evidence.schemas import PubMedArticle
from src.evidence_extraction import ExtractedEvidence, ExtractionValidationError, validate_extraction


@pytest.fixture
def article():
    return PubMedArticle(
        pmid="12345678",
        title="Screening mortality study",
        authors=("Ada Author",),
        publication_year="2024",
        journal="Journal",
        abstract="The relative risk was 0.74 (95% CI 0.66-0.83) after screening.",
    )


def candidate(**overrides):
    data = {
        "pmid": "12345678", "title": "Screening mortality study",
        "study_design": "Meta-analysis", "population": "Women aged 50-74",
        "intervention": "Screening", "comparator": "No screening",
        "outcome": "Mortality", "effect_measure": "Relative risk",
        "effect_value": 0.74, "confidence_interval_low": 0.66,
        "confidence_interval_high": 0.83, "unit": "Relative risk",
        "evidence_excerpt": "The relative risk was 0.74 (95% CI 0.66-0.83) after screening.",
        "candidate_roi_parameter": "lives_saved_per_1000", "directly_usable": False,
        "conversion_required": True, "evidence_strength": "Moderate",
        "limitations": ["Baseline mortality is required."],
    }
    data.update(overrides)
    return ExtractedEvidence(**data)


def test_valid_extraction_passes(article):
    assert validate_extraction(candidate(), article).effect_value == 0.74


def test_excerpt_must_exist(article):
    with pytest.raises(ExtractionValidationError, match="not found"):
        validate_extraction(candidate(evidence_excerpt="Not in the abstract."), article)


def test_number_must_appear_in_excerpt(article):
    with pytest.raises(ExtractionValidationError, match="effect value"):
        validate_extraction(candidate(effect_value=0.75), article)


def test_relative_effect_cannot_directly_map_to_absolute_parameter(article):
    with pytest.raises(ExtractionValidationError, match="relative effect"):
        validate_extraction(candidate(directly_usable=True), article)
