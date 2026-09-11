"""Persist parameter decisions and append an immutable decision audit trail."""

import csv
import json
from datetime import datetime, timezone
from pathlib import Path

from .schemas import DecisionAction, ParameterDecision, ParameterRecommendation

FIELDS = [
    "parameter_name", "original_value", "recommended_value", "final_value",
    "unit", "action", "pmids", "decision_note", "updated_at",
]


class ParameterDecisionRepository:
    def __init__(self, csv_path: Path, audit_path: Path):
        self.csv_path = csv_path
        self.audit_path = audit_path
        self.csv_path.parent.mkdir(parents=True, exist_ok=True)

    def list_decisions(self) -> list[dict[str, str]]:
        if not self.csv_path.exists():
            return []
        with self.csv_path.open(newline="", encoding="utf-8") as stream:
            return list(csv.DictReader(stream))

    def latest_by_parameter(self) -> dict[str, dict[str, str]]:
        return {row["parameter_name"]: row for row in self.list_decisions()}

    def save_decision(
        self,
        recommendation: ParameterRecommendation,
        action: DecisionAction,
        final_value: float,
        decision_note: str,
    ) -> ParameterDecision:
        if not decision_note.strip():
            raise ValueError("A decision note is required for the audit trail.")
        if action == DecisionAction.ACCEPT:
            if not recommendation.can_accept or recommendation.recommended_value is None:
                raise ValueError("This evidence is not sufficient to accept a recommendation.")
            if final_value != recommendation.recommended_value:
                raise ValueError("Accepted value must equal the validated recommendation.")
        if action in {DecisionAction.KEEP, DecisionAction.RESET} and final_value != recommendation.original_value:
            raise ValueError("Keep/reset must use the original model value.")
        if final_value < 0:
            raise ValueError("Final parameter value cannot be negative.")
        if recommendation.unit == "%" and not 0 <= final_value <= 100:
            raise ValueError("Percentage parameters must be between 0 and 100.")

        decision = ParameterDecision(
            parameter_name=recommendation.parameter_name,
            original_value=recommendation.original_value,
            recommended_value=recommendation.recommended_value,
            final_value=final_value,
            unit=recommendation.unit,
            action=action,
            pmids=recommendation.pmids,
            decision_note=decision_note.strip(),
            updated_at=datetime.now(timezone.utc).isoformat(),
        )
        row = decision.model_dump(mode="json")
        row["pmids"] = json.dumps(decision.pmids)
        rows = [
            current for current in self.list_decisions()
            if current["parameter_name"] != decision.parameter_name
        ] + [row]
        with self.csv_path.open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=FIELDS)
            writer.writeheader()
            writer.writerows(rows)

        with self.audit_path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(decision.model_dump(mode="json"), ensure_ascii=False) + "\n")
        return decision
