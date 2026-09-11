"""Fixed candidate extractions for no-key demonstration."""

import json
from pathlib import Path

from .schemas import ExtractedEvidence


def load_demo_extractions(path: Path) -> dict[str, ExtractedEvidence]:
    with path.open(encoding="utf-8") as stream:
        return {
            item["pmid"]: ExtractedEvidence.model_validate(item)
            for item in json.load(stream)
        }
