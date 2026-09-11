"""Small dependency-free client for NCBI PubMed E-utilities."""

import json
import socket
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from .pubmed_parser import parse_pubmed_xml
from .schemas import PubMedArticle


class PubMedError(RuntimeError):
    """A user-safe PubMed search or retrieval failure."""


class PubMedClient:
    BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"

    def __init__(self, timeout: float = 12.0, tool: str = "breast_roi_copilot"):
        self.timeout = timeout
        self.tool = tool

    def _get(self, endpoint: str, params: dict) -> bytes:
        query = urlencode({**params, "tool": self.tool})
        request = Request(
            f"{self.BASE_URL}/{endpoint}?{query}",
            headers={"User-Agent": "BreastROICopilot/0.1 (NCBI E-utilities client)"},
        )
        try:
            with urlopen(request, timeout=self.timeout) as response:
                return response.read()
        except HTTPError as exc:
            raise PubMedError(f"PubMed returned HTTP {exc.code}. Please try again later.") from exc
        except (URLError, TimeoutError, socket.timeout) as exc:
            raise PubMedError("Could not reach PubMed. Check your connection and try again.") from exc

    def search_pmids(self, query: str, limit: int = 5) -> list[str]:
        clean_query = query.strip()
        if not clean_query:
            raise ValueError("Search query cannot be empty.")
        payload = self._get(
            "esearch.fcgi",
            {"db": "pubmed", "term": clean_query, "retmax": max(1, min(limit, 20)), "retmode": "json"},
        )
        try:
            data = json.loads(payload)
            return [str(pmid) for pmid in data["esearchresult"]["idlist"]]
        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            raise PubMedError("PubMed returned an unexpected search response.") from exc

    def fetch_articles(self, pmids: list[str]) -> list[PubMedArticle]:
        if not pmids:
            return []
        payload = self._get(
            "efetch.fcgi",
            {"db": "pubmed", "id": ",".join(pmids), "retmode": "xml"},
        )
        try:
            return parse_pubmed_xml(payload)
        except ValueError as exc:
            raise PubMedError(str(exc)) from exc

    def search(self, query: str, limit: int = 5) -> list[PubMedArticle]:
        return self.fetch_articles(self.search_pmids(query, limit))
