"""Parse PubMed XML into stable application records."""

import re
from xml.etree import ElementTree as ET

from .schemas import PubMedArticle


def _text(element: ET.Element | None, default: str = "") -> str:
    if element is None:
        return default
    return "".join(element.itertext()).strip() or default


def _publication_year(citation: ET.Element) -> str:
    article_date = citation.find(".//Article/ArticleDate/Year")
    if article_date is not None and _text(article_date):
        return _text(article_date)
    year = citation.find(".//Article/Journal/JournalIssue/PubDate/Year")
    if year is not None and _text(year):
        return _text(year)
    medline_date = _text(citation.find(".//Article/Journal/JournalIssue/PubDate/MedlineDate"))
    match = re.search(r"\b(18|19|20)\d{2}\b", medline_date)
    return match.group(0) if match else "Unknown"


def _authors(citation: ET.Element) -> tuple[str, ...]:
    names = []
    for author in citation.findall(".//Article/AuthorList/Author"):
        collective = _text(author.find("CollectiveName"))
        if collective:
            names.append(collective)
            continue
        given = _text(author.find("ForeName")) or _text(author.find("Initials"))
        family = _text(author.find("LastName"))
        full_name = " ".join(part for part in (given, family) if part)
        if full_name:
            names.append(full_name)
    return tuple(names)


def _abstract(citation: ET.Element) -> str:
    sections = []
    for item in citation.findall(".//Article/Abstract/AbstractText"):
        body = _text(item)
        if not body:
            continue
        label = item.attrib.get("Label", "").strip()
        sections.append(f"{label}: {body}" if label else body)
    return "\n\n".join(sections) if sections else "Abstract unavailable."


def parse_pubmed_xml(xml_data: bytes | str) -> list[PubMedArticle]:
    """Parse an NCBI PubmedArticleSet response, preserving PMID/article alignment."""
    try:
        root = ET.fromstring(xml_data)
    except ET.ParseError as exc:
        raise ValueError("PubMed returned invalid XML.") from exc

    articles = []
    for citation in root.findall(".//PubmedArticle"):
        pmid = _text(citation.find(".//MedlineCitation/PMID"))
        title = _text(citation.find(".//Article/ArticleTitle"), "Untitled article")
        if not pmid:
            continue
        articles.append(
            PubMedArticle(
                pmid=pmid,
                title=title,
                authors=_authors(citation),
                publication_year=_publication_year(citation),
                journal=_text(citation.find(".//Article/Journal/Title"), "Unknown journal"),
                abstract=_abstract(citation),
            )
        )
    return articles
