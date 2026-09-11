"""Typed records returned by the PubMed evidence layer."""

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class PubMedArticle:
    pmid: str
    title: str
    authors: tuple[str, ...]
    publication_year: str
    journal: str
    abstract: str

    @property
    def pubmed_url(self) -> str:
        return f"https://pubmed.ncbi.nlm.nih.gov/{self.pmid}/"

    def to_dict(self) -> dict:
        record = asdict(self)
        record["authors"] = list(self.authors)
        return record

    @classmethod
    def from_dict(cls, record: dict) -> "PubMedArticle":
        return cls(
            pmid=str(record["pmid"]),
            title=str(record["title"]),
            authors=tuple(record.get("authors", [])),
            publication_year=str(record.get("publication_year", "Unknown")),
            journal=str(record.get("journal", "Unknown journal")),
            abstract=str(record.get("abstract", "Abstract unavailable.")),
        )
