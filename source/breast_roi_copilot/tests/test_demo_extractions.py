import json
from pathlib import Path

from src.evidence.schemas import PubMedArticle
from src.evidence_extraction import validate_extraction
from src.evidence_extraction.demo_provider import load_demo_extractions


DATA_DIR = Path(__file__).parents[1] / "data"


def test_all_demo_extractions_are_grounded():
    with (DATA_DIR / "sample_pubmed_articles.json").open(encoding="utf-8") as stream:
        articles = {item["pmid"]: PubMedArticle.from_dict(item) for item in json.load(stream)}
    extractions = load_demo_extractions(DATA_DIR / "sample_extractions.json")
    assert len(extractions) == 3
    for pmid, extraction in extractions.items():
        validate_extraction(extraction, articles[pmid])
