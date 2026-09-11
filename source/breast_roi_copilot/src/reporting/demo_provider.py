"""Deterministic, clearly labeled report demo requiring no LLM call."""

from .schemas import EvidenceClaim, ExecutiveReport, ReportAudience


def build_demo_report(
    audience: ReportAudience,
    roi_output: dict,
    approved_evidence: list[dict[str, str]],
    output_language: str = "English",
) -> ExecutiveReport:
    zh = output_language.casefold() in {"chinese", "中文", "zh"}
    roi = roi_output.get("roi")
    roi_text = "not available" if roi is None else f"{float(roi):.1%}"
    evidence_claims: list[EvidenceClaim] = []
    cited_pmids: list[str] = []
    interpretation = "证据不足。" if zh else "Insufficient evidence."
    if approved_evidence:
        row = approved_evidence[0]
        pmid = str(row.get("pmid", ""))
        excerpt = str(row.get("evidence_excerpt", "")).strip()
        if pmid and excerpt:
            evidence_claims = [
                EvidenceClaim(
                    claim=str(row.get("outcome") or "The approved record is relevant to the screening decision."),
                    pmids=[pmid],
                    evidence_excerpt=excerpt,
                )
            ]
            cited_pmids = [pmid]
            interpretation = (
                f"该证据（PMID {pmid}）未直接验证本场景的ROI或关键参数，因此不纳入管理层主结论，详细记录保留在证据附录。"
                if zh else
                f"One human-approved evidence record is available (PMID {pmid}); its applicability remains subject to the documented population and study limitations."
            )

    if zh:
        return ExecutiveReport(
            audience=audience,
            executive_summary=(
                f"当前结果支持进入小范围试点验证：确定性场景预计新增筛查 {roi_output['additional_screened']:,.0f} 人，"
                f"模型 ROI 为 {roi_text}。正式扩大投入前，应先用本地运营与成本数据验证关键假设。"
            ),
            clinical_impact=(
                f"在既定假设下，模型预计检出乳腺癌病例 {roi_output['detected_breast_cancer_cases']:.1f} 例，"
                f"挽救生命 {roi_output['lives_saved']:.1f} 人。"
            ),
            financial_impact=(
                f"模型项目成本为 ${roi_output['screening_program_cost']:,.0f}，净节约为 "
                f"${roi_output['net_savings']:,.0f}。这些数值为确定性模型预测结果。"
            ),
            evidence_interpretation=interpretation,
            key_assumptions=[
                "检出率、死亡率、分期分布、分期转移和成本均属于模型假设。",
                "参数助手建议只有经过人工确认后才能进入模型。",
            ],
            limitations=[
                "结果来自确定性场景模型，尚未经过本地真实实施数据验证。",
                "关键结果会受到实际筛查参与、召回、随访完成和本地成本变化影响。",
            ],
            recommended_actions=[
                "运营团队先核对本地筛查成本、召回率和随访完成率，并锁定试点参数。",
                "选择限定门诊或目标人群开展小范围试点，记录实际触达、筛查、召回、随访与成本。",
                "财务与运营团队将试点实绩和模型预测并排复盘，识别偏差最大的参数。",
                "管理层根据试点结果作出扩大、调整或停止的阶段性决策。",
            ],
            evidence_claims=evidence_claims,
            cited_pmids=cited_pmids,
            simulation_snapshot=dict(roi_output),
        )

    return ExecutiveReport(
        audience=audience,
        executive_summary=(
            f"The deterministic scenario estimates {roi_output['additional_screened']:,.0f} "
            f"additional screens and an ROI of {roi_text}. These are modeled outputs, not guaranteed outcomes."
        ),
        clinical_impact=(
            f"The model estimates {roi_output['detected_breast_cancer_cases']:.1f} detected cases "
            f"and {roi_output['lives_saved']:.1f} lives saved under its stated assumptions."
        ),
        financial_impact=(
            f"Modeled program cost is ${roi_output['screening_program_cost']:,.0f}, with net savings "
            f"of ${roi_output['net_savings']:,.0f}. These values are projections from the deterministic model."
        ),
        evidence_interpretation=interpretation,
        key_assumptions=[
            "Detection, mortality, stage distribution, stage-shift, and cost inputs are model assumptions.",
            "Parameter Copilot values enter the model only after human confirmation.",
        ],
        limitations=[
            "This is a scenario model and does not establish realized clinical or financial outcomes.",
            "Abstract-level evidence may not provide directly transferable effect sizes.",
        ],
        recommended_actions=[
            "Review all assumptions with clinical, finance, and payer stakeholders.",
            "Run sensitivity analyses before using the scenario for planning.",
        ],
        evidence_claims=evidence_claims,
        cited_pmids=cited_pmids,
        simulation_snapshot=dict(roi_output),
    )
