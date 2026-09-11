"""Deterministic evidence gate for AI-extracted, human-approved records."""

from collections import defaultdict

from src.models.schemas import BreastROIInputs

from .schemas import EvidenceSufficiency, ParameterRecommendation

PARAMETERS = {
    "lives_saved_per_1000": ("Lives saved per 1,000", "lives / 1,000"),
    "cancer_detection_per_1000": ("Cancer detection rate", "cases / 1,000"),
    "followup_completion_rate": ("Follow-up completion", "%"),
    "regional_to_local_shift": ("Regional → localized shift", "%"),
    "distant_to_regional_shift": ("Distant → regional shift", "%"),
}


def _truthy(value) -> bool:
    return str(value).strip().casefold() in {"true", "1", "yes"}


def _number(value) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def build_parameter_recommendations(
    library_rows: list[dict],
    defaults: BreastROIInputs | None = None,
) -> list[ParameterRecommendation]:
    defaults = defaults or BreastROIInputs()
    approved = defaultdict(list)
    for row in library_rows:
        if row.get("review_status") == "Approved" and row.get("candidate_roi_parameter") in PARAMETERS:
            approved[row["candidate_roi_parameter"]].append(row)

    recommendations = []
    for name, (display_name, unit) in PARAMETERS.items():
        original = float(getattr(defaults, name))
        evidence = approved[name]
        pmids = sorted({str(row.get("pmid", "")) for row in evidence if row.get("pmid")})
        directly_usable = [
            row for row in evidence
            if _truthy(row.get("directly_usable")) and _number(row.get("effect_value")) is not None
        ]

        if directly_usable:
            # Multiple approved directly-usable records require an explicit synthesis rule.
            # Until then, only a single compatible record can generate an accept-able value.
            if len(directly_usable) == 1:
                row = directly_usable[0]
                value = _number(row.get("effect_value"))
                recommendations.append(
                    ParameterRecommendation(
                        parameter_name=name, display_name=display_name,
                        original_value=original, unit=unit,
                        recommended_value=value,
                        lower_bound=_number(row.get("confidence_interval_low")),
                        upper_bound=_number(row.get("confidence_interval_high")),
                        evidence_sufficiency=EvidenceSufficiency.SUFFICIENT,
                        rationale="One approved record is marked directly usable with a compatible numeric effect. Human acceptance is still required.",
                        pmids=pmids, can_accept=True,
                    )
                )
                continue
            status = EvidenceSufficiency.INSUFFICIENT
            rationale = "Multiple directly usable records require an explicit evidence-synthesis rule before recommending one value."
        elif any(_truthy(row.get("conversion_required")) for row in evidence):
            status = EvidenceSufficiency.CONVERSION_REQUIRED
            rationale = "Approved evidence reports a relative or otherwise incompatible effect. Baseline risk, time horizon, or a documented conversion method is required."
        elif evidence:
            status = EvidenceSufficiency.INSUFFICIENT
            rationale = "Approved evidence is relevant, but it does not report a directly transferable numeric value for this ROI parameter."
        else:
            status = EvidenceSufficiency.NO_EVIDENCE
            rationale = "No approved Care Gap Value Library record maps to this parameter."

        recommendations.append(
            ParameterRecommendation(
                parameter_name=name, display_name=display_name,
                original_value=original, unit=unit,
                evidence_sufficiency=status, rationale=rationale,
                pmids=pmids, can_accept=False,
            )
        )
    return recommendations
