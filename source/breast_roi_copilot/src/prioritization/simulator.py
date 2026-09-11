"""Compare random outreach with care-gap-risk-prioritized outreach."""

from dataclasses import dataclass

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class OutreachEconomics:
    cost_per_outreach: float
    annualized_screening_cost: float
    expected_followup_cost_per_screen: float
    stage_shift_savings_per_case: float


@dataclass(frozen=True)
class StrategyResult:
    strategy: str
    outreach_count: int
    true_gaps_reached: float
    expected_completed_screenings: float
    expected_detected_cases: float
    treatment_cost_avoided: float
    program_cost: float
    net_savings: float
    roi: float | None


@dataclass(frozen=True)
class PrioritizationComparison:
    random: StrategyResult
    prioritized: StrategyResult
    priority_score: pd.Series
    selected_prioritized_ids: tuple[str, ...]


def _result(name: str, selected: pd.DataFrame, economics: OutreachEconomics) -> StrategyResult:
    valid_gap = selected["ground_truth_gap"].astype(float)
    completed = float((valid_gap * selected["completion_probability"]).sum())
    detected = float(
        (valid_gap * selected["completion_probability"] * selected["detection_probability"]).sum()
    )
    avoided = detected * economics.stage_shift_savings_per_case
    program_cost = (
        len(selected) * economics.cost_per_outreach
        + completed * (economics.annualized_screening_cost + economics.expected_followup_cost_per_screen)
    )
    net = avoided - program_cost
    return StrategyResult(
        strategy=name,
        outreach_count=len(selected),
        true_gaps_reached=float(valid_gap.sum()),
        expected_completed_screenings=completed,
        expected_detected_cases=detected,
        treatment_cost_avoided=avoided,
        program_cost=program_cost,
        net_savings=net,
        roi=net / program_cost if program_cost else None,
    )


def simulate_prioritization(
    population: pd.DataFrame,
    outreach_capacity: int,
    economics: OutreachEconomics,
    random_trials: int = 100,
    seed: int = 42,
) -> PrioritizationComparison:
    """Run a deterministic priority strategy and Monte Carlo random benchmark."""
    required = {
        "patient_id", "ground_truth_gap", "care_gap_score", "years_since_screen",
        "completion_probability", "detection_probability",
    }
    missing = required.difference(population.columns)
    if missing:
        raise ValueError(f"Population is missing required columns: {sorted(missing)}")
    if not 1 <= outreach_capacity <= len(population):
        raise ValueError("outreach_capacity must be between 1 and the population size.")
    if random_trials < 1:
        raise ValueError("random_trials must be at least 1.")
    if min(
        economics.cost_per_outreach,
        economics.annualized_screening_cost,
        economics.expected_followup_cost_per_screen,
        economics.stage_shift_savings_per_case,
    ) < 0:
        raise ValueError("Economic inputs cannot be negative.")

    overdue = np.clip((population["years_since_screen"] - 1.0) / 5.0, 0, 1)
    priority_score = (
        0.60 * population["care_gap_score"]
        + 0.25 * overdue
        + 0.15 * population["completion_probability"]
    )
    prioritized_index = priority_score.nlargest(outreach_capacity).index
    prioritized = _result("Risk-prioritized", population.loc[prioritized_index], economics)

    rng = np.random.default_rng(seed)
    trial_results = []
    indices = population.index.to_numpy()
    for _ in range(random_trials):
        sampled = rng.choice(indices, size=outreach_capacity, replace=False)
        trial_results.append(_result("Random", population.loc[sampled], economics))

    random = StrategyResult(
        strategy="Random",
        outreach_count=outreach_capacity,
        true_gaps_reached=float(np.mean([row.true_gaps_reached for row in trial_results])),
        expected_completed_screenings=float(np.mean([row.expected_completed_screenings for row in trial_results])),
        expected_detected_cases=float(np.mean([row.expected_detected_cases for row in trial_results])),
        treatment_cost_avoided=float(np.mean([row.treatment_cost_avoided for row in trial_results])),
        program_cost=float(np.mean([row.program_cost for row in trial_results])),
        net_savings=float(np.mean([row.net_savings for row in trial_results])),
        roi=float(np.mean([row.roi for row in trial_results if row.roi is not None])),
    )
    selected_ids = tuple(population.loc[prioritized_index, "patient_id"].astype(str))
    return PrioritizationComparison(random, prioritized, priority_score.rename("priority_score"), selected_ids)
