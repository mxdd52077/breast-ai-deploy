"""Deterministic synthetic cases used for the public patient demo."""

from dataclasses import dataclass
from datetime import date, datetime, timezone

from .schemas import (
    CareEvent,
    ClinicalFact,
    ConfirmationStatus,
    EventType,
    PatientCase,
    PatientProfile,
    SourceDocument,
    DocumentPage,
)


@dataclass(frozen=True)
class DemoCaseSummary:
    id: str
    name: str
    stage: str
    description: str


DEMO_CASES = (
    DemoCaseSummary(
        id="endocrine",
        name="林女士 · 术后内分泌治疗",
        stage="术后随访期",
        description="练习核对每日用药和乳腺外科复诊安排",
    ),
    DemoCaseSummary(
        id="chemotherapy",
        name="周女士 · 化疗治疗期",
        stage="化疗期",
        description="练习核对化疗安排、复查血常规和肿瘤科复诊",
    ),
    DemoCaseSummary(
        id="radiotherapy",
        name="陈女士 · 放疗照护期",
        stage="放疗期",
        description="练习核对放疗疗程、皮肤护理医嘱和复诊安排",
    ),
)


def get_demo_case_summaries() -> tuple[DemoCaseSummary, ...]:
    return DEMO_CASES


def _build_case(
    *,
    case_id: str,
    filename: str,
    source_text: str,
    display_name: str,
    treatment_stage: str,
    diagnosis_summary: str,
    fact_specs: list[tuple[str, str, str]],
    event_specs: list[tuple[str, EventType, str, date, str | None, str]],
    current_medications: list[str] | None = None,
) -> PatientCase:
    document = SourceDocument(
        id=f"demo-{case_id}-document",
        filename=filename,
        media_type="text/plain",
        uploaded_at=datetime(2026, 8, 28, tzinfo=timezone.utc),
        pages=[DocumentPage(page_number=1, text=source_text)],
    )
    facts = [
        ClinicalFact(
            id=f"demo-{case_id}-{fact_id}",
            category=category,
            value=value,
            original_text=value,
            source_document_id=document.id,
            source_page=1,
        )
        for fact_id, category, value in fact_specs
    ]
    events = [
        CareEvent(
            id=f"demo-{case_id}-{event_id}",
            event_type=event_type,
            title=title,
            scheduled_date=scheduled_date,
            frequency=frequency,
            source_fact_ids=[f"demo-{case_id}-{source_fact_id}"],
        )
        for event_id, event_type, title, scheduled_date, frequency, source_fact_id in event_specs
    ]
    return PatientCase(
        profile=PatientProfile(
            display_name=display_name,
            treatment_stage=treatment_stage,
            diagnosis_summary=diagnosis_summary,
            current_medications=current_medications or [],
        ),
        documents=[document],
        facts=facts,
        events=events,
    )


def build_demo_case(case_id: str = "endocrine") -> PatientCase:
    if case_id == "endocrine":
        return _build_case(
            case_id=case_id,
            filename="模拟出院小结.txt",
            source_text="模拟病例：乳腺癌术后辅助治疗。来曲唑 2.5 mg，每日一次。2026-09-05 乳腺外科复诊。",
            display_name="林女士（模拟）",
            treatment_stage="术后随访期",
            diagnosis_summary="乳腺癌术后辅助治疗",
            fact_specs=[
                ("diagnosis", "诊断", "乳腺癌术后辅助治疗"),
                ("medication", "用药", "来曲唑 2.5 mg，每日一次"),
                ("followup", "复诊", "2026-09-05 乳腺外科复诊"),
            ],
            event_specs=[
                ("medication-event", EventType.MEDICATION, "按医嘱服用来曲唑 2.5 mg", date(2026, 8, 28), "每日一次", "medication"),
                ("followup-event", EventType.APPOINTMENT, "乳腺外科复诊", date(2026, 9, 5), None, "followup"),
            ],
            current_medications=["来曲唑 2.5 mg，每日一次（待确认）"],
        )
    if case_id == "chemotherapy":
        return _build_case(
            case_id=case_id,
            filename="模拟化疗医嘱.txt",
            source_text="模拟病例：乳腺癌术后化疗期。2026-09-02 第 3 周期化疗。2026-08-31 复查血常规。2026-09-09 肿瘤内科复诊。",
            display_name="周女士（模拟）",
            treatment_stage="化疗期",
            diagnosis_summary="乳腺癌术后化疗期",
            fact_specs=[
                ("diagnosis", "诊断", "乳腺癌术后化疗期"),
                ("treatment", "治疗", "2026-09-02 第 3 周期化疗"),
                ("exam", "检查", "2026-08-31 复查血常规"),
                ("followup", "复诊", "2026-09-09 肿瘤内科复诊"),
            ],
            event_specs=[
                ("exam-event", EventType.EXAM, "复查血常规", date(2026, 8, 31), None, "exam"),
                ("treatment-event", EventType.TREATMENT, "按医嘱进行第 3 周期化疗", date(2026, 9, 2), None, "treatment"),
                ("followup-event", EventType.APPOINTMENT, "肿瘤内科复诊", date(2026, 9, 9), None, "followup"),
            ],
        )
    if case_id == "radiotherapy":
        return _build_case(
            case_id=case_id,
            filename="模拟放疗阶段小结.txt",
            source_text="模拟病例：乳腺癌术后放疗期。2026-09-01 开始放疗，共 15 次。每日观察照射区皮肤并记录变化。2026-09-22 放疗科复诊。",
            display_name="陈女士（模拟）",
            treatment_stage="放疗期",
            diagnosis_summary="乳腺癌术后放疗期",
            fact_specs=[
                ("diagnosis", "诊断", "乳腺癌术后放疗期"),
                ("treatment", "治疗", "2026-09-01 开始放疗，共 15 次"),
                ("self-care", "医嘱", "每日观察照射区皮肤并记录变化"),
                ("followup", "复诊", "2026-09-22 放疗科复诊"),
            ],
            event_specs=[
                ("treatment-event", EventType.TREATMENT, "开始放疗疗程", date(2026, 9, 1), "按医嘱疗程", "treatment"),
                ("self-care-event", EventType.SELF_CARE, "观察照射区皮肤并记录变化", date(2026, 8, 28), "每日", "self-care"),
                ("followup-event", EventType.APPOINTMENT, "放疗科复诊", date(2026, 9, 22), None, "followup"),
            ],
        )
    raise ValueError("未知的模拟档案。")
