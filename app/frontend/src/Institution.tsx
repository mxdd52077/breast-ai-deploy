import { useEffect, useState } from "react";
import { Calculator, Download, History } from "lucide-react";
import { api, type Simulation } from "./api";
import DataCheck from "./DataCheck";
import AnalysisTable from "./AnalysisTable";
import DecisionAssistant from "./DecisionAssistant";
import ModelEvaluation from "./ModelEvaluation";
const names: Record<string, string> = {
  population_size: "目标人群人数",
  current_screening_rate: "当前筛查率 %",
  target_screening_rate: "目标筛查率 %",
  average_age: "平均年龄",
  mammography_cost: "单次筛查成本",
  screening_interval: "筛查间隔（年）",
  recall_rate: "召回率 %",
  followup_cost: "随访单次成本",
  followup_completion_rate: "随访完成率 %",
  cancer_detection_per_1000: "每千人检出数",
  lives_saved_per_1000: "每千人挽救生命数",
  localized_stage_percent: "局限期占比 %",
  regional_stage_percent: "区域期占比 %",
  distant_stage_percent: "远处期占比 %",
  unknown_stage_percent: "未知分期占比 %",
  localized_stage_cost: "局限期治疗成本",
  regional_stage_cost: "区域期治疗成本",
  distant_stage_cost: "远处期治疗成本",
  regional_to_local_shift: "区域转局限期比例 %",
  distant_to_regional_shift: "远处转区域期比例 %",
};
const results: Record<string, string> = {
  additional_screened: "新增筛查人数",
  detected_breast_cancer_cases: "预计检出病例",
  screening_program_cost: "项目总成本",
  treatment_cost_avoided: "预计避免治疗成本",
  net_savings: "预计净节省",
  roi: "投资回报率",
};
export default function Institution({
  onError,
}: {
  onError: (s: string) => void;
}) {
  const [inputs, setInputs] = useState<
      Record<string, number | string | boolean>
    >({}),
    [name, setName] = useState("筛查规划方案"),
    [result, setResult] = useState<Simulation | null>(null),
    [history, setHistory] = useState<Simulation[]>([]),
    [busy, setBusy] = useState(false);
  const [approvals, setApprovals] = useState<
    Record<string, { id: string; value: number }>
  >({});
  const [sources, setSources] = useState<Record<string, string>>({});
  const [hospitalKeys, setHospitalKeys] = useState<string[]>([]);
  useEffect(() => {
    Promise.all([
      api<Record<string, number | string | boolean>>("/institution/defaults"),
      api<Simulation[]>("/institution/simulations"),
    ])
      .then(([i, h]) => {
        setInputs(i);
        setHistory(h);
      })
      .catch((e) => onError(e.message));
  }, [onError]);
  async function run() {
    setBusy(true);
    try {
      const r = await api<Simulation>("/institution/simulations", {
        method: "POST",
        body: JSON.stringify({
          name,
          inputs,
          approval_ids: Object.values(approvals).map((x) => x.id),
          sources,
        }),
      });
      setResult(r);
      setHistory(await api("/institution/simulations"));
    } catch (e) {
      onError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  function exportResult() {
    if (!result) return;
    const u = URL.createObjectURL(
      new Blob([JSON.stringify(result, null, 2)], { type: "application/json" }),
    );
    const a = document.createElement("a");
    a.href = u;
    a.download = "APEX-规划测算.json";
    a.click();
    setTimeout(() => URL.revokeObjectURL(u), 10000);
  }
  return (
    <>
      <div className="page-title">
        <div>
          <h1>机构决策</h1>
          <p>参数有据可查，结果可重复计算。</p>
        </div>
      </div>
      <p className="notice-box">
        模型范围：40–74岁女性 DBT
        筛查。以下为规划测算；默认参数来自原模型，未完成中国本地校准。所有成本须使用同一币种。
      </p>
      <DataCheck
        onError={onError}
        onApply={(values, source) => {
          setInputs((v) => ({ ...v, ...values }));
          setHospitalKeys(Object.keys(values));
          if (source)
            setSources((v) => ({
              ...v,
              ...Object.fromEntries(
                Object.keys(values).map((k) => [k, source]),
              ),
            }));
        }}
      />
      <DecisionAssistant
        onError={onError}
        result={result}
        onApply={(values, approval, source) => {
          const next = approval
            ? values
            : Object.fromEntries(
                Object.entries(values).filter(
                  ([k]) => !hospitalKeys.includes(k),
                ),
              );
          setInputs((v) => ({ ...v, ...next }));
          setSources((v) =>
            Object.fromEntries(Object.entries(v).filter(([k]) => !(k in next))),
          );
          setApprovals((v) =>
            Object.fromEntries(Object.entries(v).filter(([k]) => !(k in next))),
          );
          if (approval)
            setApprovals((v) => ({
              ...v,
              [approval.parameter!]: {
                id: approval.id,
                value: approval.value!,
              },
            }));
          if (source)
            setSources((v) => ({
              ...v,
              ...Object.fromEntries(Object.keys(next).map((k) => [k, source])),
            }));
        }}
      />
      <div className="institution-grid">
        <section className="panel">
          <h2>确认规划参数</h2>
          <label className="field">
            方案名称
            <input
              value={name}
              maxLength={80}
              onChange={(e) => setName(e.target.value)}
            />
          </label>
          <div className="parameter-grid">
            {Object.entries(inputs)
              .filter(([key]) => key in names)
              .map(([key, value]) => (
                <label className="field" key={key}>
                  {names[key] || key}
                  <small>
                    {approvals[key]
                      ? "来源：已批准PubMed证据"
                      : sources[key]
                        ? hospitalKeys.includes(key)
                          ? "来源：已确认医院数据"
                          : "来源：已确认场景"
                        : "来源：人工输入或原模型假设（待本地校准）"}
                  </small>
                  <input
                    type="number"
                    min="0"
                    step="any"
                    value={String(value)}
                    onChange={(e) => {
                      setApprovals((v) => {
                        const n = { ...v };
                        delete n[key];
                        return n;
                      });
                      setSources((v) => {
                        const n = { ...v };
                        delete n[key];
                        return n;
                      });
                      setInputs((v) => ({
                        ...v,
                        [key]:
                          e.target.value === "" ? "" : Number(e.target.value),
                      }));
                    }}
                  />
                </label>
              ))}
          </div>
          <label className="checkbox">
            <input
              type="checkbox"
              checked={!!inputs.redistribute_unknown_stage}
              onChange={(e) =>
                setInputs((v) => ({
                  ...v,
                  redistribute_unknown_stage: e.target.checked,
                }))
              }
            />
            按已知比例分配未知分期
          </label>
          <button
            className="primary full"
            disabled={busy || !Object.keys(inputs).length}
            onClick={() => void run()}
          >
            <Calculator size={18} />
            {busy ? "正在计算…" : "确认参数并计算"}
          </button>
        </section>
        <div>
          <section className="panel">
            <div className="section-head">
              <h2>结果对照</h2>
              {result && (
                <button className="text-btn" onClick={exportResult}>
                  <Download size={16} />
                  导出
                </button>
              )}
            </div>
            {result ? (
              <>
                <h3>{result.name}</h3>
                <div className="result-grid">
                  {Object.entries(results).map(([k, l]) => (
                    <div key={k}>
                      <span>{l}</span>
                      <strong>
                        {result.results[k] == null
                          ? "不适用"
                          : typeof result.results[k] === "number"
                            ? k === "roi"
                              ? ((result.results[k] as number) * 100).toFixed(
                                  1,
                                ) + "%"
                              : (result.results[k] as number).toLocaleString(
                                  "zh-CN",
                                  { maximumFractionDigits: 1 },
                                )
                            : result.results[k]}
                      </strong>
                    </div>
                  ))}
                </div>
                <p className="muted">
                  结果由 Python 确定性内核计算，未使用大模型改写数值。
                </p>
              </>
            ) : (
              <p className="muted">确认左侧参数后查看测算结果。</p>
            )}
          </section>
          <section className="panel history-panel">
            <h2>
              <History size={19} />
              已保存方案
            </h2>
            {history.length ? (
              history.map((r) => (
                <button
                  className="history-row"
                  key={r.id}
                  onClick={() => {
                    setResult(r);
                    setInputs(r.inputs);
                    setName(r.name);
                    setApprovals(
                      Object.fromEntries(
                        Object.entries(r.analysis.provenance || {})
                          .filter(([, v]) => v.approval_id)
                          .map(([k, v]) => [
                            k,
                            { id: v.approval_id!, value: Number(v.value) },
                          ]),
                      ),
                    );
                    setSources(
                      Object.fromEntries(
                        Object.entries(r.analysis.provenance || {})
                          .filter(([, v]) => v.source_id)
                          .map(([k, v]) => [k, v.source_id!]),
                      ),
                    );
                    setHospitalKeys(
                      Object.entries(r.analysis.provenance || {})
                        .filter(
                          ([, v]) => v.kind === "institution_data_proposal",
                        )
                        .map(([k]) => k),
                    );
                  }}
                >
                  <strong>{r.name}</strong>
                  <span>查看与调整 →</span>
                </button>
              ))
            ) : (
              <p className="muted">计算后自动保存，可再次打开对照。</p>
            )}
          </section>
        </div>
      </div>
      {result && (
        <>
          <AnalysisTable
            title="规划情景对照（非置信区间）"
            rows={result.analysis.scenarios}
          />
          <AnalysisTable
            title="单因素敏感性分析"
            rows={result.analysis.sensitivity}
          />
        </>
      )}
      <ModelEvaluation onError={onError} />
    </>
  );
}
