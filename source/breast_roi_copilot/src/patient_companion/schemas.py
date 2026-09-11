"""Strict contracts for the patient companion workflow."""

from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ConfirmationStatus(str, Enum):
    NEEDS_CONFIRMATION = "待确认"
    CONFIRMED = "已确认"
    REJECTED = "已排除"


def resolve_confirmation_status(
    choice: str | None,
    current: ConfirmationStatus,
) -> ConfirmationStatus:
    """Resolve a confirmation widget value without mutating its current status."""
    return current if choice is None else ConfirmationStatus(choice)


class EventType(str, Enum):
    MEDICATION = "用药"
    APPOINTMENT = "复诊"
    EXAM = "检查"
    TREATMENT = "治疗"
    SELF_CARE = "通用照护"


class TaskStatus(str, Enum):
    PENDING = "待完成"
    COMPLETED = "已完成"
    SKIPPED = "已跳过"


class DocumentPage(StrictModel):
    page_number: int = Field(ge=1)
    text: str = Field(min_length=1)


class SourceDocument(StrictModel):
    id: str = Field(min_length=1)
    filename: str = Field(min_length=1)
    media_type: str = Field(min_length=1)
    uploaded_at: datetime
    pages: list[DocumentPage] = Field(min_length=1)


class ClinicalFact(StrictModel):
    id: str = Field(min_length=1)
    category: str = Field(min_length=1)
    value: str = Field(min_length=1)
    original_text: str = Field(min_length=1)
    source_document_id: str = Field(min_length=1)
    source_page: int = Field(ge=1)
    confirmation_status: ConfirmationStatus = ConfirmationStatus.NEEDS_CONFIRMATION
    notes: str | None = None


class PathologyMarker(StrictModel):
    name: str = Field(min_length=1)
    value: str = Field(min_length=1)


class PatientProfile(StrictModel):
    display_name: str = Field(min_length=1)
    treatment_stage: str = Field(min_length=1)
    diagnosis_summary: str = Field(min_length=1)
    pathology_markers: list[PathologyMarker] = Field(default_factory=list)
    current_medications: list[str] = Field(default_factory=list)
    allergies: list[str] = Field(default_factory=list)
    care_team: list[str] = Field(default_factory=list)


class CareEvent(StrictModel):
    id: str = Field(min_length=1)
    event_type: EventType
    title: str = Field(min_length=1)
    scheduled_date: date
    frequency: str | None = None
    source_fact_ids: list[str] = Field(min_length=1)
    confirmation_status: ConfirmationStatus = ConfirmationStatus.NEEDS_CONFIRMATION


class CareTask(StrictModel):
    id: str = Field(min_length=1)
    instructions: str = Field(min_length=1)
    due_date: date
    frequency: str | None = None
    source_event_id: str = Field(min_length=1)
    status: TaskStatus = TaskStatus.PENDING


class SymptomCheckIn(StrictModel):
    symptom: str = Field(min_length=1)
    severity: int = Field(ge=0, le=10)
    occurred_at: datetime
    safety_escalation: bool = False


class PatientCareReport(StrictModel):
    overview: str
    timeline: list[str]
    key_results: list[str]
    current_arrangements: list[str]
    needs_confirmation: list[str]
    visit_questions: list[str]
    source_fact_ids: list[str]


class PatientCase(StrictModel):
    profile: PatientProfile
    documents: list[SourceDocument] = Field(default_factory=list)
    facts: list[ClinicalFact] = Field(default_factory=list)
    events: list[CareEvent] = Field(default_factory=list)
    tasks: list[CareTask] = Field(default_factory=list)


class PatientExtraction(StrictModel):
    """Model-owned output; uploaded documents remain application-owned."""

    profile: PatientProfile
    facts: list[ClinicalFact] = Field(default_factory=list)
    events: list[CareEvent] = Field(default_factory=list)


class KnowledgeChunk(StrictModel):
    id: str = Field(min_length=1)
    title: str
    publisher: str
    source_url: HttpUrl
    topic: str
    treatment_stages: list[str]
    audience: str = "患者"
    jurisdiction: str
    updated_at: date
    reviewed_at: date
    risk_level: str
    text: str = Field(min_length=1)


class PatientAnswer(StrictModel):
    answer: str
    status: str
    citations: list[str]
    safety_notice: str | None = None
