"""Deterministic checks for report numbers, citations, and excerpts."""

import re

from .schemas import ExecutiveReport


class ReportValidationError(ValueError):
    """Raised when a report is not faithful to its supplied inputs."""


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().casefold()


def _validate_narrative_numbers(
    report: ExecutiveReport,
    roi_output: dict,
    roi_inputs: dict | None = None,
) -> None:
    """Reject numeric claims absent from confirmed inputs and deterministic outputs."""
    traceable_values = list(roi_output.values()) + list((roi_inputs or {}).values())
    numeric_outputs = [
        float(value)
        for value in traceable_values
        if isinstance(value, (int, float)) and not isinstance(value, bool) and value is not None
    ]
    # ROI is stored as a ratio but normally narrated as a percentage.
    if isinstance(roi_output.get("roi"), (int, float)):
        numeric_outputs.append(float(roi_output["roi"]) * 100)

    narrative = " ".join(
        [report.executive_summary, report.clinical_impact, report.financial_impact,
         report.evidence_interpretation, *report.key_assumptions,
         *report.limitations, *report.recommended_actions]
    )
    # Citation IDs are validated separately; do not treat a labeled PMID as a financial amount.
    narrative = re.sub(r'PMIDs?\s*[:：]?\s*(\d+)', lambda m: 'PMID' if m[1] in report.cited_pmids else m[0], narrative, flags=re.I)
    # Ignore digits embedded in established alphanumeric terms such as "3D".
    for token in re.findall(
        r"(?<![A-Za-z])\$?(-?\d[\d,]*(?:\.\d+)?)\s*%?(?![A-Za-z])",
        narrative,
    ):
        value = float(token.replace(",", ""))
        # Displayed model values may be rounded to an integer or one decimal place.
        if not any(abs(value - allowed) <= max(0.051, abs(allowed) * 0.00005) for allowed in numeric_outputs):
            raise ReportValidationError(
                f"Narrative numeric value {token} is not traceable to the ROI output."
            )


def validate_executive_report(
    report: ExecutiveReport,
    roi_output: dict,
    approved_evidence: list[dict[str, str]],
    roi_inputs: dict | None = None,
) -> ExecutiveReport:
    """Reject changed ROI snapshots, invented PMIDs, and unsupported excerpts."""
    if report.simulation_snapshot.model_dump(mode="python") != roi_output:
        raise ReportValidationError(
            "The report's simulation snapshot does not exactly match the ROI engine output."
        )

    evidence_by_pmid = {
        str(row.get("pmid", "")): row
        for row in approved_evidence
        if row.get("review_status") == "Approved" and str(row.get("pmid", ""))
    }
    allowed_pmids = set(evidence_by_pmid)
    cited_pmids = set(report.cited_pmids)
    if not cited_pmids.issubset(allowed_pmids):
        invalid = cited_pmids - allowed_pmids
        raise ReportValidationError(
            f"Report cites PMID(s) outside the approved library: {', '.join(sorted(invalid))}."
        )

    claim_pmids: set[str] = set()
    for index, claim in enumerate(report.evidence_claims, start=1):
        current = set(claim.pmids)
        if not current or not current.issubset(allowed_pmids):
            raise ReportValidationError(f"Evidence claim {index} contains an unapproved PMID.")
        if not all(pmid.isdigit() for pmid in current):
            raise ReportValidationError(f"Evidence claim {index} contains an invalid PMID.")
        excerpt = _normalize(claim.evidence_excerpt)
        if not any(
            excerpt in _normalize(str(evidence_by_pmid[pmid].get("evidence_excerpt", "")))
            for pmid in current
        ):
            raise ReportValidationError(
                f"Evidence claim {index}'s excerpt was not found in the approved record."
            )
        excerpt_numbers={float(x.replace(',','')) for x in re.findall(r'-?\d[\d,]*(?:\.\d+)?',claim.evidence_excerpt)}
        claim_text=re.sub(r'PMIDs?\s*[:：]?\s*\d+','',claim.claim,flags=re.I)
        for token in re.findall(r'(?<![A-Za-z\d])-?\d[\d,]*(?:\.\d+)?(?![A-Za-z\d])',claim_text):
            if float(token.replace(',','')) not in excerpt_numbers:
                raise ReportValidationError(f'Evidence claim {index} has an unsupported numeric value.')
        claim_pmids.update(current)
    if claim_pmids != cited_pmids:
        raise ReportValidationError(
            "The cited PMID list must exactly match the report's evidence claims."
        )
    _validate_narrative_numbers(report, roi_output, roi_inputs)
    return report
