"""Parse a natural-language hospital scenario without performing ROI mathematics."""

from pydantic import BaseModel, ConfigDict, Field


class ScenarioDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")

    population_size: int | None = Field(default=None, ge=0)
    current_screening_rate: float | None = Field(default=None, ge=0, le=100)
    target_screening_rate: float | None = Field(default=None, ge=0, le=100)
    average_age: int | None = Field(default=None, ge=40, le=74)
    screening_modality: str | None = None
    cancer_detection_per_1000: float | None = Field(default=None, ge=0)
    recall_rate: float | None = Field(default=None, ge=0, le=100)
    missing_fields: list[str]
    assumptions: list[str]
    pubmed_query: str = Field(min_length=3)


class ScenarioParsingError(RuntimeError):
    """A safe error raised when the live scenario parser fails."""


SYSTEM_PROMPT = """You parse a hospital breast-screening scenario into a strict schema.
Do not calculate ROI and do not invent values that the user did not supply.
Use null for missing numeric fields and list them in missing_fields.
The product scope is women aged 40-74 and mammography/DBT screening.
Create one concise PubMed query focused on cancer detection rate per 1,000 and recall rate
for the supplied modality and population. Do not add cost terms to the PubMed query.
State every normalization or interpretation in assumptions."""


def parse_scenario_with_openai(text: str, api_key: str, model: str) -> ScenarioDraft:
    if not text.strip():
        raise ValueError("Scenario cannot be empty.")
    if not api_key.strip():
        raise ValueError("An OpenAI API key is required.")
    try:
        from openai import OpenAI

        response = OpenAI(api_key=api_key).responses.parse(
            model=model,
            input=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": text.strip()},
            ],
            text_format=ScenarioDraft,
        )
        if response.output_parsed is None:
            raise ScenarioParsingError("The model did not return a structured scenario.")
        return response.output_parsed
    except ScenarioParsingError:
        raise
    except Exception as exc:
        raise ScenarioParsingError("Scenario parsing failed. No values were applied.") from exc
