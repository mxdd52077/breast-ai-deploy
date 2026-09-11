import { useRef, useState } from "react";
import { UploadCloud } from "lucide-react";
import { api } from "./api";
type Result = {
  passed: boolean;
  row_count: number;
  proposals?: Record<string, number>;
  source_id?: string;
  derivations?: string[];
  checks: {
    name: string;
    status: string;
    detail: string;
    affected_rows: number;
  }[];
};
const labels: Record<string, string> = {
  "Hospital input fields": "医院数据字段",
  "Patient IDs": "患者编号完整性",
  "Duplicate IDs": "重复编号",
  "Age range": "年龄范围",
  "As-of date": "统计日期",
  "Last screen date": "上次筛查日期",
  "Date chronology": "日期先后顺序",
  "Required status fields": "状态字段",
  "Synthetic marker": "虚构资料标记",
  "Sample size": "样本数量",
  "Optional risk fields": "可选字段",
};
export default function DataCheck({
  onError,
  onApply,
}: {
  onError: (s: string) => void;
  onApply: (values: Record<string, number>, source?: string) => void;
}) {
  const input = useRef<HTMLInputElement>(null);
  const [result, setResult] = useState<Result | null>(null),
    [busy, setBusy] = useState(false),
    [name, setName] = useState("");
  async function check(file: File) {
    setBusy(true);
    setResult(null);
    try {
      const form = new FormData();
      form.append("file", file);
      const r = await api<Result>("/institution/data-check", {
        method: "POST",
        body: form,
      });
      setResult(r);
      setName(file.name);
    } catch (e) {
      onError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <section className="panel">
      <div className="section-head">
        <h2>数据质量检查</h2>
        <button
          className="outline small"
          disabled={busy}
          onClick={() => input.current?.click()}
        >
          <UploadCloud size={16} />
          {busy ? "正在检查…" : "检查CSV"}
        </button>
      </div>
      <p className="muted">
        检查必填字段、重复编号、年龄和日期。文件在本次请求中分析，界面仅显示汇总结果。
      </p>
      <div className="section-head">
        <a className="text-btn" href="/api/institution/sample.csv" download>
          下载示例 CSV
        </a>
        <button
          className="outline small"
          disabled={busy}
          onClick={async () => {
            try {
              const r = await fetch("/api/institution/sample.csv");
              if (!r.ok) throw new Error("示例加载失败");
              await check(new File([await r.blob()], "APEX-synthetic.csv"));
            } catch (e) {
              onError((e as Error).message);
            }
          }}
        >
          使用内置合成数据
        </button>
      </div>
      <details>
        <summary>查看字段要求</summary>
        <p className="muted">
          patient_id、as_of_date、age、last_screen_date、never_screened、has_active_appointment、outreach_consent。日期用
          YYYY-MM-DD，状态用 true/false。演示数据增加
          is_synthetic=true。最多4MB、50000行。
        </p>
      </details>
      <input
        hidden
        ref={input}
        type="file"
        accept=".csv"
        onChange={(e) => {
          if (e.target.files?.[0]) void check(e.target.files[0]);
          e.target.value = "";
        }}
      />
      {result && (
        <>
          <h3 className="data-check-title">
            {name} · {result.row_count}行 ·{" "}
            {result.passed ? "检查通过" : "需要修正"}
          </h3>
          <div className="table-scroll">
            <table>
              <thead>
                <tr>
                  <th>检查项</th>
                  <th>结果</th>
                  <th>影响行数</th>
                </tr>
              </thead>
              <tbody>
                {result.checks.map((r, i) => (
                  <tr key={i}>
                    <td>
                      <details>
                        <summary>{labels[r.name] || r.name}</summary>
                        <p>{r.detail}</p>
                      </details>
                    </td>
                    <td>
                      <span
                        className={
                          "badge " +
                          (r.status === "PASS"
                            ? "confirmed"
                            : r.status === "FAIL"
                              ? "failed"
                              : "pending")
                        }
                      >
                        {r.status === "PASS"
                          ? "通过"
                          : r.status === "FAIL"
                            ? "失败"
                            : "提醒"}
                      </span>
                    </td>
                    <td>{r.affected_rows}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {result.passed && (
            <>
              <p>
                建议人数 {result.proposals?.population_size}，平均年龄{" "}
                {result.proposals?.average_age} 岁，当前筛查率{" "}
                {result.proposals?.current_screening_rate}%。
              </p>
              <button
                className="text-btn"
                onClick={() =>
                  result.proposals &&
                  onApply(result.proposals, result.source_id)
                }
              >
                确认并应用数据汇总参数 →
              </button>
            </>
          )}
          <details>
            <summary>派生字段计算来源</summary>
            {result.derivations?.map((x) => (
              <p key={x}>{x}</p>
            ))}
          </details>
        </>
      )}
    </section>
  );
}
