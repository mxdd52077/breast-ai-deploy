export default function AnalysisTable({
  title,
  rows,
}: {
  title: string;
  rows: Record<string, number | string | null>[];
}) {
  if (!rows.length) return null;
  const keys = Object.keys(rows[0]);
  return (
    <section className="panel">
      <h2>{title}</h2>
      <div className="table-scroll">
        <table>
          <thead>
            <tr>
              {keys.map((k) => (
                <th key={k}>{k}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((r, i) => (
              <tr key={i}>
                {keys.map((k) => (
                  <td key={k}>
                    {r[k] == null
                      ? "不适用"
                      : typeof r[k] === "number"
                        ? k === "ROI"
                          ? (Number(r[k]) * 100).toFixed(1) + "%"
                          : Number(r[k]).toLocaleString("zh-CN", {
                              maximumFractionDigits: 1,
                            })
                        : r[k]}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
