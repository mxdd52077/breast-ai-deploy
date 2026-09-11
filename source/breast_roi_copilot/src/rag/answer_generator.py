"""Optional OpenAI provider for live structured evidence synthesis."""

from src.evidence.schemas import PubMedArticle

from .prompts import SYSTEM_PROMPT, build_evidence_prompt
from .schemas import GroundedAnswer


class EvidenceGenerationError(RuntimeError):
    """A user-safe failure from the live LLM provider."""


def generate_with_openai(
    question: str,
    articles: list[PubMedArticle],
    api_key: str,
    model: str = "gpt-5.6-luna",
) -> GroundedAnswer:
    if not question.strip():
        raise ValueError("Question cannot be empty.")
    if not articles:
        raise ValueError("At least one retrieved PubMed article is required.")
    if not api_key.strip():
        raise ValueError("An OpenAI API key is required for live analysis.")

    try:
        from openai import OpenAI
    except ImportError as exc:
        raise EvidenceGenerationError(
            "The OpenAI SDK is not installed. Run pip install -r requirements.txt."
        ) from exc

    try:
        client = OpenAI(api_key=api_key)
        response = client.responses.parse(
            model=model,
            input=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": build_evidence_prompt(question, articles)},
            ],
            text_format=GroundedAnswer,
        )
        if response.output_parsed is None:
            raise EvidenceGenerationError("The model did not return a structured answer.")
        return response.output_parsed
    except EvidenceGenerationError:
        raise
    except Exception as exc:
        raise EvidenceGenerationError(
            "Live evidence analysis failed. No unvalidated answer was displayed."
        ) from exc
