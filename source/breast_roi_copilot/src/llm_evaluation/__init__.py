"""Offline, reproducible evaluation utilities for the medical RAG workflow."""

from .engine import evaluate_cases, load_benchmark

__all__ = ["evaluate_cases", "load_benchmark"]
