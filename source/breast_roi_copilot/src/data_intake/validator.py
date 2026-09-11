"""Validate hospital-like inputs and derive downstream decision fields."""

from dataclasses import dataclass
from hashlib import sha256

import numpy as np
import pandas as pd

from src.models import BreastROIInputs
from src.models.breast_roi import get_age_band

HOSPITAL_REQUIRED_COLUMNS = (
    "patient_id", "as_of_date", "age", "last_screen_date", "never_screened",
    "has_active_appointment", "outreach_consent",
)
HOSPITAL_OPTIONAL_COLUMNS = ("prior_abnormal", "family_history", "preferred_language", "clinic_id")
DERIVED_COLUMNS = (
    "years_since_screen", "ground_truth_gap", "care_gap_score",
    "completion_probability", "detection_probability",
)
LEGACY_CORE_COLUMNS = (
    "patient_id", "age", "years_since_screen", "never_screened", "prior_abnormal",
    "family_history", "ground_truth_gap", "care_gap_score", "completion_probability",
    "detection_probability",
)
# Backward-compatible export for existing imports.
CORE_COLUMNS = LEGACY_CORE_COLUMNS


@dataclass(frozen=True)
class DerivationConfig:
    screening_interval_years: float = 2.0
    base_completion_probability: float = 0.45
    roi_inputs: BreastROIInputs = BreastROIInputs()

    def validate(self) -> None:
        if not 0.5 <= self.screening_interval_years <= 10:
            raise ValueError("screening_interval_years must be between 0.5 and 10.")
        if not 0 <= self.base_completion_probability <= 1:
            raise ValueError("base_completion_probability must be between 0 and 1.")


@dataclass(frozen=True)
class QualityCheck:
    name: str
    status: str
    detail: str
    affected_rows: int = 0


@dataclass(frozen=True)
class QualityReport:
    row_count: int
    column_count: int
    is_synthetic: bool
    checks: tuple[QualityCheck, ...]
    input_schema: str = "hospital_raw"

    @property
    def passed(self) -> bool:
        return all(check.status != "FAIL" for check in self.checks)

    @property
    def failure_count(self) -> int:
        return sum(check.status == "FAIL" for check in self.checks)

    @property
    def warning_count(self) -> int:
        return sum(check.status == "WARN" for check in self.checks)


def _boolean_series(series: pd.Series) -> pd.Series:
    mapping = {"true": True, "false": False, "1": True, "0": False, "yes": True, "no": False, "y": True, "n": False}
    return series.map(lambda value: mapping.get(str(value).strip().lower()) if pd.notna(value) else pd.NA).astype("boolean")


def _check(name: str, affected: int, fail_detail: str, pass_detail: str) -> QualityCheck:
    return QualityCheck(name, "FAIL" if affected else "PASS", fail_detail if affected else pass_detail, affected)


def _synthetic_status(data: pd.DataFrame) -> tuple[bool, QualityCheck]:
    if "is_synthetic" not in data:
        return False, QualityCheck("Synthetic marker", "WARN", "No synthetic marker was supplied; IDs will be de-identified before downstream use.")
    values = _boolean_series(data["is_synthetic"])
    data["is_synthetic"] = values
    is_synthetic = bool(values.notna().all() and values.fillna(False).all())
    affected = int(values.isna().sum() + (~values.fillna(False)).sum())
    return is_synthetic, QualityCheck(
        "Synthetic marker", "PASS" if is_synthetic else "WARN",
        "Every row is explicitly marked synthetic." if is_synthetic else "Dataset is not uniformly marked synthetic; IDs will be de-identified before downstream use.",
        affected,
    )


