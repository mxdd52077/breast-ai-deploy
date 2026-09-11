import pytest

from src.evaluation import evaluate_classifier, threshold_sweep


def test_classification_metrics_match_known_confusion_matrix():
    metrics = evaluate_classifier(
        [True, True, False, False], [0.9, 0.4, 0.6, 0.1], threshold=0.5
    )
    assert (metrics.true_positive, metrics.false_positive, metrics.false_negative, metrics.true_negative) == (1, 1, 1, 1)
    assert metrics.sensitivity == pytest.approx(0.5)
    assert metrics.specificity == pytest.approx(0.5)
    assert metrics.precision == pytest.approx(0.5)
    assert metrics.accuracy == pytest.approx(0.5)
    assert metrics.f1_score == pytest.approx(0.5)


def test_threshold_sweep_returns_one_row_per_threshold():
    table = threshold_sweep([True, False], [0.8, 0.2], [0.3, 0.5, 0.7])
    assert table["threshold"].tolist() == [0.3, 0.5, 0.7]
    assert len(table) == 3
