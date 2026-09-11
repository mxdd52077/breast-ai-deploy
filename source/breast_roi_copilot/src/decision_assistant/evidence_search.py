"""Two-pass PubMed retrieval for parameter-oriented decision support."""

from src.evidence import PubMedArticle, PubMedClient


STANDARD_PARAMETER_QUERY = (
    '("digital breast tomosynthesis" OR DBT OR mammography) '
    'AND ("breast cancer screening" OR screening) '
    'AND ("cancer detection rate" OR "recall rate")'
)


def search_parameter_evidence(
    client: PubMedClient,
    precise_query: str,
    limit: int = 5,
) -> tuple[list[PubMedArticle], bool]:
    """Run a precise query, then broaden automatically when results are sparse."""
    precise = client.search(precise_query, limit)
    if len(precise) >= min(3, limit):
        return precise[:limit], False

    broad = client.search(STANDARD_PARAMETER_QUERY, limit)
    merged: list[PubMedArticle] = []
    seen: set[str] = set()
    for article in [*precise, *broad]:
        if article.pmid not in seen:
            merged.append(article)
            seen.add(article.pmid)
        if len(merged) == limit:
            break
    return merged, True
