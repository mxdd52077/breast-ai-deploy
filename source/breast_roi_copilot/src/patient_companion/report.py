"""Build a patient-facing report from confirmed, source-backed facts."""

from .schemas import ConfirmationStatus, PatientCareReport, PatientCase


def build_report(case: PatientCase) -> PatientCareReport:
    confirmed = [
        fact for fact in case.facts if fact.confirmation_status is ConfirmationStatus.CONFIRMED
    ]
    pending = [
        fact for fact in case.facts if fact.confirmation_status is ConfirmationStatus.NEEDS_CONFIRMATION
    ]
    confirmed_ids = {fact.id for fact in confirmed}
    arrangements = [
        f"{event.scheduled_date.isoformat()} · {event.title}"
        for event in case.events
        if event.confirmation_status is ConfirmationStatus.CONFIRMED
        and set(event.source_fact_ids).issubset(confirmed_ids)
    ]
    return PatientCareReport(
        overview=case.profile.diagnosis_summary,
        timeline=arrangements,
        key_results=[f"{fact.category}：{fact.value}" for fact in confirmed],
        current_arrangements=arrangements,
        needs_confirmation=[f"{fact.category}：{fact.value}" for fact in pending],
        visit_questions=[
            "这些医嘱的执行时间和频率是否正确？",
            "出现哪些症状时需要提前联系治疗团队？",
        ],
        source_fact_ids=[fact.id for fact in confirmed],
    )
