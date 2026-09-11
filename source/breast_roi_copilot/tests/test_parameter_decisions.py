import json

import pytest

from src.copilot import (
    DecisionAction, EvidenceSufficiency, ParameterDecisionRepository,
    ParameterRecommendation,
)


@pytest.fixture
def recommendation():
    return ParameterRecommendation(
        parameter_name="followup_completion_rate", display_name="Follow-up completion",
        original_value=80, unit="%", recommended_value=82,
        lower_bound=78, upper_bound=86,
        evidence_sufficiency=EvidenceSufficiency.SUFFICIENT,
        rationale="Approved evidence", pmids=["111"], can_accept=True,
    )


def test_accept_decision_is_persisted_and_audited(tmp_path, recommendation):
    repository = ParameterDecisionRepository(tmp_path / "decisions.csv", tmp_path / "audit.jsonl")
    decision = repository.save_decision(
        recommendation, DecisionAction.ACCEPT, 82, "Accepted after evidence review."
    )
    assert decision.final_value == 82
    assert repository.latest_by_parameter()["followup_completion_rate"]["action"] == "Accept recommendation"
    assert json.loads((tmp_path / "audit.jsonl").read_text())["pmids"] == ["111"]


def test_accept_is_blocked_when_evidence_is_insufficient(tmp_path, recommendation):
    repository = ParameterDecisionRepository(tmp_path / "decisions.csv", tmp_path / "audit.jsonl")
    blocked = recommendation.model_copy(update={"can_accept": False, "recommended_value": None})
    with pytest.raises(ValueError, match="not sufficient"):
        repository.save_decision(blocked, DecisionAction.ACCEPT, 82, "Should fail")


def test_manual_edit_validates_percentage_range(tmp_path, recommendation):
    repository = ParameterDecisionRepository(tmp_path / "decisions.csv", tmp_path / "audit.jsonl")
    with pytest.raises(ValueError, match="between 0 and 100"):
        repository.save_decision(recommendation, DecisionAction.EDIT, 120, "Out of range")


def test_note_is_required(tmp_path, recommendation):
    repository = ParameterDecisionRepository(tmp_path / "decisions.csv", tmp_path / "audit.jsonl")
    with pytest.raises(ValueError, match="decision note"):
        repository.save_decision(recommendation, DecisionAction.KEEP, 80, "")
