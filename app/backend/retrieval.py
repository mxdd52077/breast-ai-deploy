"""Account-scoped hybrid retrieval for verified personal facts and public guidance."""
from __future__ import annotations

import hashlib
import math
import re
import unicodedata
from collections import Counter
from typing import Literal

from pydantic import BaseModel
from sqlalchemy import select

from .db import Document, DocumentChunk, Session, engine

EMBEDDING_DIM = 384
EMBEDDING_MODEL = "apex-zh-char-v1"


class EvidenceChunk(BaseModel):
    id: str
    title: str
    publisher: str
    text: str
    source_url: str = ""
    reviewed_at: str = ""
    source_type: Literal["personal", "knowledge"] = "knowledge"
    document_id: str | None = None
    page: int | None = None
    location: str = ""
    review_status: str = "confirmed"


def _normalized(text: str) -> str:
    return re.sub(r"\s+", "", unicodedata.normalize("NFKC", text).lower())


def tokens(text: str) -> set[str]:
    value = _normalized(text)
    output = set(re.findall(r"[a-z0-9_.+-]+", value))
    for width in (2, 3):
        output.update(value[i : i + width] for i in range(max(0, len(value) - width + 1)))
    return {item for item in output if item}


def embedding(text: str) -> list[float]:
    """Stable normalized feature hashing; no patient text leaves the application."""
    counts: Counter[int] = Counter()
    for token in tokens(text):
        digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
        raw = int.from_bytes(digest, "big")
        counts[raw % EMBEDDING_DIM] += -1 if raw & 1 else 1
    vector = [float(counts[i]) for i in range(EMBEDDING_DIM)]
    norm = math.sqrt(sum(value * value for value in vector)) or 1.0
    return [value / norm for value in vector]


def _cosine(left: list[float], right: list[float]) -> float:
    return sum(a * b for a, b in zip(left, right))


def _lexical(query: str, text: str) -> float:
    query_tokens = tokens(query)
    if not query_tokens:
        return 0.0
    return len(query_tokens & tokens(text)) / len(query_tokens)


def sync_fact_chunk(db, fact, document) -> None:
    chunk = db.scalar(select(DocumentChunk).where(DocumentChunk.fact_id == fact.id))
    content = fact.value.strip()
    vector = embedding(f"{document.name} {fact.category} {content}") if content else None
    if chunk is None:
        chunk = DocumentChunk(
            user_id=fact.user_id,
            document_id=fact.document_id,
            fact_id=fact.id,
            page=fact.page,
            location=fact.location,
            content=content,
            content_hash=hashlib.sha256(content.encode("utf-8")).hexdigest(),
        )
        db.add(chunk)
    chunk.page = fact.page
    chunk.location = fact.location
    chunk.content = content
    chunk.content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()
    chunk.review_status = fact.status
    chunk.embedding_model = EMBEDDING_MODEL
    chunk.embedding = vector


def retrieve_personal(query: str, user_id: str, limit: int = 3) -> list[EvidenceChunk]:
    query_vector = embedding(query)
    with Session() as db:
        rows = db.execute(
            select(DocumentChunk, Document)
            .join(Document, Document.id == DocumentChunk.document_id)
            .where(
                DocumentChunk.user_id == user_id,
                DocumentChunk.review_status == "confirmed",
            )
        ).all()
        changed = False
        ranked = []
        for chunk, document in rows:
            if chunk.embedding is None or chunk.embedding_model != EMBEDDING_MODEL:
                chunk.embedding = embedding(f"{document.name} {chunk.content}")
                chunk.embedding_model = EMBEDDING_MODEL
                changed = True
        if changed:
            db.commit()
        if engine.dialect.name == "postgresql" and rows:
            vector_rows = db.execute(
                select(DocumentChunk, Document)
                .join(Document, Document.id == DocumentChunk.document_id)
                .where(
                    DocumentChunk.user_id == user_id,
                    DocumentChunk.review_status == "confirmed",
                    DocumentChunk.embedding.is_not(None),
                )
                .order_by(DocumentChunk.embedding.cosine_distance(query_vector))
                .limit(max(24, limit * 8))
            ).all()
            candidates = {chunk.id: (chunk, document) for chunk, document in vector_rows}
            lexical_rows = sorted(
                rows,
                key=lambda item: _lexical(query, f"{item[1].name} {item[0].content}"),
                reverse=True,
            )[: max(24, limit * 8)]
            candidates.update({chunk.id: (chunk, document) for chunk, document in lexical_rows})
            rows = list(candidates.values())
        for chunk, document in rows:
            vector = list(chunk.embedding)
            semantic = max(0.0, _cosine(query_vector, vector))
            lexical = _lexical(query, f"{document.name} {chunk.content}")
            score = 0.55 * semantic + 0.45 * lexical
            if score > 0:
                ranked.append((score, chunk, document))
        ranked.sort(key=lambda item: item[0], reverse=True)
        return [
            EvidenceChunk(
                id=f"personal:{chunk.id}",
                title=document.name,
                publisher="你的资料",
                text=chunk.content,
                reviewed_at=document.report_date or "",
                source_type="personal",
                document_id=document.id,
                page=chunk.page,
                location=chunk.location,
                review_status=chunk.review_status,
            )
            for _, chunk, document in ranked[:limit]
        ]


def retrieve_evidence(query: str, library: list[EvidenceChunk], user_id: str, limit: int = 5) -> list[EvidenceChunk]:
    personal = retrieve_personal(query, user_id, limit=min(6,limit))
    public_ranked = sorted(
        ((0.55 * max(0.0, _cosine(embedding(query), embedding(f"{item.title} {item.text}"))) + 0.45 * _lexical(query, f"{item.title} {item.text}"), item) for item in library),
        key=lambda item: item[0],
        reverse=True,
    )
    public = [item for score, item in public_ranked if score > 0][:3]
    return (personal + public)[:limit]


def citation_payload(source: EvidenceChunk) -> dict:
    return {
        "id": source.id,
        "title": source.title,
        "publisher": source.publisher,
        "url": source.source_url,
        "text": source.text,
        "reviewed_at": source.reviewed_at,
        "source_type": source.source_type,
        "document_id": source.document_id,
        "page": source.page,
        "location": source.location,
        "review_status": source.review_status,
    }
