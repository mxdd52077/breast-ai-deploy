import pandas as pd

from src.population import SyntheticPopulationConfig, generate_synthetic_population


def test_synthetic_population_is_reproducible_and_non_identifiable():
    config = SyntheticPopulationConfig(population_size=1_000, seed=7, model_noise=0.8)
    first = generate_synthetic_population(config)
    second = generate_synthetic_population(config)
    pd.testing.assert_frame_equal(first, second)
    assert len(first) == 1_000
    assert first["patient_id"].str.startswith("SYN-").all()
    assert first["age"].between(40, 74).all()
    assert first["care_gap_score"].between(0, 1).all()
    assert 0 < first["ground_truth_gap"].mean() < 1


def test_synthetic_population_rejects_invalid_size():
    try:
        generate_synthetic_population(SyntheticPopulationConfig(population_size=10))
    except ValueError as error:
        assert "population_size" in str(error)
    else:
        raise AssertionError("Expected invalid population size to fail")
