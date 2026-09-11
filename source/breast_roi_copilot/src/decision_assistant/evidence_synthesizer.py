"""Grounded cross-document synthesis for decision-assistant parameters."""

import re
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.evidence import PubMedArticle


class EvidenceRelevance(StrEnum):
    DIRECT = "direct"
    INDIRECT = "indirect"
    NOT_RELEVANT = "not_relevant"


class ParameterName(StrEnum):
    DETECTION = "cancer_detection_per_1000"
    RECALL = "recall_rate_percent"


class ArticleAssessment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pmid: str
    relevance: EvidenceRelevance
    population: str
    modality: str
    study_design: str
    extracted_parameter: ParameterName | None = None
    extracted_value: float | None = Field(default=None, ge=0)
    evidence_excerpt: str | None = None
    transferability: str
    limitations: list[str]

    @model_validator(mode="after")
    def numeric_claim_requires_excerpt(self):
        if (self.extracted_value is None) != (self.evidence_excerpt is None):
            raise ValueError("A numeric extraction and its evidence excerpt must be provided together.")
        return self


class ParameterRecommendation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    parameter: ParameterName
    evidence_low: float | None = Field(default=None, ge=0)
    evidence_high: float | None = Field(default=None, ge=0)
    recommended_value: float | None = Field(default=None, ge=0)
    action: str = Field(description="Use candidate, keep default, or insufficient evidence.")
    rationale: str
    supporting_pmids: list[str]
    limitations: list[str]


class EvidenceSynthesis(BaseModel):
    model_config = ConfigDict(extra="forbid")

    overall_summary: str
    assessments: list[ArticleAssessment]
    recommendations: list[ParameterRecommendation]
    conflicts: list[str]


class EvidenceSynthesisError(RuntimeError):
    """Safe error for generation or deterministic grounding failures."""


SYSTEM_PROMPT = """You are a cautious breast-screening evidence analyst.
Use only the supplied PubMed titles and abstracts. Assess every supplied article.
The target parameters are cancer detection rate per 1,000 screenings and recall rate percent.
Do not confuse supplemental-test detection rates, AI-reader performance, sensitivity, PPV,
false-positive rate, or abnormal interpretation rate with the target parameters.
For every extracted number, copy a short exact excerpt containing that number from the abstract.
Mark population/modality mismatch as indirect or not relevant. Never average heterogeneous studies.
A recommended value may only equal one of the directly transferable extracted values; otherwise use
null and action 'keep default' or 'insufficient evidence'. Cite only supplied PMIDs.
Write summaries, rationales, transferability notes, conflicts, and limitations in Chinese."""


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().casefold()


def _number_appears(value: float, excerpt: str) -> bool:
    candidates = {str(value), f"{value:g}", f"{value:.1f}", f"{value:.2f}"}
    return any(candidate in excerpt for candidate in candidates)


def complete_missing_assessments(
    synthesis: EvidenceSynthesis,
    articles: list[PubMedArticle],
) -> EvidenceSynthesis:
    """Add explicit no-extraction rows when the model accidentally skips an article."""
    article_map = {article.pmid: article for article in articles}
    assessed_pmids = [assessment.pmid for assessment in synthesis.assessments]
    unknown = set(assessed_pmids) - set(article_map)
    duplicates = {pmid for pmid in assessed_pmids if assessed_pmids.count(pmid) > 1}

    # Unknown citations and every copy of a duplicated assessment are discarded.
    # This preserves readable synthesis while preventing contaminated rows from
    # contributing a value to a recommendation.
    completed = [
        assessment
        for assessment in synthesis.assessments
        if assessment.pmid in article_map and assessment.pmid not in duplicates
    ]
    kept_pmids = {assessment.pmid for assessment in completed}
    missing = [pmid for pmid in article_map if pmid not in kept_pmids]
    for pmid in missing:
        completed.append(
            ArticleAssessment(
                pmid=pmid,
                relevance=EvidenceRelevance.INDIRECT,
                population="AI未完成评估",
                modality="AI未完成评估",
                study_design="AI未完成评估",
                extracted_parameter=None,
                extracted_value=None,
                evidence_excerpt=None,
                transferability="本轮AI未返回该文献的评估，因此不得用于参数建议。",
                limitations=["需要重新运行AI总结或进入专业证据页面人工审阅。"],
            )
        )
    contamination_notes = []
    if unknown:
        contamination_notes.append(
            "AI生成了本次检索之外的PMID，系统已删除："
            + "、".join(f"PMID {pmid}" for pmid in sorted(unknown))
        )
    if duplicates:
        contamination_notes.append(
            "AI重复评估了文献，系统已删除重复条目并标记为待复核："
            + "、".join(f"PMID {pmid}" for pmid in sorted(duplicates))
        )
    if missing:
        contamination_notes.append(
            "以下文献本轮未形成唯一、可信的AI评估，已标记且不参与参数建议："
            + "、".join(f"PMID {pmid}" for pmid in missing)
        )

    if missing or unknown or duplicates:
        recommendations = synthesis.recommendations
        if unknown or duplicates:
            # Once citation identity is contaminated, numeric roll-ups cannot be
            # trusted even if some individual rows look plausible.
            recommendations = [
                recommendation.model_copy(
                    update={
                        "evidence_low": None,
                        "evidence_high": None,
                        "recommended_value": None,
                        "action": "insufficient evidence",
                        "supporting_pmids": [],
                        "rationale": recommendation.rationale
                        + " 本轮存在PMID身份异常，系统已撤销数值建议，请重新运行或人工复核。",
                        "limitations": [
                            *recommendation.limitations,
                            "本轮AI输出包含陌生或重复PMID。",
                        ],
                    }
                )
                for recommendation in recommendations
            ]
        synthesis = synthesis.model_copy(
            update={
                "assessments": completed,
                "recommendations": recommendations,
                "conflicts": [*synthesis.conflicts, *contamination_notes],
            }
        )
    return synthesis


