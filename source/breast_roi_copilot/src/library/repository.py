"""Small auditable CSV repository for reviewed evidence candidates."""

import csv
import json
from datetime import datetime, timezone
from pathlib import Path

from src.evidence_extraction.schemas import ExtractedEvidence, ReviewStatus

FIELDS = [
    "record_id", "pmid", "title", "study_design", "population", "sample_size",
    "intervention", "comparator", "outcome", "effect_measure", "effect_value",
    "confidence_interval_low", "confidence_interval_high", "unit", "time_horizon",
    "evidence_excerpt", "candidate_roi_parameter", "directly_usable",
    "conversion_required", "evidence_strength", "limitations", "review_status",
    "reviewer_note", "created_at", "updated_at",
]


class CareGapLibraryRepository:
    def __init__(self, csv_path: Path, audit_path: Path):
        self.csv_path = csv_path
        self.audit_path = audit_path
        self.csv_path.parent.mkdir(parents=True, exist_ok=True)

    def _read_rows(self) -> list[dict[str, str]]:
        if not self.csv_path.exists():
            return []
        with self.csv_path.open(newline="", encoding="utf-8") as stream:
            return list(csv.DictReader(stream))

    def list_records(self) -> list[dict[str, str]]:
        return self._read_rows()

    def save_review(
        self,
        extraction: ExtractedEvidence,
        status: ReviewStatus,
        reviewer_note: str,
    ) -> str:
        if status not in {ReviewStatus.APPROVED, ReviewStatus.REJECTED}:
            raise ValueError("Human review must be Approved or Rejected.")
        if not reviewer_note.strip():
            raise ValueError("A reviewer note is required for the audit trail.")

        record_id = f"PUBMED-{extraction.pmid}-{extraction.candidate_roi_parameter or 'unmapped'}"
        timestamp = datetime.now(timezone.utc).isoformat()
        rows = self._read_rows()
        existing = next((row for row in rows if row["record_id"] == record_id), None)
        created_at = existing["created_at"] if existing else timestamp
        payload = extraction.model_dump(mode="json")
        row = {field: "" for field in FIELDS}
        row.update({key: value for key, value in payload.items() if key in row})
        row.update(
            {
                "record_id": record_id,
                "limitations": json.dumps(extraction.limitations, ensure_ascii=False),
                "review_status": status.value,
                "reviewer_note": reviewer_note.strip(),
                "created_at": created_at,
                "updated_at": timestamp,
            }
        )
        rows = [current for current in rows if current["record_id"] != record_id] + [row]
        with self.csv_path.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=FIELDS)
            writer.writeheader()
            writer.writerows(rows)

        event = {
            "timestamp": timestamp,
            "record_id": record_id,
            "pmid": extraction.pmid,
            "action": status.value,
            "reviewer_note": reviewer_note.strip(),
        }
        with self.audit_path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(event, ensure_ascii=False) + "\n")
        return record_id
