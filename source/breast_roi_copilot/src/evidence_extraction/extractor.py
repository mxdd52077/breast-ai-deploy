"""Optional OpenAI provider for live effect-size extraction."""

from src.evidence.schemas import PubMedArticle
from src.rag.answer_generator import EvidenceGenerationError

from .prompts import SYSTEM_PROMPT, build_extraction_prompt
from .schemas import ExtractedEvidence


def extract_with_openai(
    article: PubMedArticle,
    api_key: str,
    model: str = "gpt-5.6-luna",
) -> ExtractedEvidence:
    if not api_key.strip():
        raise ValueError("An OpenAI API key is required for live extraction.")
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise EvidenceGenerationError(
            "The OpenAI SDK is not installed. Run pip install -r requirements.txt."
        ) from exc

    try:
        response = OpenAI(api_key=api_key).responses.parse(
            model=model,
            input=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": build_extraction_prompt(article)},
            ],
            text_format=ExtractedEvidence,
        )
        if response.output_parsed is None:
            raise EvidenceGenerationError("The model did not return structured evidence.")
        return response.output_parsed
    except EvidenceGenerationError:
        raise
    except Exception as exc:
        raise EvidenceGenerationError(
            "Live extraction failed. No unvalidated evidence was saved."
        ) from exc
