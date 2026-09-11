"""Create a reproducible synthetic breast-screening care-gap population."""

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class SyntheticPopulationConfig:
    population_size: int = 10_000
    seed: int = 42
    model_noise: float = 0.85

    def validate(self) -> None:
        if not 100 <= self.population_size <= 1_000_000:
            raise ValueError("population_size must be between 100 and 1,000,000.")
        if not 0 <= self.model_noise <= 3:
            raise ValueError("model_noise must be between 0 and 3.")


def _sigmoid(values: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-values))


def generate_synthetic_population(config: SyntheticPopulationConfig) -> pd.DataFrame:
    """Return fictional patient-level records for workflow testing only.

    Ground truth is an operational demo definition: a patient is overdue when
    the synthetic time since last screening is at least two years. The care-gap
    score deliberately contains noise so performance evaluation is meaningful.
    """
    config.validate()
    rng = np.random.default_rng(config.seed)
    size = config.population_size

    age = rng.integers(40, 75, size=size)
    years_since_screen = np.clip(rng.gamma(shape=2.0, scale=1.25, size=size), 0, 8)
    never_screened = rng.random(size) < 0.08
    years_since_screen = np.where(never_screened, 8.0, years_since_screen)
    prior_abnormal = rng.random(size) < (0.07 + 0.002 * (age - 40))
    family_history = rng.random(size) < 0.16
    ground_truth_gap = years_since_screen >= 2.0

    overdue_intensity = np.clip((years_since_screen - 1.0) / 5.0, 0, 1)
    age_intensity = (age - 40) / 34
    score_logit = (
        -1.45
        + 3.2 * overdue_intensity
        + 0.35 * age_intensity
        + 0.45 * prior_abnormal
        + 0.35 * family_history
        + rng.normal(0, config.model_noise, size)
    )
    care_gap_score = _sigmoid(score_logit)

    completion_probability = np.clip(
        0.36 + 0.30 * care_gap_score + 0.08 * prior_abnormal - 0.04 * never_screened,
        0.15,
        0.90,
    )
    detection_probability = np.clip(
        0.0030
        + 0.00013 * (age - 40)
        + 0.0030 * prior_abnormal
        + 0.0020 * family_history,
        0.002,
        0.020,
    )

    return pd.DataFrame(
        {
            "patient_id": [f"SYN-{index:06d}" for index in range(1, size + 1)],
            "age": age,
            "years_since_screen": years_since_screen.round(2),
            "never_screened": never_screened,
            "prior_abnormal": prior_abnormal,
            "family_history": family_history,
            "ground_truth_gap": ground_truth_gap,
            "care_gap_score": care_gap_score.round(6),
            "completion_probability": completion_probability.round(6),
            "detection_probability": detection_probability.round(6),
        }
    )
