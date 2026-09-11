"""Load fixed, prevalidated answers for a no-key product demonstration."""

import json
from pathlib import Path

from .schemas import GroundedAnswer


def load_demo_answers(path: Path) -> dict[str, GroundedAnswer]:
    with path.open(encoding="utf-8") as stream:
        records = json.load(stream)
    return {
        record["question"]: GroundedAnswer.model_validate(record["answer"])
        for record in records
    }
