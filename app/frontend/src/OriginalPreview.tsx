import { useState } from "react";
export default function OriginalPreview({
  id,
  name,
  page,
}: {
  id: string;
  name: string;
  page: number;
}) {
  const [open, setOpen] = useState(false);
  const ext = name.split(".").pop()?.toLowerCase();
  if (!ext || !["pdf", "png", "jpg", "jpeg", "webp"].includes(ext)) return null;
  const url = `/api/documents/${id}/file?inline=true`;
  return (
    <div className="original-preview">
      <button className="outline small" onClick={() => setOpen(!open)}>
        {open ? "收起原件" : "展开原件对照"}
      </button>
      {open && (
        <>
          {ext === "pdf" ? (
            <iframe title="PDF原件" src={`${url}#page=${page}`} />
          ) : (
            <a href={url} target="_blank" rel="noreferrer">
              <img src={url} alt="上传资料的原始图片，点击放大查看" />
            </a>
          )}
          <p className="muted">
            请对照原件核实文字、日期和数值。
            <a href={url} target="_blank" rel="noreferrer">
              在新窗口打开
            </a>
          </p>
        </>
      )}
    </div>
  );
}
