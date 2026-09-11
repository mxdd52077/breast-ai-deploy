"""Deterministic, atomic review transitions for extracted patient facts."""

from collections.abc import Mapping

from .schemas import ConfirmationStatus, PatientCase, resolve_confirmation_status


def apply_fact_review(
    case: PatientCase,
    choices: Mapping[str, str | None],
) -> PatientCase:
    """Apply a submitted review without allowing partial or unknown updates."""
    fact_ids = {fact.id for fact in case.facts}
    unknown_ids = set(choices) - fact_ids
    if unknown_ids:
        raise ValueError(f"核对结果包含未知事实：{', '.join(sorted(unknown_ids))}")

    resolved = {
        fact.id: resolve_confirmation_status(
            choices.get(fact.id),
            fact.confirmation_status,
        )
        for fact in case.facts
    }

    reviewed = case.model_copy(deep=True)
    for fact in reviewed.facts:
        fact.confirmation_status = resolved[fact.id]

    for event in reviewed.events:
        statuses = [resolved[fact_id] for fact_id in event.source_fact_ids]
        if statuses and all(status is ConfirmationStatus.CONFIRMED for status in statuses):
            event.confirmation_status = ConfirmationStatus.CONFIRMED
        elif any(status is ConfirmationStatus.REJECTED for status in statuses):
            event.confirmation_status = ConfirmationStatus.REJECTED
        else:
            event.confirmation_status = ConfirmationStatus.NEEDS_CONFIRMATION
    return reviewed
