import pytest

from src.population import SyntheticPopulationConfig, generate_synthetic_population
from src.prioritization import OutreachEconomics, simulate_prioritization


def test_prioritized_outreach_reaches_more_true_gaps_than_random():
    population = generate_synthetic_population(
        SyntheticPopulationConfig(population_size=10_000, seed=42, model_noise=0.85)
    )
    economics = OutreachEconomics(12.0, 97.5, 20.792, 50_000.0)
    result = simulate_prioritization(population, 2_000, economics, random_trials=100, seed=42)
    assert result.prioritized.outreach_count == 2_000
    assert result.random.outreach_count == 2_000
    assert result.prioritized.true_gaps_reached > result.random.true_gaps_reached
    assert result.prioritized.expected_completed_screenings > result.random.expected_completed_screenings
    assert result.prioritized.expected_detected_cases > result.random.expected_detected_cases
    assert len(result.selected_prioritized_ids) == 2_000


def test_program_cost_and_roi_use_supplied_economics():
    population = generate_synthetic_population(SyntheticPopulationConfig(population_size=500, seed=3))
    economics = OutreachEconomics(10.0, 100.0, 20.0, 40_000.0)
    result = simulate_prioritization(population, 100, economics, random_trials=5, seed=3).prioritized
    expected_cost = 100 * 10 + result.expected_completed_screenings * 120
    assert result.program_cost == pytest.approx(expected_cost)
    assert result.net_savings == pytest.approx(result.treatment_cost_avoided - result.program_cost)
    assert result.roi == pytest.approx(result.net_savings / result.program_cost)


def test_capacity_cannot_exceed_population():
    population = generate_synthetic_population(SyntheticPopulationConfig(population_size=100))
    economics = OutreachEconomics(1, 1, 1, 1)
    with pytest.raises(ValueError):
        simulate_prioritization(population, 101, economics)