def validate_evidence_synthesis(
    synthesis: EvidenceSynthesis,
    articles: list[PubMedArticle],
) -> EvidenceSynthesis:
    article_map = {article.pmid: article for article in articles}
    if not article_map:
        raise EvidenceSynthesisError("没有可供总结的PubMed文献。")

    assessed_pmids = [assessment.pmid for assessment in synthesis.assessments]
    if set(assessed_pmids) != set(article_map) or len(assessed_pmids) != len(set(assessed_pmids)):
        raise EvidenceSynthesisError("AI必须逐篇评估本次检索到的全部文献，且不得增加其他PMID。")

    validated_values: dict[ParameterName, list[tuple[float, str]]] = {
        ParameterName.DETECTION: [],
        ParameterName.RECALL: [],
    }
    for assessment in synthesis.assessments:
        article = article_map[assessment.pmid]
        if assessment.evidence_excerpt is None:
            continue
        if _normalize(assessment.evidence_excerpt) not in _normalize(article.abstract):
            raise EvidenceSynthesisError(f"PMID {assessment.pmid} 的引用片段不在原摘要中。")
        if not _number_appears(float(assessment.extracted_value), assessment.evidence_excerpt):
            raise EvidenceSynthesisError(f"PMID {assessment.pmid} 的候选数字不在引用片段中。")
        validated_values[assessment.extracted_parameter].append(
            (float(assessment.extracted_value), assessment.pmid)
        )

    seen_parameters: set[ParameterName] = set()
    for recommendation in synthesis.recommendations:
        if recommendation.parameter in seen_parameters:
            raise EvidenceSynthesisError("每个ROI参数只能生成一条综合建议。")
        seen_parameters.add(recommendation.parameter)
        valid_pairs = validated_values[recommendation.parameter]
        valid_values = [value for value, _ in valid_pairs]
        valid_pmids = {pmid for _, pmid in valid_pairs}
        if not set(recommendation.supporting_pmids).issubset(valid_pmids):
            raise EvidenceSynthesisError("参数建议引用了没有对应数值原文的PMID。")
        if recommendation.recommended_value is not None and not any(
            abs(recommendation.recommended_value - value) < 1e-9 for value in valid_values
        ):
            raise EvidenceSynthesisError("建议值必须来自已通过原文校验的文献数值。")
        if valid_values:
            if recommendation.evidence_low is not None and recommendation.evidence_low != min(valid_values):
                raise EvidenceSynthesisError("证据区间下限与已验证文献数值不一致。")
            if recommendation.evidence_high is not None and recommendation.evidence_high != max(valid_values):
                raise EvidenceSynthesisError("证据区间上限与已验证文献数值不一致。")
        elif any(value is not None for value in (recommendation.evidence_low, recommendation.evidence_high, recommendation.recommended_value)):
            raise EvidenceSynthesisError("没有通过原文校验的数值时不得生成数值建议。")
    return synthesis


def synthesize_evidence_with_openai(
    articles: list[PubMedArticle],
    scenario: dict,
    api_key: str,
    model: str,
) -> EvidenceSynthesis:
    if not api_key.strip():
        raise ValueError("需要配置OpenAI API key才能总结文献。")
    evidence_text = "\n\n".join(
        f"PMID: {article.pmid}\nTITLE: {article.title}\nABSTRACT: {article.abstract}"
        for article in articles
    )
    try:
        from openai import OpenAI

        response = OpenAI(api_key=api_key).responses.parse(
            model=model,
            input=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": (
                        "目标场景：" + str(scenario) + "\n\n本次检索文献：\n" + evidence_text
                    ),
                },
            ],
            text_format=EvidenceSynthesis,
        )
        if response.output_parsed is None:
            raise EvidenceSynthesisError("AI没有返回结构化文献总结。")
        completed = complete_missing_assessments(response.output_parsed, articles)
        return validate_evidence_synthesis(completed, articles)
    except (EvidenceSynthesisError, ValueError):
        raise
    except Exception as exc:
        raise EvidenceSynthesisError("文献总结失败，未生成或应用任何参数建议。") from exc
