import { useEffect, useRef, type ReactNode } from "react";
import { ChevronLeft, ChevronRight, X, CalendarDays } from "lucide-react";
import { shortDate, today, type Task } from "./api";

export function Modal({
  title,
  children,
  onClose,
  wide = false,
}: {
  title: string;
  children: ReactNode;
  onClose: () => void;
  wide?: boolean;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    ref.current?.showModal();
    return () => ref.current?.close();
  }, []);
  return (
    <dialog
      className={wide ? "modal wide" : "modal"}
      ref={ref}
      onCancel={onClose}
      onClick={(e) => {
        if (e.target === ref.current) onClose();
      }}
    >
      <header className="modal-head">
        <h2>{title}</h2>
        <button className="icon-btn" aria-label="关闭" onClick={onClose}>
          <X size={22} />
        </button>
      </header>
      {children}
    </dialog>
  );
}
export function Badge({ status }: { status: string }) {
  const labels: Record<string, string> = {
    pending: "待核对",
    confirmed: "已确认",
    rejected: "已排除",
    queued: "等待整理",
    processing: "正在整理",
    failed: "需重试",
    ready: "已整理",
    completed: "已完成",
    skipped: "已跳过",
  };
  return <span className={"badge " + status}>{labels[status] || status}</span>;
}
export function Empty({
  title,
  text,
  action,
}: {
  title: string;
  text: string;
  action?: ReactNode;
}) {
  return (
    <div className="empty">
      <img src="/art/checklist.png" alt="" />
      <div>
        <h3>{title}</h3>
        <p>{text}</p>
        {action}
      </div>
    </div>
  );
}
export function Calendar({
  month,
  selected,
  tasks,
  onMonth,
  onSelect,
}: {
  month: Date;
  selected: string;
  tasks: Task[];
  onMonth: (d: Date) => void;
  onSelect: (d: string) => void;
}) {
  const year = month.getFullYear(),
    m = month.getMonth();
  const first = new Date(year, m, 1);
  const offset = (first.getDay() + 6) % 7;
  const length = new Date(year, m + 1, 0).getDate();
  const cells = Array.from(
    { length: Math.ceil((offset + length) / 7) * 7 },
    (_, i) => {
      const d = new Date(year, m, i - offset + 1);
      const key = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
      return { day: d.getDate(), key, out: d.getMonth() !== m };
    },
  );
  const marks = new Set(tasks.filter((t) => t.active).map((t) => t.due_date));
  return (
    <section className="panel calendar">
      <h3>
        <CalendarDays size={20} />
        照护日历
      </h3>
      <div className="month-nav">
        <button
          className="icon-btn"
          aria-label="上个月"
          onClick={() => onMonth(new Date(year, m - 1, 1))}
        >
          <ChevronLeft size={18} />
        </button>
        <strong>
          {year}年{m + 1}月
        </strong>
        <button
          className="icon-btn"
          aria-label="下个月"
          onClick={() => onMonth(new Date(year, m + 1, 1))}
        >
          <ChevronRight size={18} />
        </button>
      </div>
      <div className="calendar-grid">
        {"一二三四五六日".split("").map((x) => (
          <span className="weekday" key={x}>
            {x}
          </span>
        ))}
        {cells.map((c) => (
          <button
            key={c.key}
            aria-label={`${c.key}${marks.has(c.key) ? " 有安排" : ""}`}
            aria-pressed={selected === c.key}
            onClick={() => onSelect(c.key)}
            className={[
              c.out ? "outside" : "",
              c.key === selected ? "selected" : "",
              marks.has(c.key) ? "has-task" : "",
              c.key === today() ? "today" : "",
            ].join(" ")}
          >
            {c.day}
            {marks.has(c.key) && <i />}
          </button>
        ))}
      </div>
      <button
        className="text-btn today-link"
        onClick={() => {
          onMonth(new Date());
          onSelect(today());
        }}
      >
        回到今天
      </button>
    </section>
  );
}
export function TaskRow({
  task,
  onStatus,
  onSource,
  busy,
}: {
  task: Task;
  onStatus: (status: string) => void;
  onSource: () => void;
  busy: boolean;
}) {
  const overdue =
    task.active && task.status === "pending" && task.due_date < today();
  return (
    <div className={"task-row " + (!task.active ? "inactive" : "")}>
      <div className="task-symbol">
        <CalendarDays size={20} />
      </div>
      <div className="task-main">
        <div className="task-meta">
          <span>
            {shortDate(task.due_date)} {task.due_time || "时间未指定"}
            {task.due_end_date && (
              <>
                {" 至 "}
                {shortDate(task.due_end_date)} {task.due_end_time || "时间未指定"}
              </>
            )}
          </span>
          {overdue && <span className="overdue">待补记</span>}
          {!task.active && <span className="badge pending">来源待核对</span>}
        </div>
        <p>{task.title}</p>
        <button className="text-btn" onClick={onSource}>
          查看资料来源
        </button>
      </div>
      <select
        aria-label="任务状态"
        value={task.status}
        disabled={busy || !task.active}
        onChange={(e) => onStatus(e.target.value)}
      >
        <option value="pending">待完成</option>
        <option value="completed">已完成</option>
        <option value="skipped">已跳过</option>
      </select>
    </div>
  );
}
