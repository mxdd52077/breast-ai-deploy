"""Persist approved reports and append report lifecycle audit events."""

import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from .schemas import ExecutiveReport, ReportStatus


class ExecutiveReportRepository:
    def __init__(self, reports_path: Path, audit_path: Path):
        self.reports_path = reports_path
        self.audit_path = audit_path
        self.reports_path.parent.mkdir(parents=True, exist_ok=True)

    def list_reports(self) -> list[dict]:
        if not self.reports_path.exists():
            return []
        return json.loads(self.reports_path.read_text(encoding="utf-8"))

    def save_approved(
        self,
        report: ExecutiveReport,
        reviewer_note: str,
        generation_mode: str,
    ) -> dict:
        if not reviewer_note.strip():
            raise ValueError("A reviewer note is required before report approval.")
        timestamp = datetime.now(timezone.utc).isoformat()
        record = {
            "report_id": f"REPORT-{uuid4().hex[:12]}",
            "status": ReportStatus.APPROVED.value,
            "generation_mode": generation_mode,
            "reviewer_note": reviewer_note.strip(),
            "approved_at": timestamp,
            "report": report.model_dump(mode="json"),
        }
        reports = self.list_reports() + [record]
        self.reports_path.write_text(
            json.dumps(reports, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        with self.audit_path.open("a", encoding="utf-8") as stream:
            stream.write(
                json.dumps(
                    {
                        "timestamp": timestamp,
                        "report_id": record["report_id"],
                        "action": "Approved",
                        "generation_mode": generation_mode,
                        "reviewer_note": reviewer_note.strip(),
                        "cited_pmids": report.cited_pmids,
                    },
                    ensure_ascii=False,
                )
                + "\n"
            )
        return record
