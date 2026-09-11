"""Dependency-light binary classification metrics for care-gap detection."""

from dataclasses import asdict, dataclass
from typing import Iterable

import pandas as pd


@dataclass(frozen=True)
class ClassificationMetrics:
    threshold: float
    true_positive: int
    false_positive: int
    false_negative: int
    true_negative: int
    sensitivity: float
    specificity: float
    precision: float
    accuracy: float
    f1_score: float
    prevalence: float


def _ratio(numerator: int, denominator: int) -> float:
    return numerator / denominator if denominator else 0.0


def evaluate_classifier(y_true: Iterable[bool], scores: Iterable[float], threshold: float = 0.5) -> ClassificationMetrics:
    """Calculate transparent binary metrics without scikit-learn."""
    true_values = [bool(value) for value in y_true]
    score_values = [float(value) for value in scores]
    if len(true_values) != len(score_values) or not true_values:
        raise ValueError("y_true and scores must have the same non-zero length.")
    if not 0 <= threshold <= 1:
        raise ValueError("threshold must be between 0 and 1.")

    predictions = [score >= threshold for score in score_values]
    tp = sum(actual and predicted for actual, predicted in zip(true_values, predictions))
    fp = sum(not actual and predicted for actual, predicted in zip(true_values, predictions))
    fn = sum(actual and not predicted for actual, predicted in zip(true_values, predictions))
    tn = sum(not actual and not predicted for actual, predicted in zip(true_values, predictions))
    precision = _ratio(tp, tp + fp)
    sensitivity = _ratio(tp, tp + fn)

    return ClassificationMetrics(
        threshold=threshold,
        true_positive=tp,
        false_positive=fp,
        false_negative=fn,
        true_negative=tn,
        sensitivity=sensitivity,
        specificity=_ratio(tn, tn + fp),
        precision=precision,
        accuracy=_ratio(tp + tn, len(true_values)),
        f1_score=_ratio(2 * precision * sensitivity, precision + sensitivity),
        prevalence=_ratio(tp + fn, len(true_values)),
    )


def threshold_sweep(y_true: Iterable[bool], scores: Iterable[float], thresholds: Iterable[float]) -> pd.DataFrame:
    """Evaluate the same synthetic model across operating thresholds."""
    true_values = list(y_true)
    score_values = list(scores)
    return pd.DataFrame(
        [asdict(evaluate_classifier(true_values, score_values, threshold)) for threshold in thresholds]
    )
