from pathlib import Path

from src.llm_evaluation import evaluate_cases, load_benchmark


def test_offline_benchmark_exposes_prompt_improvement():
    path = Path(__file__).parents[1] / "data" / "llm_eval_benchmark_v1.json"
    cases = load_benchmark(path)
    results = evaluate_cases(cases, ["Prompt V1", "Prompt V3"])
    rates = results.groupby("prompt_version")["passed"].mean()
    assert len(cases) == 6
    assert rates["Prompt V3"] > rates["Prompt V1"]
    assert {"pmid_valid", "refusal_correct", "retrieval_hit", "error_type"}.issubset(results.columns)
