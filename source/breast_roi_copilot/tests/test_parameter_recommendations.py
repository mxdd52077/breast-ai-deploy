from src.copilot import EvidenceSufficiency, build_parameter_recommendations


def by_name(rows):
    return {item.parameter_name: item for item in rows}


def test_no_evidence_produces_no_recommendation():
    rec = by_name(build_parameter_recommendations([]))["regional_to_local_shift"]
    assert rec.evidence_sufficiency == EvidenceSufficiency.NO_EVIDENCE
    assert rec.recommended_value is None
    assert rec.can_accept is False


def test_relevant_non_numeric_evidence_is_insufficient():
    rows = [{
        "review_status": "Approved", "candidate_roi_parameter": "regional_to_local_shift",
        "pmid": "26835975", "directly_usable": "False", "conversion_required": "False",
        "effect_value": "",
    }]
    rec = by_name(build_parameter_recommendations(rows))["regional_to_local_shift"]
    assert rec.evidence_sufficiency == EvidenceSufficiency.INSUFFICIENT
    assert rec.pmids == ["26835975"]
    assert rec.can_accept is False


def test_relative_effect_needing_conversion_has_no_numeric_recommendation():
    rows = [{
        "review_status": "Approved", "candidate_roi_parameter": "lives_saved_per_1000",
        "pmid": "38878837", "directly_usable": "False", "conversion_required": "True",
        "effect_value": "0.55",
    }]
    rec = by_name(build_parameter_recommendations(rows))["lives_saved_per_1000"]
    assert rec.evidence_sufficiency == EvidenceSufficiency.CONVERSION_REQUIRED
    assert rec.recommended_value is None


def test_single_directly_usable_record_can_be_accepted():
    rows = [{
        "review_status": "Approved", "candidate_roi_parameter": "followup_completion_rate",
        "pmid": "111", "directly_usable": "True", "conversion_required": "False",
        "effect_value": "82", "confidence_interval_low": "78", "confidence_interval_high": "86",
    }]
    rec = by_name(build_parameter_recommendations(rows))["followup_completion_rate"]
    assert rec.evidence_sufficiency == EvidenceSufficiency.SUFFICIENT
    assert rec.recommended_value == 82
    assert rec.can_accept is True
