import pytest

from src.decision_assistant.evidence_synthesizer import (
    ArticleAssessment,
    EvidenceRelevance,
    EvidenceSynthesis,
    EvidenceSynthesisError,
    ParameterName,
    ParameterRecommendation,
    complete_missing_assessments,
    validate_evidence_synthesis,
)
from src.evidence import PubMedArticle


def article() -> PubMedArticle:
    return PubMedArticle(
        pmid="123",
        title="DBT screening outcomes",
        authors=(), publication_year="2025", journal="Test",
        abstract="The cancer detection rate was 6.4 per 1000 screenings and recall rate was 8.5%.",
    )


def synthesis(excerpt="cancer detection rate was 6.4 per 1000 screenings") -> EvidenceSynthesis:
    return EvidenceSynthesis(
        overall_summary="直接证据有限。",
        assessments=[ArticleAssessment(
            pmid="123", relevance=EvidenceRelevance.DIRECT, population="screening",
            modality="DBT", study_design="cohort", extracted_parameter=ParameterName.DETECTION,
            extracted_value=6.4, evidence_excerpt=excerpt, transferability="可作为候选",
            limitations=["单中心"],
        )],
        recommendations=[ParameterRecommendation(
            parameter=ParameterName.DETECTION, evidence_low=6.4, evidence_high=6.4,
            recommended_value=6.4, action="use candidate", rationale="场景相符",
            supporting_pmids=["123"], limitations=["需人工确认"],
        )],
        conflicts=[],
    )


def test_grounded_synthesis_passes():
    assert validate_evidence_synthesis(synthesis(), [article()]).recommendations[0].recommended_value == 6.4


def test_excerpt_must_exist_in_abstract():
    with pytest.raises(EvidenceSynthesisError):
        validate_evidence_synthesis(synthesis("invented result 6.4"), [article()])


def test_recommended_value_must_come_from_validated_extraction():
    candidate = synthesis()
    candidate.recommendations[0].recommended_value = 7.0
    with pytest.raises(EvidenceSynthesisError):
        validate_evidence_synthesis(candidate, [article()])


def test_missing_article_is_marked_and_excluded_instead_of_hiding_all_output():
    second = PubMedArticle(
        pmid="456", title="Other study", authors=(), publication_year="2024",
        journal="Test", abstract="No transferable parameter was reported.",
    )
    completed = complete_missing_assessments(synthesis(), [article(), second])
    assert {item.pmid for item in completed.assessments} == {"123", "456"}
    missing = next(item for item in completed.assessments if item.pmid == "456")
    assert missing.extracted_value is None
    assert validate_evidence_synthesis(completed, [article(), second]) == completed


def test_unknown_pmid_is_removed_and_numeric_recommendation_is_revoked():
    candidate = synthesis()
    candidate.assessments.append(candidate.assessments[0].model_copy(update={"pmid": "999"}))
    completed = complete_missing_assessments(candidate, [article()])
    assert [item.pmid for item in completed.assessments] == ["123"]
    assert completed.recommendations[0].recommended_value is None
    assert completed.recommendations[0].supporting_pmids == []
    assert validate_evidence_synthesis(completed, [article()]) == completed


def test_duplicate_pmid_is_replaced_with_safe_pending_review_row():
    candidate = synthesis()
    candidate.assessments.append(candidate.assessments[0].model_copy())
    completed = complete_missing_assessments(candidate, [article()])
    assert len(completed.assessments) == 1
    assert completed.assessments[0].pmid == "123"
    assert completed.assessments[0].extracted_value is None
    assert completed.recommendations[0].recommended_value is None
    assert validate_evidence_synthesis(completed, [article()]) == completed
