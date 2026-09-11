"""Small, auditable patient-education retrieval layer."""

import re

from .schemas import KnowledgeChunk, PatientAnswer


URGENT_TERMS = {"呼吸困难", "胸痛", "昏厥", "大量出血", "意识不清", "严重过敏"}


def _tokens(text: str) -> set[str]:
    normalized = re.sub(r"[^\w\u4e00-\u9fff]", "", text.lower())
    words = set(re.findall(r"[a-z0-9]+", normalized))
    words.update(normalized[index : index + 2] for index in range(max(0, len(normalized) - 1)))
    return {token for token in words if token}


def retrieve_chunks(
    question: str,
    chunks: list[KnowledgeChunk],
    stage: str | None = None,
    limit: int = 3,
) -> list[KnowledgeChunk]:
    query_tokens = _tokens(question)
    candidates = [
        chunk
        for chunk in chunks
        if not stage or not chunk.treatment_stages or stage in chunk.treatment_stages
    ]
    scored = [
        (len(query_tokens & _tokens(f"{chunk.title}{chunk.topic}{chunk.text}")), chunk)
        for chunk in candidates
    ]
    return [chunk for score, chunk in sorted(scored, key=lambda item: item[0], reverse=True) if score > 0][
        :limit
    ]


def answer_from_demo(question: str, chunks: list[KnowledgeChunk]) -> PatientAnswer:
    if any(term in question for term in URGENT_TERMS):
        return PatientAnswer(
            answer="这些描述可能需要及时医疗评估。请立即联系治疗团队；如果症状严重或快速加重，请联系当地急救服务。",
            status="safety_escalation",
            citations=[],
            safety_notice="这不是诊断或治疗建议。",
        )
    if not chunks:
        return PatientAnswer(
            answer="当前知识库没有足够证据回答这个问题。请记录问题并咨询你的治疗团队。",
            status="insufficient_evidence",
            citations=[],
        )
    summary = " ".join(chunk.text for chunk in chunks)
    return PatientAnswer(
        answer=summary,
        status="supported",
        citations=[chunk.id for chunk in chunks],
        safety_notice="内容用于就医准备和健康教育，不能替代医生诊疗。",
    )
