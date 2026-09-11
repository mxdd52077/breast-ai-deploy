from src.decision_assistant.evidence_search import search_parameter_evidence
from src.evidence import PubMedArticle


def make_article(pmid: str) -> PubMedArticle:
    return PubMedArticle(
        pmid=pmid, title=f"Study {pmid}", authors=(), publication_year="2025",
        journal="Test", abstract="Abstract",
    )


class FakeClient:
    def __init__(self, batches):
        self.batches = iter(batches)
        self.calls = 0

    def search(self, query, limit):
        self.calls += 1
        return next(self.batches)


def test_sparse_precise_search_is_broadened_and_deduplicated():
    client = FakeClient([[make_article("1")], [make_article("1"), make_article("2"), make_article("3")]])
    articles, expanded = search_parameter_evidence(client, "precise", 5)
    assert [article.pmid for article in articles] == ["1", "2", "3"]
    assert expanded is True
    assert client.calls == 2


def test_sufficient_precise_search_does_not_broaden():
    client = FakeClient([[make_article("1"), make_article("2"), make_article("3")]])
    articles, expanded = search_parameter_evidence(client, "precise", 5)
    assert len(articles) == 3
    assert expanded is False
    assert client.calls == 1
