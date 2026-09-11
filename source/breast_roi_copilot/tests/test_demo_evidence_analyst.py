import json
from pathlib import Path

from src.evidence.schemas import PubMedArticle
from src.rag.citation_validator import validate_grounded_answer
from src.rag.demo_provider import load_demo_answers


DATA_DIR = Path(__file__).parents[1] / "data"


def test_every_demo_answer_is_grounded_in_demo_articles():
    with (DATA_DIR / "sample_pubmed_articles.json").open(encoding="utf-8") as stream:
        articles = [PubMedArticle.from_dict(item) for item in json.load(stream)]
    answers = load_demo_answers(DATA_DIR / "sample_grounded_answers.json")
    assert len(answers) == 3
    for answer in answers.values():
        validate_grounded_answer(answer, articles)
