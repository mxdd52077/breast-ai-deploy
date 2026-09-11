import { useState } from "react";
import { api } from "./api";
const names: Record<string, string> = {
  true_positive: "真阳性",
  false_positive: "假阳性",
  false_negative: "假阴性",
  true_negative: "真阴性",
  sensitivity: "敏感度",
  specificity: "特异度",
  precision: "精确率",
  accuracy: "准确率",
  f1_score: "F1",
  prevalence: "样本阳性比例",
};
export default function ModelEvaluation({
  onError,
}: {
  onError: (s: string) => void;
}) {
  const [file, setFile] = useState<File | null>(null),
    [note, setNote] = useState(""),
    [threshold, setThreshold] = useState(0.5),
    [busy, setBusy] = useState(false),
    [result, setResult] = useState<{
      metrics: Record<string, number | null>;
      notice: string;
      row_count: number;
    } | null>(null);
  async function run() {
    setBusy(true);
    try {
      const body = new FormData();
      body.append("file", file!);
      body.append("source_note", note);
      body.append("threshold", String(threshold));
      setResult(await api("/institution/evaluation", { method: "POST", body }));
    } catch (e) {
      onError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <section className="panel">
      <h2>模型效果评估</h2>
      <p className="muted">
        上传独立观察的真实标签与模型分数，计算混淆矩阵和分类指标。CSV仅需label（0或1）、score（0到1），不需要患者身份信息。请说明标签含义、观察窗口和样本来源。
      </p>
      <label className="field">
        标签与评分 CSV
        <input
          type="file"
          accept=".csv"
          onChange={(e) => {
            setFile(e.target.files?.[0] || null);
            setResult(null);
          }}
        />
      </label>
      <label className="field">
        标签定义与数据来源
        <textarea
          value={note}
          onChange={(e) => setNote(e.target.value)}
          maxLength={1000}
        />
      </label>
      <label className="field">
        判定阈值
        <input
          type="number"
          min={0}
          max={1}
          step=".01"
          value={threshold}
          onChange={(e) => setThreshold(Number(e.target.value))}
        />
      </label>
      <button
        className="outline"
        disabled={busy || !file || note.trim().length < 3}
        onClick={() => void run()}
      >
        {busy ? "计算中…" : "计算评估指标"}
      </button>
      {result && (
        <>
          <p>
            {result.row_count} 条样本 · {result.notice}
          </p>
          <div className="result-grid">
            {Object.entries(names).map(([k, l]) => (
              <div key={k}>
                <span>{l}</span>
                <strong>
                  {result.metrics[k] === null
                    ? "不适用"
                    : result.metrics[k]?.toLocaleString("zh-CN", {
                        maximumFractionDigits: 3,
                      })}
                </strong>
              </div>
            ))}
          </div>
        </>
      )}
    </section>
  );
}
