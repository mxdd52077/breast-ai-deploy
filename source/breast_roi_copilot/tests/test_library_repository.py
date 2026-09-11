import json

import pytest

from src.evidence_extraction import ExtractedEvidence, ReviewStatus
from src.library import CareGapLibraryRepository


@pytest.fixture
def extraction():
    return ExtractedEvidence(
        pmid="123", title="Study", study_design="RCT", population="Adults",
        intervention="Screening", comparator="No screening", outcome="Mortality",
        evidence_excerpt="Mortality was lower.", evidence_strength="Moderate",
        candidate_roi_parameter="lives_saved_per_1000", directly_usable=False,
        limitations=["No absolute effect."],
    )


def test_review_is_persisted_and_audited(tmp_path, extraction):
    repository = CareGapLibraryRepository(tmp_path / "library.csv", tmp_path / "audit.jsonl")
    record_id = repository.save_review(extraction, ReviewStatus.APPROVED, "Verified against abstract.")
    rows = repository.list_records()
    assert record_id == "PUBMED-123-lives_saved_per_1000"
    assert rows[0]["review_status"] == "Approved"
    assert rows[0]["reviewer_note"] == "Verified against abstract."
    event = json.loads((tmp_path / "audit.jsonl").read_text())
    assert event["action"] == "Approved"


def test_reviewer_note_is_required(tmp_path, extraction):
    repository = CareGapLibraryRepository(tmp_path / "library.csv", tmp_path / "audit.jsonl")
    with pytest.raises(ValueError, match="reviewer note"):
        repository.save_review(extraction, ReviewStatus.REJECTED, "")


def test_second_review_updates_instead_of_duplicates(tmp_path, extraction):
    repository = CareGapLibraryRepository(tmp_path / "library.csv", tmp_path / "audit.jsonl")
    repository.save_review(extraction, ReviewStatus.APPROVED, "First review")
    repository.save_review(extraction, ReviewStatus.REJECTED, "Re-reviewed")
    rows = repository.list_records()
    assert len(rows) == 1
    assert rows[0]["review_status"] == "Rejected"