def _derive_hospital_fields(data: pd.DataFrame, config: DerivationConfig) -> pd.DataFrame:
    result = data.copy()
    config.validate()
    never = result["never_screened"].fillna(False).astype(bool)
    appointment = result["has_active_appointment"].fillna(False).astype(bool)
    consent = result["outreach_consent"].fillna(False).astype(bool)
    prior = result["prior_abnormal"].fillna(False).astype(bool)
    family = result["family_history"].fillna(False).astype(bool)

    days = (result["as_of_date"] - result["last_screen_date"]).dt.days
    years = (days / 365.25).clip(lower=0, upper=20)
    result["years_since_screen"] = years.where(~never, 20.0).round(2)
    overdue = never | (result["years_since_screen"] >= config.screening_interval_years)
    result["ground_truth_gap"] = (overdue & ~appointment & consent).astype(bool)

    overdue_intensity = np.clip(result["years_since_screen"] / config.screening_interval_years, 0, 2) / 2
    rule_score = (
        0.15 + 0.55 * overdue_intensity + 0.12 * never.astype(float)
        + 0.10 * prior.astype(float) + 0.08 * family.astype(float)
        - 0.35 * appointment.astype(float) - 0.30 * (~consent).astype(float)
    )
    result["care_gap_score"] = np.clip(rule_score, 0, 1).round(6)

    completion = (
        config.base_completion_probability + 0.10 * prior.astype(float)
        + 0.05 * family.astype(float) - 0.08 * never.astype(float)
        - 0.20 * (~consent).astype(float)
    )
    result["completion_probability"] = np.clip(completion, 0.05, 0.90).round(6)

    age_factors = result["age"].map(lambda age: get_age_band(int(age))[1] / 239.8)
    base_detection = config.roi_inputs.cancer_detection_per_1000 / 1000
    result["detection_probability"] = np.clip(base_detection * age_factors, 0, 1).round(6)
    return result


def _validate_hospital(raw: pd.DataFrame, config: DerivationConfig) -> tuple[pd.DataFrame, QualityReport]:
    data = raw.copy()
    checks: list[QualityCheck] = []
    missing = sorted(set(HOSPITAL_REQUIRED_COLUMNS).difference(data.columns))
    checks.append(QualityCheck("Hospital input fields", "FAIL" if missing else "PASS", f"Missing: {', '.join(missing)}" if missing else "All hospital input fields are present.", len(missing)))
    is_synthetic, synthetic_check = _synthetic_status(data)
    if missing:
        checks.append(synthetic_check)
        return data, QualityReport(len(data), len(data.columns), is_synthetic, tuple(checks), "hospital_raw")

    for column in ("prior_abnormal", "family_history"):
        if column not in data:
            data[column] = False
            checks.append(QualityCheck("Optional risk fields", "WARN", f"{column} was not supplied and defaults to false."))
    data["patient_id"] = data["patient_id"].astype("string").str.strip()
    data["age"] = pd.to_numeric(data["age"], errors="coerce")
    for column in ("never_screened", "has_active_appointment", "outreach_consent", "prior_abnormal", "family_history"):
        data[column] = _boolean_series(data[column])
    data["as_of_date"] = pd.to_datetime(data["as_of_date"], errors="coerce")
    data["last_screen_date"] = pd.to_datetime(data["last_screen_date"], errors="coerce")

    empty_ids = int(data["patient_id"].isna().sum() + (data["patient_id"] == "").sum())
    checks.append(_check("Patient IDs", empty_ids, "Patient IDs are missing.", "All rows have a patient ID."))
    duplicate_ids = int(data["patient_id"].duplicated(keep=False).sum())
    checks.append(_check("Duplicate IDs", duplicate_ids, "Duplicate patient IDs were found.", "Patient IDs are unique."))
    age_invalid = int((~data["age"].between(40, 74)).fillna(True).sum())
    checks.append(_check("Age range", age_invalid, "Age must be between 40 and 74.", "All ages are within 40–74."))
    invalid_as_of = int(data["as_of_date"].isna().sum())
    checks.append(_check("As-of date", invalid_as_of, "As-of dates are missing or invalid.", "All as-of dates are valid."))
    needs_date = ~data["never_screened"].fillna(False)
    invalid_last = int((needs_date & data["last_screen_date"].isna()).sum())
    checks.append(_check("Last screen date", invalid_last, "Patients with prior screening need a valid last_screen_date.", "Prior-screened patients have a valid last_screen_date."))
    future_dates = int((data["last_screen_date"].notna() & (data["last_screen_date"] > data["as_of_date"])).sum())
    checks.append(_check("Date chronology", future_dates, "Last screen date cannot be after the as-of date.", "Screening dates follow valid chronology."))
    invalid_booleans = int(data[["never_screened", "has_active_appointment", "outreach_consent"]].isna().any(axis=1).sum())
    checks.append(_check("Required status fields", invalid_booleans, "Required status fields contain invalid values.", "Required status fields are parseable."))
    checks.append(synthetic_check)
    checks.append(QualityCheck("Sample size", "WARN" if len(data) < 100 else "PASS", "Fewer than 100 records may make evaluation metrics unstable." if len(data) < 100 else "Dataset contains at least 100 records.", len(data) if len(data) < 100 else 0))

    report = QualityReport(len(data), len(raw.columns), is_synthetic, tuple(checks), "hospital_raw")
    if report.passed:
        data = _derive_hospital_fields(data, config)
    return data, report


