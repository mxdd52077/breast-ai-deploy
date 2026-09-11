"""OpenAI Structured Outputs provider dedicated to the patient experience."""

from .schemas import KnowledgeChunk, PatientAnswer, PatientCase, PatientExtraction, SourceDocument
from .validation import validate_case_provenance


DEFAULT_PATIENT_MODEL = "gpt-5.6-sol"


class PatientAIError(RuntimeError):
    """A user-safe failure from the patient AI provider."""


def _safe_openai_error(exc: Exception, action: str) -> str:
    error_name = type(exc).__name__
    status_code = getattr(exc, "status_code", None)
    if error_name == "AuthenticationError" or status_code == 401:
        return "OpenAI API Key 无效或已被撤销，请更新服务端 Key 后重试。"
    if error_name in {"PermissionDeniedError", "NotFoundError"} or status_code in {403, 404}:
        return "当前 OpenAI 项目无权使用所选模型，请检查模型权限或模型名称。"
    if error_name == "RateLimitError" or status_code == 429:
        return "OpenAI 请求达到限额或账户额度不足，请检查用量与账单后重试。"
    if error_name in {"APITimeoutError", "APIConnectionError"}:
        return "连接 OpenAI 超时或网络不可用，请稍后重试。"
    if error_name == "BadRequestError" or status_code == 400:
        return "OpenAI 拒绝了结构化请求；系统未展示未经验证的结果。"
    return f"{action}失败；系统未展示未经验证的结果。"


def _client(api_key: str):
    if not api_key.strip():
        raise ValueError("PATIENT_OPENAI_API_KEY 未配置。")
    try:
        from openai import OpenAI
    except ImportError as exc:
        raise PatientAIError("OpenAI SDK 未安装。") from exc
    return OpenAI(api_key=api_key)


def assemble_patient_case(
    documents: list[SourceDocument], extraction: PatientExtraction
) -> PatientCase:
    validate_case_provenance(documents, extraction.facts, extraction.events)
    return PatientCase(
        profile=extraction.profile,
        documents=documents,
        facts=extraction.facts,
        events=extraction.events,
    )


def extract_case_with_openai(
    documents: list[SourceDocument],
    api_key: str,
    model: str = DEFAULT_PATIENT_MODEL,
) -> PatientCase:
    document_text = "\n\n".join(
        f"文档ID={document.id} 文件名={document.filename}\n"
        + "\n".join(f"页码={page.page_number}\n{page.text}" for page in document.pages)
        for document in documents
    )
    prompt = f"""请将以下脱敏医疗文档整理为 PatientExtraction。
只能提取原文明确出现的事实。每个 ClinicalFact 必须保留逐字 original_text、文档 ID 和页码；
所有事实和事件默认标记为待确认。不得诊断、补充治疗、药物、剂量或日期。

文档：
{document_text}
"""
    try:
        response = _client(api_key).responses.parse(
            model=model,
            input=[
                {
                    "role": "system",
                    "content": "你是乳腺癌患者照护导航助手，不是医生。严格遵守来源边界。",
                },
                {"role": "user", "content": prompt},
            ],
            text_format=PatientExtraction,
        )
        if response.output_parsed is None:
            raise PatientAIError("模型没有返回可验证的结构化结果。")
        return assemble_patient_case(documents, response.output_parsed)
    except (PatientAIError, ValueError):
        raise
    except Exception as exc:
        raise PatientAIError(_safe_openai_error(exc, "患者资料分析")) from exc


def answer_with_openai(
    question: str,
    chunks: list[KnowledgeChunk],
    api_key: str,
    model: str = DEFAULT_PATIENT_MODEL,
) -> PatientAnswer:
    if not chunks:
        return PatientAnswer(
            answer="当前知识库没有足够证据回答这个问题。请咨询治疗团队。",
            status="insufficient_evidence",
            citations=[],
        )
    context = "\n\n".join(f"[{chunk.id}] {chunk.text}" for chunk in chunks)
    try:
        response = _client(api_key).responses.parse(
            model=model,
            input=[
                {
                    "role": "system",
                    "content": (
                        "只根据提供的知识片段回答患者问题。引用只能使用方括号中的 ID；"
                        "不得诊断、改药或推荐治疗方案。证据不足时明确拒答。"
                    ),
                },
                {"role": "user", "content": f"问题：{question}\n\n知识片段：\n{context}"},
            ],
            text_format=PatientAnswer,
        )
        answer = response.output_parsed
        if answer is None:
            raise PatientAIError("模型没有返回可验证的结构化答案。")
        allowed = {chunk.id for chunk in chunks}
        if not set(answer.citations).issubset(allowed):
            raise PatientAIError("回答包含无法验证的知识来源。")
        return answer
    except (PatientAIError, ValueError):
        raise
    except Exception as exc:
        raise PatientAIError(_safe_openai_error(exc, "知识问答")) from exc
