"""Create actionable tasks only from confirmed care events."""

from datetime import date

from .schemas import CareEvent, CareTask, ConfirmationStatus


def build_care_tasks(events: list[CareEvent], today: date | None = None) -> list[CareTask]:
    _ = today or date.today()
    return [
        CareTask(
            id=f"task-{event.id}",
            instructions=event.title,
            due_date=event.scheduled_date,
            frequency=event.frequency,
            source_event_id=event.id,
        )
        for event in events
        if event.confirmation_status is ConfirmationStatus.CONFIRMED
    ]
