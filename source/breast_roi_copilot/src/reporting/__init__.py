"""Evidence-grounded executive report generation and governance."""

from .demo_provider import build_demo_report
from .decision_analysis import (
    build_management_recommendations,
    build_planning_scenarios,
    build_sensitivity_analysis,
)
from .generator import ReportGenerationError, generate_report_with_openai
from .prompts import SYSTEM_PROMPT, build_report_prompt
from .repository import ExecutiveReportRepository
from .schemas import ExecutiveReport, EvidenceClaim, ReportAudience, ReportStatus
from .validator import ReportValidationError, validate_executive_report

__all__ = [
    "EvidenceClaim",
    "ExecutiveReport",
    "ExecutiveReportRepository",
    "ReportAudience",
    "ReportGenerationError",
    "ReportStatus",
    "ReportValidationError",
    "SYSTEM_PROMPT",
    "build_demo_report",
    "build_management_recommendations",
    "build_planning_scenarios",
    "build_report_prompt",
    "build_sensitivity_analysis",
    "generate_report_with_openai",
    "validate_executive_report",
]
