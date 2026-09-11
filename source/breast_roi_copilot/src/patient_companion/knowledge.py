"""Load the small, reviewed patient education corpus bundled with the demo."""

import json
from pathlib import Path

from .schemas import KnowledgeChunk


DEFAULT_KNOWLEDGE_PATH = Path(__file__).resolve().parents[2] / "data" / "patient_knowledge.json"


def load_knowledge(path: Path = DEFAULT_KNOWLEDGE_PATH) -> list[KnowledgeChunk]:
    return [KnowledgeChunk.model_validate(item) for item in json.loads(path.read_text("utf-8"))]