def _validate_legacy(raw: pd.DataFrame) -> tuple[pd.DataFrame, QualityReport]:
    data = raw.copy()
    checks: list[QualityCheck] = [QualityCheck("Legacy derived schema", "WARN", "This file already contains system-derived fields. Hospital-raw format is preferred.")]
    missing = sorted(set(LEGACY_CORE_COLUMNS).difference(data.columns))
    checks.append(QualityCheck("Required columns", "FAIL" if missing else "PASS", f"Missing: {', '.join(missing)}" if missing else "All required columns are present.", len(missing)))
    is_synthetic, synthetic_check = _synthetic_status(data)
    checks.append(synthetic_check)
    if missing:
        return data, QualityReport(len(data), len(data.columns), is_synthetic, tuple(checks), "legacy_derived")
    data["patient_id"] = data["patient_id"].astype("string").str.strip()
    for column in ("never_screened", "prior_abnormal", "family_history", "ground_truth_gap"):
        data[column] = _boolean_series(data[column])
    for column in ("age", "years_since_screen", "care_gap_score", "completion_probability", "detection_probability"):
        data[column] = pd.to_numeric(data[column], errors="coerce")
    invalid = int(data[list(LEGACY_CORE_COLUMNS)].isna().any(axis=1).sum())
    checks.append(_check("Missing or invalid values", invalid, "Core fields contain missing or invalid values.", "Core fields are complete and parseable."))
    duplicates = int(data["patient_id"].duplicated(keep=False).sum())
    checks.append(_check("Duplicate IDs", duplicates, "Duplicate patient IDs were found.", "Patient IDs are unique."))
    return data, QualityReport(len(data), len(raw.columns), is_synthetic, tuple(checks), "legacy_derived")


def validate_population_dataset(raw: pd.DataFrame, config: DerivationConfig | None = None) -> tuple[pd.DataFrame, QualityReport]:
    """Accept hospital-raw input preferentially, with legacy demo compatibility."""
    normalized = raw.copy()
    normalized.columns = [str(column).strip() for column in normalized.columns]
    if set(HOSPITAL_REQUIRED_COLUMNS).issubset(normalized.columns):
        return _validate_hospital(normalized, config or DerivationConfig())
    return _validate_legacy(normalized)


def deidentify_patient_ids(data: pd.DataFrame, salt: str = "breast-roi-copilot") -> pd.DataFrame:
    output = data.copy()
    output["patient_id"] = output["patient_id"].map(lambda value: "HASH-" + sha256(f"{salt}:{value}".encode("utf-8")).hexdigest()[:16])
    return output
