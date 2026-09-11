from dataclasses import asdict

import pytest

from src.models import BreastROIInputs, calculate_breast_roi
from src.reporting.demo_provider import build_demo_report
from src.reporting.prompts import SYSTEM_PROMPT
from src.reporting.schemas import ExecutiveReport, ReportAudience
from src.reporting.validator import ReportValidationError, validate_executive_report


def approved_evidence():
    return [
        {
            "pmid": "12345678",
            "review_status": "Approved",
            "outcome": "Screening was associated with earlier detection.",
            "evidence_excerpt": "Screening was associated with earlier detection.",
        }
    ]


def test_demo_report_passes_number_and_citation_validation():
    result = asdict(calculate_breast_roi(BreastROIInputs()))
    report = build_demo_report(ReportAudience.EXECUTIVE, result, approved_evidence())
    assert validate_executive_report(report, result, approved_evidence()) == report
    assert report.cited_pmids == ["12345678"]


def test_report_rejects_changed_roi_snapshot():
    result = asdict(calculate_breast_roi(BreastROIInputs()))
    report = build_demo_report(ReportAudience.EXECUTIVE, result, approved_evidence())
    report.simulation_snapshot.net_savings += 1
    with pytest.raises(ReportValidationError, match="does not exactly match"):
        validate_executive_report(report, result, approved_evidence())


def test_report_rejects_unapproved_pmid():
    result = asdict(calculate_breast_roi(BreastROIInputs()))
    report = build_demo_report(ReportAudience.EXECUTIVE, result, approved_evidence())
    report.cited_pmids = ["99999999"]
    with pytest.raises(ReportValidationError, match="outside the approved library"):
        validate_executive_report(report, result, approved_evidence())


def test_report_rejects_invented_narrative_number():
    result = asdict(calculate_breast_roi(BreastROIInputs()))
    report = build_demo_report(ReportAudience.EXECUTIVE, result, approved_evidence())
    report.financial_impact = "Modeled net savings are $999,999."
    with pytest.raises(ReportValidationError, match="not traceable"):
        validate_executive_report(report, result, approved_evidence())


def test_report_allows_numbers_embedded_in_modality_terms():
    result = asdict(calculate_breast_roi(BreastROIInputs()))
    report = build_demo_report(ReportAudience.EXECUTIVE, result, approved_evidence())
    report.clinical_impact += " Screening modality: DBT / 3D mammography."
    assert validate_executive_report(report, result, approved_evidence()) == report


def test_report_allows_confirmed_input_numbers_when_inputs_are_supplied():
    inputs = asdict(BreastROIInputs())
    result = asdict(calculate_breast_roi(BreastROIInputs()))
    report = build_demo_report(ReportAudience.EXECUTIVE, result, approved_evidence())
    report.executive_summary += " Confirmed average age: 55."
    assert validate_executive_report(report, result, approved_evidence(), inputs) == report


def test_demo_report_abstains_without_approved_evidence():
    result = asdict(calculate_breast_roi(BreastROIInputs()))
    report = build_demo_report(ReportAudience.PAYER, result, [])
    assert report.evidence_interpretation == "Insufficient evidence."
    assert report.cited_pmids == []
    assert validate_executive_report(report, result, []) == report


def test_chinese_demo_report_remains_faithful_to_roi_output():
    result = asdict(calculate_breast_roi(BreastROIInputs()))
    report = build_demo_report(
        ReportAudience.EXECUTIVE, result, approved_evidence(), "Chinese"
    )
    assert "确定性场景" in report.executive_summary
    assert validate_executive_report(report, result, approved_evidence()) == report


def test_structured_output_schema_has_no_dynamic_object_fields():
    schema = ExecutiveReport.model_json_schema()
    snapshot = schema["$defs"]["SimulationSnapshot"]
    assert snapshot["additionalProperties"] is False
    assert set(snapshot["required"]) == set(snapshot["properties"])


def test_report_prompt_separates_machine_precision_from_narrative_formatting():
    assert "完整机器精度只能出现在 simulation_snapshot" in SYSTEM_PROMPT
    assert "ROI 按百分比保留 1 位小数" in SYSTEM_PROMPT
    assert "排除未知分期" in SYSTEM_PROMPT
