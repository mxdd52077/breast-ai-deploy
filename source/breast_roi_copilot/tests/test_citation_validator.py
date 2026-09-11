import pytest

from src.evidence.schemas import PubMedArticle
from src.rag import (
    CitationValidationError,
    EvidenceStatus,
    GroundedAnswer,
    SupportingClaim,
    validate_grounded_answer,
)


@pytest.fixture
def articles():
    return [
        PubMedArticle(
            pmid="12345678",
            title="Example",
            authors=("Ada Author",),
            publication_year="2024",
            journal="Journal",
            abstract="Screening was associated with increased localized-stage incidence.",
        )
    ]


def supported_answer(**overrides):
    data = {
        "answer": "The evidence partially supports the claim. [PMID: 12345678]",
        "evidence_status": EvidenceStatus.PARTIALLY_SUPPORTED,
        "supporting_claims": [
            SupportingClaim(
                claim="Localized-stage incidence increased.",
                pmids=["12345678"],
                evidence_excerpt="Screening was associated with increased localized-stage incidence.",
            )
        ],
        "evidence_limitations": ["Observational evidence."],
        "retrieved_pmids": ["12345678"],
    }
    data.update(overrides)
    return GroundedAnswer(**data)


def test_valid_grounded_answer_passes(articles):
    assert validate_grounded_answer(supported_answer(), articles).evidence_status == EvidenceStatus.PARTIALLY_SUPPORTED


def test_invented_pmid_is_rejected(articles):
    answer = supported_answer(
        supporting_claims=[
            SupportingClaim(
                claim="Invented claim",
                pmids=["99999999"],
                evidence_excerpt="Invented excerpt",
            )
        ]
    )
    with pytest.raises(CitationValidationError, match="outside the current search"):
        validate_grounded_answer(answer, articles)


def test_excerpt_absent_from_abstract_is_rejected(articles):
    answer = supported_answer(
        supporting_claims=[
            SupportingClaim(
                claim="Unsupported claim",
                pmids=["12345678"],
                evidence_excerpt="This sentence is not in the abstract.",
            )
        ]
    )
    with pytest.raises(CitationValidationError, match="not found"):
        validate_grounded_answer(answer, articles)


def test_retrieved_pmid_set_must_match(articles):
    with pytest.raises(CitationValidationError, match="does not match"):
        validate_grounded_answer(supported_answer(retrieved_pmids=[]), articles)


def test_insufficient_evidence_has_no_claims(articles):
    answer = GroundedAnswer(
        answer="Insufficient evidence.",
        evidence_status=EvidenceStatus.INSUFFICIENT,
        supporting_claims=[],
        evidence_limitations=["No compatible numeric parameter was reported."],
        retrieved_pmids=["12345678"],
    )
    assert validate_grounded_answer(answer, articles) == answer


def test_insufficient_evidence_with_claim_is_rejected(articles):
    answer = supported_answer(evidence_status=EvidenceStatus.INSUFFICIENT)
    with pytest.raises(CitationValidationError, match="cannot contain"):
        validate_grounded_answer(answer, articles)
