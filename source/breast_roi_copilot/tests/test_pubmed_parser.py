import json

import pytest

from src.evidence.pubmed_client import PubMedClient, PubMedError
from src.evidence.pubmed_parser import parse_pubmed_xml


SAMPLE_XML = b"""<?xml version="1.0"?>
<PubmedArticleSet>
  <PubmedArticle>
    <MedlineCitation><PMID>12345678</PMID><Article>
      <Journal><JournalIssue><PubDate><MedlineDate>2024 Jan-Feb</MedlineDate></PubDate></JournalIssue><Title>Example Medical Journal</Title></Journal>
      <ArticleTitle>Screening <i>and</i> stage distribution</ArticleTitle>
      <Abstract><AbstractText Label="BACKGROUND">Background text.</AbstractText><AbstractText Label="RESULTS">Results text.</AbstractText></Abstract>
      <AuthorList><Author><ForeName>Ada</ForeName><LastName>Lovelace</LastName></Author><Author><CollectiveName>Trial Group</CollectiveName></Author></AuthorList>
    </Article></MedlineCitation>
  </PubmedArticle>
  <PubmedArticle>
    <MedlineCitation><PMID>87654321</PMID><Article>
      <Journal><JournalIssue><PubDate><Year>2023</Year></PubDate></JournalIssue><Title>Second Journal</Title></Journal>
      <ArticleTitle>Article without an abstract</ArticleTitle>
    </Article></MedlineCitation>
  </PubmedArticle>
</PubmedArticleSet>"""


def test_parser_preserves_article_and_pmid_alignment():
    articles = parse_pubmed_xml(SAMPLE_XML)
    assert [article.pmid for article in articles] == ["12345678", "87654321"]
    assert articles[0].title == "Screening and stage distribution"
    assert articles[0].authors == ("Ada Lovelace", "Trial Group")
    assert articles[0].publication_year == "2024"
    assert articles[0].journal == "Example Medical Journal"
    assert articles[0].abstract == "BACKGROUND: Background text.\n\nRESULTS: Results text."
    assert articles[1].abstract == "Abstract unavailable."


def test_parser_rejects_invalid_xml():
    with pytest.raises(ValueError, match="invalid XML"):
        parse_pubmed_xml(b"not xml")


def test_search_pmids_parses_json(monkeypatch):
    client = PubMedClient()
    monkeypatch.setattr(client, "_get", lambda endpoint, params: json.dumps({"esearchresult": {"idlist": ["1", "2"]}}).encode())
    assert client.search_pmids("mammography", limit=5) == ["1", "2"]


def test_empty_query_is_rejected_without_network():
    with pytest.raises(ValueError, match="cannot be empty"):
        PubMedClient().search_pmids("   ")


def test_malformed_search_response_has_safe_error(monkeypatch):
    client = PubMedClient()
    monkeypatch.setattr(client, "_get", lambda endpoint, params: b"{}")
    with pytest.raises(PubMedError, match="unexpected"):
        client.search_pmids("mammography")
