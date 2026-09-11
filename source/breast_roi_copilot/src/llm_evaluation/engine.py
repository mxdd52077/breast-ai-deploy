"""Promptfoo-inspired offline benchmark with deterministic medical assertions."""

import json
import time
from pathlib import Path

import pandas as pd


def load_benchmark(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as stream:
        return json.load(stream)


def _score(case: dict, version: str) -> dict:
    candidate = case["outputs"][version]
    started = time.perf_counter()
    cited = set(candidate.get("cited_pmids", []))
    allowed = set(case["retrieved_pmids"])
    expected = set(case.get("expected_pmids", []))
    status_ok = candidate.get("evidence_status") == case["expected_status"]
    pmid_ok = cited.issubset(allowed)
    retrieval_hit = not expected or bool(expected & allowed)
    refusal_ok = (candidate.get("evidence_status") == "Insufficient evidence") == bool(case["should_refuse"])
    format_ok = all(key in candidate for key in ("answer", "evidence_status", "cited_pmids"))
    forbidden = [term for term in case.get("forbidden_terms", []) if term.casefold() in candidate["answer"].casefold()]
    grounding_ok = pmid_ok and not forbidden
    passed = all((status_ok, pmid_ok, refusal_ok, format_ok, grounding_ok, retrieval_hit))
    return {
        "case_id": case["case_id"],
        "category": case["category"],
        "question": case["question"],
        "prompt_version": version,
        "passed": passed,
        "retrieval_hit": retrieval_hit,
        "pmid_valid": pmid_ok,
        "refusal_correct": refusal_ok,
        "status_correct": status_ok,
        "format_valid": format_ok,
        "grounded": grounding_ok,
        "latency_ms": round((time.perf_counter() - started) * 1000, 3),
        "input_tokens": candidate.get("input_tokens", 0),
        "output_tokens": candidate.get("output_tokens", 0),
        "estimated_cost_usd": candidate.get("estimated_cost_usd", 0.0),
        "error_type": "—" if passed else candidate.get("error_type", "未分类"),
        "answer": candidate["answer"],
        "expected": case["expected_status"],
        "root_cause": candidate.get("root_cause", ""),
        "fix": candidate.get("fix", ""),
    }


def evaluate_cases(cases: list[dict], versions: list[str]) -> pd.DataFrame:
    return pd.DataFrame(_score(case, version) for version in versions for case in cases)
