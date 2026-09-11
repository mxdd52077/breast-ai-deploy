"""Local safety gates for model-extracted patient data."""

import re
import unicodedata

from .schemas import CareEvent, ClinicalFact, SourceDocument


class ProvenanceError(ValueError):
    """Extracted content cannot be proven from the uploaded documents."""


def _normalize_layout_whitespace(value: str) -> str:
    """Ignore PDF layout whitespace without changing clinical wording."""
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", value))


def validate_case_provenance(
    documents: list[SourceDocument],
    facts: list[ClinicalFact],
    events: list[CareEvent],
) -> None:
    pages = {
        (document.id, page.page_number): page.text
        for document in documents
        for page in document.pages
    }
    for fact in facts:
        source = pages.get((fact.source_document_id, fact.source_page))
        if source is None:
            raise ProvenanceError(f"事实 {fact.id} 引用了不存在的文档或页码。")
        normalized_quote = _normalize_layout_whitespace(fact.original_text)
        normalized_source = _normalize_layout_whitespace(source)
        if not normalized_quote or normalized_quote not in normalized_source:
            raise ProvenanceError(f"事实 {fact.id} 无法在原文中定位。")
    fact_ids = {fact.id for fact in facts}
    for event in events:
        if not set(event.source_fact_ids).issubset(fact_ids):
            raise ProvenanceError(f"事件 {event.id} 引用了不存在的事实。")
