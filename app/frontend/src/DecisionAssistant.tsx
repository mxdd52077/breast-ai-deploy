import { useEffect, useState } from "react";
import { api, streamInstitution, type Simulation } from "./api";

type Entry = {
  id: string;
  kind?: string;
  parameter?: string;
  value?: number;
  title?: string;
  pmid?: string;
  abstract?: string;
  url?: string;
  quote?: string;
  applicability?: string;
  status?: string;
  report?: Report;
  simulation_id?: string;
  [key: string]: unknown;
};
type Report = {
  executive_summary: string;
  clinical_impact: string;
  financial_impact: string;
  evidence_interpretation: string;
  key_assumptions: string[];
  limitations: string[];
  recommended_actions: string[];
  evidence_claims: {
    claim: string;
    pmids: string[];
    evidence_excerpt: string;
  }[];
  cited_pmids: string[];
};
const labels: Record<string, string> = {
  population_size: "目标人群人数",
  average_age: "平均年龄",
  current_screening_rate: "当前筛查率 %",
  target_screening_rate: "目标筛查率 %",
  cancer_detection_per_1000: "每千人检出数",
  recall_rate: "召回率 %",
};
const metrics: Record<string, string> = {
  outreach_count: "外展人数",
  true_gaps_reached: "触达照护缺口人数",
  expected_completed_screenings: "预计完成筛查",
  expected_detected_cases: "预计检出病例",
  program_cost: "项目成本",
  net_savings: "净节约",
  roi: "ROI（比值）",
};
export default function DecisionAssistant({
  onError,
  onApply,
  result,
}: {
  onError: (s: string) => void;
  onApply: (
    v: Record<string, number>,
    approval?: Entry,
    source?: string,
  ) => void;
  result: Simulation | null;
}) {
  const [step, setStep] = useState("scenario");
  const [outreachCost, setOutreachCost] = useState(10),
    [completion, setCompletion] = useState(0.45),
    [hospitalFile, setHospitalFile] = useState<File | null>(null),
    [assumptions, setAssumptions] = useState(false),
    [text, setText] = useState("希望将40–74岁女性DBT筛查率提升至70%"),
    [query, setQuery] = useState(
      "digital breast tomosynthesis screening cancer detection recall rate",
    ),
    [entries, setEntries] = useState<Entry[]>([]),
    [draft, setDraft] = useState<Entry | null>(null),
    [busy, setBusy] = useState(""),
    [note, setNote] = useState(""),
    [capacity, setCapacity] = useState(200),
    [population, setPopulation] = useState(1000),
    [comparison, setComparison] = useState<{
      selected_rows?: {
        rank: number;
        source_row: number;
        priority_score: number;
      }[];
      random: Record<string, number>;
      prioritized: Record<string, number>;
      formula: string;
      assumptions: Record<string, number>;
    } | null>(null);
  const refresh = async () =>
    setEntries(await api<Entry[]>("/institution/workflow"));
  useEffect(() => {
    void refresh().catch((e) => onError(e.message));
  }, [onError]);
  async function act(label: string, fn: () => Promise<void>) {
    setBusy(label);
    try {
      await fn();
      await refresh();
    } catch (e) {
      onError((e as Error).message);
    } finally {
      setBusy("");
    }
  }
  const post = <T,>(path: string, body?: unknown) =>
    api<T>("/institution" + path, {
      method: "POST",
      ...(body === undefined ? {} : { body: JSON.stringify(body) }),
    });
  const articles = entries.filter((x) => x.kind === "institution_article");
  const candidates = entries.filter((x) => x.kind === "institution_candidate");
  const reports = entries.filter(
    (x) =>
      ["institution_report", "institution_report_approved"].includes(
        x.kind || "",
      ) && x.simulation_id === result?.id,
  );
  function exportReport(entry: Entry) {
    const r = entry.report!;
    const content =
      `# APEX 管理层报告\n\n方案：${result?.name}\n状态：${entry.status}\n\n` +
      [
        r.executive_summary,
        r.clinical_impact,
        r.financial_impact,
        r.evidence_interpretation,
        "## 假设\n" + r.key_assumptions.join("\n\n"),
        "## 局限性\n" + r.limitations.join("\n\n"),
        "## 建议\n" + r.recommended_actions.join("\n\n"),
        ...r.evidence_claims.map(
          (c) =>
            `${c.claim}\n\n${c.evidence_excerpt}\n\n${c.pmids.map((p) => "https://pubmed.ncbi.nlm.nih.gov/" + p + "/").join("\n")}`,
        ),
        "## 锁定计算与审批记录\n```json\n" +
          JSON.stringify({ entry, simulation: result }, null, 2) +
          "\n```",
      ].join("\n\n");
    const url = URL.createObjectURL(
      new Blob([content], { type: "text/markdown;charset=utf-8" }),
    );
    const a = document.createElement("a");
    a.href = url;
    a.download = "APEX-管理层报告.md";
    a.click();
    setTimeout(() => URL.revokeObjectURL(url), 10000);
  }
  return (
    <section className="panel">
      <h2>AI 决策助手</h2>
      <p className="muted">
        描述场景 → 检索证据 → 确认参数 → 计算 →
        审批报告。AI候选不会自动进入测算。
      </p>
      <div className="section-head" aria-label="机构工作流步骤">
        {Object.entries({
          scenario: "场景解析",
          evidence: "证据与审批",
          outreach: "外展规划",
          report: "管理报告",
        }).map(([k, l]) => (
          <button
            key={k}
            className={step === k ? "primary small" : "outline small"}
            aria-pressed={step === k}
            onClick={() => setStep(k)}
          >
            {l}
          </button>
        ))}
      </div>
      <div hidden={step !== "scenario"}>
        <label className="field">
          目标场景
          <textarea
            value={text}
            onChange={(e) => setText(e.target.value)}
            maxLength={3000}
          />
        </label>
        <button
          className="primary"
          disabled={!!busy}
          onClick={() =>
            void act("解析场景", async () => {
              const d = await streamInstitution<Entry>("/scenario-stream", { text });
              setDraft(d);
              if (typeof d.pubmed_query === "string") setQuery(d.pubmed_query);
            })
          }
        >
          解析场景
        </button>
        {draft && (
          <div className="notice-box">
            <h3>场景候选</h3>
            {Object.entries(labels)
              .filter(([k]) => typeof draft[k] === "number")
              .map(([k, l]) => (
                <p key={k}>
                  {l}：{String(draft[k])}
                </p>
              ))}
            <p>缺失：{(draft.missing_fields as string[]).join("、") || "无"}</p>
            <p>假设：{(draft.assumptions as string[]).join("；") || "无"}</p>
            <button
              className="outline"
              onClick={() =>
                onApply(
                  Object.fromEntries(
                    Object.keys(labels)
                      .filter((k) => typeof draft[k] === "number")
                      .map((k) => [k, draft[k] as number]),
                  ),
                  undefined,
                  draft.id,
                )
              }
            >
              确认应用场景参数
            </button>
            <p>已应用的医院汇总参数优先保留；可在参数表中人工调整。</p>
          </div>
        )}
        <details>
          <summary>历史场景</summary>
          {entries
            .filter((x) => x.kind === "institution_scenario")
            .map((x) => (
              <button
                className="history-row"
                key={x.id}
                onClick={() => setDraft(x)}
              >
                查看场景 · 目标筛查率{" "}
                {String(x.target_screening_rate ?? "待补充")}%
              </button>
            ))}
        </details>
      </div>
      <div hidden={step !== "evidence"}>
        <h3>PubMed 证据与参数</h3>
        <label className="field">
          检索式
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            maxLength={3000}
          />
        </label>
        <button
          className="outline"
          disabled={!!busy}
          onClick={() =>
            void act("检索文献", async () => {
              const found = await post<Entry[]>("/evidence/search", {
                text: query,
              });
              if (!found.length) onError("未检索到文献，请调整检索式。");
            })
          }
        >
          检索真实文献
        </button>
        <p className="muted">
          仅提取摘要中直接报告的绝对检出率及召回率。
          <a
            href="https://www.ncbi.nlm.nih.gov/About/disclaimer.html"
            target="_blank"
            rel="noreferrer"
          >
            NCBI 使用与版权说明
          </a>
        </p>
        {articles.map((a) => (
          <details key={a.id}>
            <summary>
              {a.title} · PMID {a.pmid}
            </summary>
            <p>{a.abstract || "无摘要，无法提取参数"}</p>
            <a href={a.url} target="_blank" rel="noreferrer">
              查看 PubMed 原文记录
            </a>
            <button
              className="text-btn"
              disabled={!!busy || !a.abstract}
              onClick={() =>
                void act("提取候选", async () => {
                  const found = await streamInstitution<Entry[]>(
                    "/evidence/" + a.id + "/extract-stream",
                  );
                  if (!found.length)
                    onError(
                      "该摘要未提供可直接采用的DBT参数，请选择其他文献。",
                    );
                })
              }
            >
              提取参数候选
            </button>
          </details>
        ))}
        <label className="field">
          适用性与审批说明
          <input
            value={note}
            onChange={(e) => setNote(e.target.value)}
            placeholder="说明证据对本院人群的适用性；报告审批也使用此说明"
            maxLength={1000}
          />
        </label>
        {candidates.map((c) => (
          <div className="notice-box" key={c.id}>
            <strong>
              {labels[c.parameter!] || c.parameter}：{c.value}
            </strong>
            <p>{c.applicability}</p>
            <blockquote>{c.quote}</blockquote>
            <p>
              PMID {c.pmid} · {c.title}
            </p>
            <button
              className="outline"
              disabled={!!busy || !note.trim()}
              onClick={() =>
                void act("批准参数", async () => {
                  const a = await post<Entry>(
                    "/candidates/" + c.id + "/approve",
                    { note },
                  );
                  onApply({ [a.parameter!]: a.value! }, a);
                })
              }
            >
              批准并应用此参数
            </button>
          </div>
        ))}
      </div>
      <div hidden={step !== "outreach"}>
        <h3>合成人群外展对比</h3>
        <p className="muted">
          固定种子42，随机外展100次。使用原模型默认经济参数，全部为合成演示，不代表医院模型效果。
        </p>
        <div className="parameter-grid">
          <label className="field">
            合成人数
            <input
              type="number"
              min={100}
              max={10000}
              value={population}
              onChange={(e) => setPopulation(Number(e.target.value))}
            />
          </label>
          <label className="field">
            外展名额
            <input
              type="number"
              min={1}
              max={population}
              value={capacity}
              onChange={(e) => setCapacity(Number(e.target.value))}
            />
          </label>
        </div>
        <button
          className="outline"
          disabled={!!busy}
          onClick={() =>
            void act("模拟外展", async () =>
              setComparison(
                await post("/outreach", { population, capacity, seed: 42 }),
              ),
            )
          }
        >
          比较随机与风险优先外展
        </button>
        {comparison && (
          <>
            <p>{comparison.formula}</p>
            {comparison.selected_rows && (
              <button
                className="text-btn"
                onClick={() => {
                  const url = URL.createObjectURL(
                    new Blob(
                      [
                        "rank,source_row,priority_score\n" +
                          comparison
                            .selected_rows!.map(
                              (r) =>
                                `${r.rank},${r.source_row},${r.priority_score}`,
                            )
                            .join("\n"),
                      ],
                      { type: "text/csv" },
                    ),
                  );
                  const a = document.createElement("a");
                  a.href = url;
                  a.download = "APEX-外展行号清单.csv";
                  a.click();
                  setTimeout(() => URL.revokeObjectURL(url), 10000);
                }}
              >
                导出外展优先顺序（原CSV行号，含表头）
              </button>
            )}
            <div className="table-scroll">
              <table>
                <thead>
                  <tr>
                    <th>指标</th>
                    <th>随机外展</th>
                    <th>风险优先外展</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(metrics).map(([k, l]) => (
                    <tr key={k}>
                      <td>{l}</td>
                      <td>
                        {comparison.random[k]?.toLocaleString("zh-CN", {
                          maximumFractionDigits: 2,
                        }) ?? "不适用"}
                      </td>
                      <td>
                        {comparison.prioritized[k]?.toLocaleString("zh-CN", {
                          maximumFractionDigits: 2,
                        }) ?? "不适用"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <details>
              <summary>已确认的经济与概率假设</summary>
              <pre>{JSON.stringify(comparison.assumptions, null, 2)}</pre>
            </details>
          </>
        )}
        <h3>医院数据外展</h3>
        <p className="muted">
          上传通过校验的医院CSV，使用当前已保存方案的成本与检出率。原始行不入库，仅保存汇总对比。
        </p>
        <label className="field">
          医院CSV
          <input
            type="file"
            accept=".csv"
            onChange={(e) => setHospitalFile(e.target.files?.[0] || null)}
          />
        </label>
        <div className="parameter-grid">
          <label className="field">
            每次外展成本
            <input
              type="number"
              min={0}
              value={outreachCost}
              onChange={(e) => setOutreachCost(Number(e.target.value))}
            />
          </label>
          <label className="field">
            基础完成概率（0–1）
            <input
              type="number"
              min={0}
              max={1}
              step="0.01"
              value={completion}
              onChange={(e) => setCompletion(Number(e.target.value))}
            />
          </label>
        </div>
        <label className="checkbox">
          <input
            type="checkbox"
            checked={assumptions}
            onChange={(e) => setAssumptions(e.target.checked)}
          />
          确认以上成本与完成概率假设（成本与方案同币种）；结果用于规划，未经过真实结局验证。
        </label>
        <button
          className="outline"
          disabled={!!busy || !result || !hospitalFile || !assumptions}
          onClick={() =>
            void act("医院数据外展", async () => {
              const form = new FormData();
              form.append("file", hospitalFile!);
              form.append("simulation_id", result!.id);
              form.append("capacity", String(capacity));
              form.append("assumptions_confirmed", "true");
              form.append("cost_per_outreach", String(outreachCost));
              form.append("base_completion_probability", String(completion));
              setComparison(
                await api("/institution/outreach/hospital", {
                  method: "POST",
                  body: form,
                }),
              );
            })
          }
        >
          使用医院数据比较外展策略
        </button>
      </div>
      <div hidden={step !== "report"}>
        <h3>管理层报告</h3>
        <label className="field">
          报告审批说明
          <input
            value={note}
            onChange={(e) => setNote(e.target.value)}
            maxLength={1000}
            placeholder="确认数字、引用和建议适用性后填写"
          />
        </label>
        <p className="muted">
          {result
            ? "基于已保存方案「" +
              result.name +
              "」，参数修改后需重新计算再生成报告。"
            : "先确认参数并计算，才能生成报告。"}
          报告通过数字与引用校验后保存为草稿，人工批准后可导出。
        </p>
        <button
          className="outline"
          disabled={!!busy || !result}
          onClick={() =>
            void act("生成报告", async () => {
              await streamInstitution("/simulations/" + result!.id + "/report-stream");
            })
          }
        >
          生成已锁定结果的报告
        </button>
        {reports.map((x) => (
          <details key={x.id}>
            <summary>
              {x.status === "approved" ? "已批准报告" : "待审批草稿"}
            </summary>
            {x.report && (
              <>
                <p>{x.report.executive_summary}</p>
                <p>{x.report.clinical_impact}</p>
                <p>{x.report.financial_impact}</p>
                <p>{x.report.evidence_interpretation}</p>
                {(
                  [
                    "key_assumptions",
                    "limitations",
                    "recommended_actions",
                  ] as const
                ).map((k, i) => (
                  <div key={k}>
                    <h4>{["关键假设", "局限性", "下一步建议"][i]}</h4>
                    <ul>
                      {x.report![k].map((t, j) => (
                        <li key={j}>{t}</li>
                      ))}
                    </ul>
                  </div>
                ))}
                {x.report.evidence_claims.map((c, i) => (
                  <blockquote key={i}>
                    {c.claim}
                    <p>{c.evidence_excerpt}</p>
                    {c.pmids.map((p) => (
                      <a
                        key={p}
                        href={"https://pubmed.ncbi.nlm.nih.gov/" + p + "/"}
                        target="_blank"
                        rel="noreferrer"
                      >
                        PMID {p}{" "}
                      </a>
                    ))}
                  </blockquote>
                ))}
              </>
            )}
            {x.status === "approved" ? (
              <button className="text-btn" onClick={() => exportReport(x)}>
                导出已批准报告
              </button>
            ) : (
              <button
                className="outline"
                disabled={!!busy || !note.trim()}
                onClick={() =>
                  void act("批准报告", async () => {
                    await post("/reports/" + x.id + "/approve", { note });
                  })
                }
              >
                确认内容并批准报告
              </button>
            )}
          </details>
        ))}
      </div>
      {busy && <p role="status">正在{busy}，请稍候…</p>}
    </section>
  );
}
