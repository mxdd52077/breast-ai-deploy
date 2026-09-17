import {
  useCallback,
  useEffect,
  useRef,
  useState,
  type FormEvent,
} from "react";
import {
  ArrowLeft,
  ArrowRight,
  Bell,
  Building2,
  CalendarDays,
  Check,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Clock,
  Download,
  FileCheck2,
  FileText,
  FolderHeart,
  Heart,
  Home,
  ImagePlus,
  LayoutDashboard,
  LoaderCircle,
  LogOut,
  MessageCircle,
  Plus,
  Ribbon,
  Search,
  Send,
  Settings,
  ShieldCheck,
  Trash2,
  UploadCloud,
  X,
} from "lucide-react";
import {
  api,
  APIError,
  setCsrf,
  shortDate,
  today,
  type User,
  type Workspace,
  type Fact,
  type Task,
  type Doc,
  type Source,
  type Message,
  streamQuestion,
} from "./api";
import { Badge, Calendar, Empty, Modal, TaskRow } from "./components";
import Institution from "./Institution";
import OriginalPreview from "./OriginalPreview";

type Page = "home" | "documents" | "care" | "chat" | "settings" | "institution";
const labels: Record<Page, string> = {
  home: "照护首页",
  documents: "我的档案",
  care: "照护计划",
  chat: "知识问答",
  settings: "个人设置",
  institution: "机构决策",
};
const nav = [
  { key: "home" as Page, icon: Home },
  { key: "documents" as Page, icon: FolderHeart },
  { key: "care" as Page, icon: FileCheck2 },
  { key: "chat" as Page, icon: MessageCircle },
];
const empty: Workspace = {
  documents: [],
  facts: [],
  tasks: [],
  user: { id: "", name: "", demo: false, institution_access: false },
};

export default function App() {
  const [user, setUser] = useState<User | null>(null),
    [loading, setLoading] = useState(true),
    [data, setData] = useState<Workspace>(empty);
  const [page, setPage] = useState<Page>("home"),
    [uploadOpen, setUploadOpen] = useState(false),
    [reviewDoc, setReviewDoc] = useState<string | null>(null),
    [reviewFact, setReviewFact] = useState<string | null>(null);
  const [error, setError] = useState(""),
    [toast, setToast] = useState(""),
    [busy, setBusy] = useState(false);
  const [month, setMonth] = useState(new Date()),
    [selected, setSelected] = useState(today());
  const [query, setQuery] = useState(""),
    [docFilter, setDocFilter] = useState("all"),
    [taskFilter, setTaskFilter] = useState("upcoming");
  const [source, setSource] = useState<Source | null>(null),
    [note, setNote] = useState(""),
    [factValue, setFactValue] = useState(""),
    [reportDate, setReportDate] = useState(""),
    [scheduleDate, setScheduleDate] = useState(""),
    [scheduleTime, setScheduleTime] = useState(""),
    [scheduleEndDate, setScheduleEndDate] = useState(""),
    [scheduleEndTime, setScheduleEndTime] = useState(""),
    [report, setReport] = useState<{ facts: Fact[]; notice: string } | null>(
      null,
    );
  const [confirmDelete, setConfirmDelete] = useState<Doc | null>(null);
  const [service, setService] = useState<{
    ocr_ready: boolean;
    ai_ready: boolean;
    real_uploads: boolean;
    demo: boolean;
  } | null>(null);
  const notice = useCallback((message: string) => {
    setToast(message);
  }, []);
  const sessionEpoch = useRef(0);
  const refresh = useCallback(async () => {
    const epoch = sessionEpoch.current;
    const w = await api<Workspace>("/workspace");
    if (epoch === sessionEpoch.current) setData(w);
  }, []);
  useEffect(() => {
    let active = true;
    api<{ user: User; csrf: string }>("/auth/me")
      .then((v) => {
        if (active) {
          setCsrf(v.csrf);
          setUser(v.user);
        }
      })
      .catch((e) => {
        if (active && !(e instanceof APIError && e.status === 401))
          setError(e.message);
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);
  useEffect(() => {
    if (!user) return;
    refresh().catch((e) => setError(e.message));
  }, [user, refresh]);
  useEffect(() => {
    if (!toast) return;
    const t = setTimeout(() => setToast(""), 4500);
    return () => clearTimeout(t);
  }, [toast]);
  const processing = data.documents.some((d) =>
    ["queued", "processing"].includes(d.status),
  );
  useEffect(() => {
    if (!user || !processing) return;
    const t = setInterval(
      () => refresh().catch((e) => setError(e.message)),
      1800,
    );
    return () => clearInterval(t);
  }, [user, processing, refresh]);
  useEffect(() => {
    if (!reviewDoc) {
      setSource(null);
      return;
    }
    let active = true;
    setSource(null);
    api<Source>("/documents/" + reviewDoc)
      .then((s) => {
        if (active) setSource(s);
      })
      .catch((e) => {
        if (active) setError(e.message);
      });
    return () => {
      active = false;
    };
  }, [reviewDoc, data.documents.find((d) => d.id === reviewDoc)?.status]);
  useEffect(() => {
    if (page === "settings")
      api<typeof service>("/settings")
        .then(setService)
        .catch((e) => setError(e.message));
  }, [page]);
  function navigate(p: Page) {
    setPage(p);
    setReviewDoc(null);
    setReviewFact(null);
    setError("");
  }
  function openReview(id: string, factId?: string) {
    setPage("documents");
    setReviewDoc(id);
    const pendingRelative = data.facts.find(
      (f) => f.document_id === id && f.status === "pending" && f.schedule_basis && f.scheduled_date,
    );
    setReviewFact(factId || pendingRelative?.id || null);
    setNote("");
    if (!factId && data.documents.find((d) => d.id === id)?.status === "ready")
      void recognizeSchedules(id, false);
  }
  async function recognizeSchedules(id: string, showEmpty: boolean) {
    await action(async () => {
      const result = await api<{ added: number; fact_ids: string[] }>(
        "/documents/" + id + "/recognize-schedules",
        { method: "POST" },
      );
      if (result.fact_ids[0]) setReviewFact(result.fact_ids[0]);
      if (result.added)
        notice(`补充识别了 ${result.added} 条时间安排，请逐条核对日期与时间。`);
      else if (showEmpty)
        notice("没有找到新的可核对时间安排；原有事项未被修改。");
    });
  }
  async function action(fn: () => Promise<unknown>, success?: string) {
    setBusy(true);
    setError("");
    try {
      await fn();
      await refresh();
      if (success) notice(success);
    } catch (e) {
      if (e instanceof TypeError) {
        await refresh().catch(() => undefined);
        notice("连接等待已结束，已刷新最新处理状态。");
      } else {
        setError((e as Error).message);
      }
    } finally {
      setBusy(false);
    }
  }
  function sourceForTask(task: Task) {
    const f = data.facts.find((f) => f.id === task.fact_id);
    if (f) openReview(f.document_id, f.id);
  }
  const pending = data.facts.filter((f) => f.status === "pending");
  const activeTasks = data.tasks.filter((t) => t.active);
  const upcoming = activeTasks.filter(
    (t) => t.status === "pending" && t.due_date >= today(),
  );
  const next = upcoming[0];
  const dayTasks = activeTasks.filter((t) => t.due_date === selected);
  const docFacts = data.facts.filter((f) => f.document_id === reviewDoc);
  const batchFacts = (reviewDoc ? docFacts : pending).filter(
    (f) => f.status === "pending" && !f.conflict,
  );
  async function confirmBatch() {
    await action(
      () =>
        api("/facts/confirm-batch", {
          method: "POST",
          body: JSON.stringify({
            items: batchFacts
              .slice(0, 200)
              .map((f) => ({ id: f.id, version: f.version })),
          }),
        }),
      "资料已批量确认，日期明确的安排已加入照护日程。",
    );
  }
  const currentFact =
    docFacts.find((f) => f.id === reviewFact) ||
    docFacts.find((f) => f.status === "pending") ||
    docFacts[0];
  const reviewDocument = data.documents.find((d) => d.id === reviewDoc);
  useEffect(() => {
    setReportDate(reviewDocument?.report_date || "");
  }, [reviewDocument?.id, reviewDocument?.report_date]);
  useEffect(() => {
    setFactValue(currentFact?.value || "");
    setScheduleDate(currentFact?.scheduled_date || "");
    setScheduleTime(currentFact?.scheduled_time || "");
    setScheduleEndDate(currentFact?.scheduled_end_date || "");
    setScheduleEndTime(currentFact?.scheduled_end_time || "");
  }, [currentFact?.id, currentFact?.version]);
  async function review(status: string) {
    if (!currentFact) return;
    await action(
      async () => {
        await api("/facts/" + currentFact.id, {
          method: "PATCH",
          body: JSON.stringify({
            status,
            version: currentFact.version,
            note,
            value: factValue.trim(),
            scheduled_date: scheduleDate || null,
            scheduled_time: scheduleTime || null,
            scheduled_end_date: scheduleEndDate || null,
            scheduled_end_time: scheduleEndTime || null,
          }),
        });
        setReviewFact(null);
        setNote("");
      },
      status === "confirmed"
        ? "核对结果已保存，照护计划已同步。"
        : "核对结果已保存。",
    );
  }
  async function saveFactText() {
    if (!currentFact || !factValue.trim()) return;
    await action(
      () =>
        api("/facts/" + currentFact.id, {
          method: "PATCH",
          body: JSON.stringify({
            status: currentFact.status,
            version: currentFact.version,
            note: currentFact.note,
            value: factValue.trim(),
          }),
        }),
      "识别内容已保存。",
    );
  }
  async function saveReportDate() {
    if (!reviewDoc || !reportDate) return;
    await action(
      () =>
        api("/documents/" + reviewDoc + "/report-date", {
          method: "PATCH",
          body: JSON.stringify({ report_date: reportDate }),
        }),
      "报告日期已保存。",
    );
  }
  async function updateTask(task: Task, status: string) {
    await action(
      () =>
        api("/tasks/" + task.id, {
          method: "PATCH",
          body: JSON.stringify({ status, version: task.version }),
        }),
      "任务状态已保存。",
    );
  }
  async function download(id: string, name: string) {
    try {
      const r = await fetch("/api/documents/" + id + "/file", {
        credentials: "same-origin",
      });
      if (!r.ok) throw new Error("原文件暂不可用。");
      const url = URL.createObjectURL(await r.blob());
      const a = document.createElement("a");
      a.href = url;
      a.download = name;
      a.click();
      setTimeout(() => URL.revokeObjectURL(url), 30000);
    } catch (e) {
      setError((e as Error).message);
    }
  }
  function resetWorkspace() {
    sessionEpoch.current++;
    setCsrf("");
    setUser(null);
    setData(empty);
    setPage("home");
    setReviewDoc(null);
    setReviewFact(null);
    setSource(null);
    setReport(null);
    setConfirmDelete(null);
    setUploadOpen(false);
    setNote("");
    setFactValue("");
    setReportDate("");
    setQuery("");
    setService(null);
    setError("");
    setToast("");
  }
  async function logout() {
    try {
      await api("/auth/logout", { method: "POST" });
      resetWorkspace();
    } catch (e) {
      if (e instanceof APIError && e.status === 401) resetWorkspace();
      else setError((e as Error).message);
    }
  }
  const listDocs = data.documents.filter(
    (d) =>
      d.name.toLowerCase().includes(query.toLowerCase()) &&
      (docFilter === "all" ||
        (docFilter === "pending" ? d.pending > 0 : d.status === "failed")),
  );
  const shownTasks = data.tasks.filter(
    (t) =>
      taskFilter === "all" ||
      (taskFilter === "upcoming"
        ? t.active && t.status === "pending"
        : taskFilter === "selected"
          ? t.due_date === selected
          : t.status === "completed"),
  );
  const taskRows = (tasks: Task[]) =>
    tasks.map((t) => (
      <TaskRow
        key={t.id}
        task={t}
        busy={busy}
        onStatus={(s) => void updateTask(t, s)}
        onSource={() => sourceForTask(t)}
      />
    ));
  const docRows = (docs: Doc[], compact = false) =>
    docs.map((d) => (
      <div className="document-row" key={d.id}>
        <button className="document-main" onClick={() => openReview(d.id)}>
          <span className="file-symbol">
            <FileText size={24} />
          </span>
          <span>
            <strong>{d.name}</strong>
            <small>
              {new Date(d.created * 1000).toLocaleDateString("zh-CN")} ·{" "}
              {d.pages ? d.pages + "页" : "待整理"}
              {!compact && " · " + (d.size / 1024).toFixed(1) + " KB"}
            </small>
          </span>
        </button>
        <Badge
          status={d.status === "ready" && d.pending ? "pending" : d.status}
        />
        {["failed", "queued"].includes(d.status) ? (
          <button
            className="text-btn"
            disabled={busy}
            onClick={() =>
              void action(
                () => api("/documents/" + d.id + "/retry", { method: "POST" }),
                "已重新排队。",
              )
            }
          >
            {d.status === "queued" ? "继续整理" : "重试"}
          </button>
        ) : (
          <button
            className="icon-btn"
            aria-label={"查看" + d.name}
            onClick={() => openReview(d.id)}
          >
            <ChevronRight size={19} />
          </button>
        )}
        {!compact && (
          <button
            className="icon-btn"
            aria-label={"删除" + d.name}
            onClick={() => setConfirmDelete(d)}
          >
            <Trash2 size={17} />
          </button>
        )}
        {d.error && <p className="doc-error">{d.error}</p>}
      </div>
    ));
  if (loading)
    return (
      <div className="initial-loading">
        <Ribbon />
        <p>正在打开你的空间…</p>
      </div>
    );
  if (!user)
    return (
      <Auth
        onAuth={(v) => {
          resetWorkspace();
          setCsrf(v.csrf);
          setUser(v.user);
          setError("");
        }}
        error={error}
      />
    );
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <button
          className="brand"
          onClick={() => navigate("home")}
          aria-label="APEX首页"
        >
          <Ribbon strokeWidth={1.9} size={43} />
          <span>
            APEX<small>乳腺患者照护伙伴</small>
          </span>
        </button>
        <nav aria-label="主导航">
          {nav.map((n) => (
            <button
              key={n.key}
              className={page === n.key ? "nav-item active" : "nav-item"}
              onClick={() => navigate(n.key)}
              aria-current={page === n.key ? "page" : undefined}
            >
              <n.icon size={22} />
              {labels[n.key]}
              {n.key === "documents" && pending.length > 0 && (
                <span className="nav-count">{pending.length}</span>
              )}
            </button>
          ))}
          {user.institution_access && (
            <button
              className={
                page === "institution"
                  ? "nav-item active institution-link"
                  : "nav-item institution-link"
              }
              onClick={() => navigate("institution")}
            >
              <Building2 size={22} />
              机构决策
            </button>
          )}
          <button
            className={page === "settings" ? "nav-item active" : "nav-item"}
            onClick={() => navigate("settings")}
          >
            <Settings size={22} />
            个人设置
          </button>
        </nav>
        <div className="sidebar-garden">
          <img src="/art/plant.png" alt="" />
          <p>一步一步，照顾好自己。</p>
        </div>
        <button className="logout nav-item" onClick={() => void logout()}>
          <LogOut size={19} />
          退出空间
        </button>
      </aside>
      <div className="main-shell">
        <header className="topbar">
          <div className="breadcrumb">
            <Home size={18} />
            <span>我的空间</span>
            <ChevronRight size={14} />
            <strong>{labels[page]}</strong>
            {reviewDoc && (
              <>
                <ChevronRight size={14} />
                <span>核对资料</span>
              </>
            )}
          </div>
          <div className="top-actions">
            <button
              className="primary small"
              onClick={() => setUploadOpen(true)}
            >
              <Plus size={19} />
              添加资料
            </button>
            <button className="profile" onClick={() => navigate("settings")}>
              <span className="avatar">{user.name.slice(-1)}</span>
              <span>{user.name}</span>
              <ChevronDown size={14} />
            </button>
            {user.demo && <span className="demo-label">演示资料</span>}
          </div>
        </header>
        <main className={"content " + (page === "chat" ? "chat-content" : "")}>
          {error && (
            <div className="error-banner" role="alert">
              <span>{error}</span>
              <button
                className="icon-btn"
                aria-label="关闭错误提示"
                onClick={() => setError("")}
              >
                <X size={17} />
              </button>
            </div>
          )}
          {page === "home" && (
            <div className="dashboard-grid">
              <div className="dashboard-main">
                <div className="page-title">
                  <div>
                    <h1>
                      {new Date().getHours() < 12
                        ? "上午好"
                        : new Date().getHours() < 18
                          ? "下午好"
                          : "晚上好"}
                      ，{user.name}
                    </h1>
                    <p>
                      今天是{" "}
                      {new Date().toLocaleDateString("zh-CN", {
                        month: "long",
                        day: "numeric",
                        weekday: "long",
                      })}
                    </p>
                  </div>
                </div>
                <section className="welcome">
                  <div>
                    <h2>把今天，照顾好。</h2>
                    <p>每一份资料，每一个安排，都清晰有序。</p>
                  </div>
                  <img src="/art/plant.png" alt="" />
                </section>
                <div className="stats">
                  <button
                    className="stat-card"
                    onClick={() => {
                      const d = data.documents.find((d) => d.pending);
                      d ? openReview(d.id) : navigate("documents");
                    }}
                  >
                    <span className="stat-icon">
                      <FileCheck2 size={25} />
                    </span>
                    <div>
                      <span>待核对资料</span>
                      <strong>
                        {pending.length}
                        <small>项</small>
                      </strong>
                    </div>
                    <ChevronRight size={18} />
                  </button>
                  <button
                    className="stat-card"
                    onClick={() => navigate("care")}
                  >
                    <span className="stat-icon">
                      <CalendarDays size={25} />
                    </span>
                    <div>
                      <span>下一次安排</span>
                      <strong className="date-stat">
                        {next ? shortDate(next.due_date) : "暂无"}
                        <small>{next?.due_time || ""}</small>
                      </strong>
                    </div>
                  </button>
                </div>
                <section className="panel">
                  <div className="section-head">
                    <h2>今日照护</h2>
                    <button
                      className="text-btn"
                      onClick={() => navigate("care")}
                    >
                      全部计划
                      <ChevronRight size={16} />
                    </button>
                  </div>
                  {activeTasks.some((t) => t.due_date === today()) ? (
                    taskRows(activeTasks.filter((t) => t.due_date === today()))
                  ) : (
                    <Empty
                      title="暂无已确认安排"
                      text="你可以查看计划，或继续核对新资料。"
                      action={
                        <button
                          className="outline small"
                          onClick={() => navigate("care")}
                        >
                          查看计划
                        </button>
                      }
                    />
                  )}
                </section>
                <section className="panel recent">
                  <div className="section-head">
                    <h2>最近资料</h2>
                    <button
                      className="text-btn"
                      onClick={() => navigate("documents")}
                    >
                      查看全部
                      <ChevronRight size={16} />
                    </button>
                  </div>
                  {data.documents.length ? (
                    docRows(data.documents.slice(0, 3), true)
                  ) : (
                    <Empty
                      title="从第一份资料开始"
                      text="把检查报告与复诊记录放在一起。"
                      action={
                        <button
                          className="primary small"
                          onClick={() => setUploadOpen(true)}
                        >
                          添加资料
                        </button>
                      }
                    />
                  )}
                </section>
              </div>
              <aside className="right-rail">
                <Calendar
                  month={month}
                  selected={selected}
                  tasks={activeTasks}
                  onMonth={setMonth}
                  onSelect={(d) => {
                    setSelected(d);
                    setTaskFilter("selected");
                  }}
                />
                <div className="panel next-card">
                  <span className="eyebrow">
                    {selected === today()
                      ? "接下来的安排"
                      : shortDate(selected) + "的安排"}
                  </span>
                  {(selected === today() ? next : dayTasks[0]) ? (
                    <>
                      <strong>
                        {shortDate(
                          (selected === today() ? next : dayTasks[0]).due_date,
                        )}{" "}
                        <small>
                          {(selected === today() ? next : dayTasks[0])
                            .due_time || ""}
                        </small>
                      </strong>
                      <p>{(selected === today() ? next : dayTasks[0]).title}</p>
                      <button
                        className="text-btn"
                        onClick={() => {
                          setTaskFilter(
                            selected === today() ? "upcoming" : "selected",
                          );
                          navigate("care");
                        }}
                      >
                        查看详情
                        <ArrowRight size={16} />
                      </button>
                    </>
                  ) : (
                    <p>暂无已确认安排</p>
                  )}
                </div>
                <section className="help-card">
                  <h3>有疑问，慢慢说</h3>
                  <p>
                    从有来源的知识
                    <br />
                    开始了解。
                  </p>
                  <button className="text-btn" onClick={() => navigate("chat")}>
                    去问一问
                    <ArrowRight size={16} />
                  </button>
                  <img src="/art/care-heart.png" alt="" />
                </section>
              </aside>
            </div>
          )}
          {page === "documents" && !reviewDoc && (
            <>
              <div className="page-title">
                <div>
                  <h1>我的档案</h1>
                  <p>把每一份资料，整理成清晰的照护线索。</p>
                </div>
                <button
                  className="outline"
                  onClick={() =>
                    api<{ facts: Fact[]; notice: string }>("/report")
                      .then(setReport)
                      .catch((e) => setError(e.message))
                  }
                >
                  <FileCheck2 size={18} />
                  照护摘要
                </button>
              </div>
              <div className="document-banner">
                <div>
                  <h2>
                    {pending.length
                      ? `${pending.length} 项资料等待你的核对`
                      : "资料与安排，都在这里"}
                  </h2>
                  <p>只有核对确认后的安排，才会加入照护计划。</p>
                  <button
                    className="primary"
                    disabled={busy || !batchFacts.length}
                    onClick={() => void confirmBatch()}
                  >
                    批量确认 {Math.min(batchFacts.length, 200)} 项资料
                  </button>
                  <p>
                    确认所有无冲突的待核对资料；日期明确的安排同步加入日程。
                  </p>
                </div>
                <img src="/art/checklist.png" alt="" />
              </div>
              <div className="filterbar">
                <div className="tabs">
                  {[
                    ["all", "全部资料"],
                    ["pending", "待核对"],
                    ["failed", "需重试"],
                  ].map(([v, l]) => (
                    <button
                      key={v}
                      className={docFilter === v ? "active" : ""}
                      onClick={() => setDocFilter(v)}
                    >
                      {l}
                    </button>
                  ))}
                </div>
                <label className="search">
                  <Search size={18} />
                  <input
                    aria-label="搜索资料"
                    placeholder="搜索资料名称"
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                  />
                </label>
              </div>
              <section className="panel document-list">
                {listDocs.length ? (
                  docRows(listDocs)
                ) : (
                  <Empty
                    title={query ? "没有找到相关资料" : "这里还没有资料"}
                    text={
                      query
                        ? "试试更短的关键词。"
                        : "添加文字文件、照片或扫描件，开始整理。"
                    }
                    action={
                      !query && (
                        <button
                          className="primary"
                          onClick={() => setUploadOpen(true)}
                        >
                          <Plus size={18} />
                          添加资料
                        </button>
                      )
                    }
                  />
                )}
              </section>
            </>
          )}
          {page === "documents" && reviewDoc && (
            <>
              <div className="page-title">
                <div>
                  <button
                    className="text-btn"
                    onClick={() => {
                      setReviewDoc(null);
                      setReviewFact(null);
                    }}
                  >
                    <ArrowLeft size={17} />
                    返回档案
                  </button>
                  <h1>核对资料</h1>
                  <p>确认后，再加入照护计划。</p>
                  <button
                    className="primary"
                    disabled={busy || !batchFacts.length}
                    onClick={() => void confirmBatch()}
                  >
                    批量确认本文件 {Math.min(batchFacts.length, 200)} 项
                  </button>
                </div>
                <div className="review-progress">
                  <strong>
                    {docFacts.filter((f) => f.status !== "pending").length} /{" "}
                    {docFacts.length}
                  </strong>
                  <progress
                    value={
                      docFacts.filter((f) => f.status !== "pending").length
                    }
                    max={docFacts.length || 1}
                  />
                </div>
              </div>
              {data.documents.find((d) => d.id === reviewDoc)?.status ===
                "failed" && (
                <div className="error-banner">
                  {data.documents.find((d) => d.id === reviewDoc)?.error}
                </div>
              )}
              <div className="review-grid">
                <section className="panel source-panel">
                  <div className="section-head">
                    <h2>原始资料</h2>
                    <button
                      className="text-btn"
                      onClick={() =>
                        void download(reviewDoc, source?.name || "资料")
                      }
                    >
                      <Download size={16} />
                      下载原件
                    </button>
                  </div>
                  <p className="source-filename">
                    <FileText size={22} />
                    {source?.name || "正在读取资料…"}
                  </p>
                  {source && (
                    <OriginalPreview
                      key={source.id}
                      id={source.id}
                      name={source.name}
                      page={currentFact?.page || 1}
                    />
                  )}
                  <div className="source-paper">
                    {source?.pages.map((p) => (
                      <section key={p.page}>
                        <small>
                          {p.location}
                          {p.ocr ? " · 请对照原图确认识别结果" : ""}
                        </small>
                        <div className="source-text">
                          {currentFact &&
                          p.page === currentFact.page &&
                          p.text.includes(currentFact.quote) ? (
                            <>
                              {p.text.slice(
                                0,
                                p.text.indexOf(currentFact.quote),
                              )}
                              <mark>{currentFact.quote}</mark>
                              {p.text.slice(
                                p.text.indexOf(currentFact.quote) +
                                  currentFact.quote.length,
                              )}
                            </>
                          ) : (
                            p.text
                          )}
                        </div>
                      </section>
                    ))}
                    {!source && <LoaderCircle className="spin" />}
                  </div>
                </section>
                <section className="panel fact-panel">
                  <div className="section-head">
                    <h2>待核对事项</h2>
                    {reviewDocument?.status === "ready" && (
                      <button
                        className="outline small"
                        disabled={busy}
                        onClick={() => void recognizeSchedules(reviewDoc, true)}
                      >
                        补充识别时间安排
                      </button>
                    )}
                  </div>
                  <div className="report-date-editor">
                    <div className="report-date-heading">
                      <span>当前报告日期</span>
                      <small>
                        {reviewDocument?.report_date
                          ? "已自动识别，可手动修改"
                          : "未自动识别，请手动填写"}
                      </small>
                    </div>
                    <div className="report-date-controls">
                      <input
                        type="date"
                        aria-label="当前报告日期"
                        value={reportDate}
                        onChange={(e) => setReportDate(e.target.value)}
                      />
                      <button
                        className="outline small"
                        disabled={
                          busy ||
                          !reportDate ||
                          reportDate === (reviewDocument?.report_date || "")
                        }
                        onClick={() => void saveReportDate()}
                      >
                        保存日期
                      </button>
                    </div>
                    <p>用于标记这份报告本身，不会自动加入照护日程。</p>
                  </div>
                  {currentFact ? (
                    <>
                      <div className="fact-picker">
                        <label>
                          选择事项
                          <select
                            value={currentFact.id}
                            onChange={(e) => {
                              setReviewFact(e.target.value);
                              setNote("");
                            }}
                          >
                            {docFacts.map((f, i) => (
                              <option key={f.id} value={f.id}>
                                {i + 1}. {f.category} ·{" "}
                                {f.status === "pending"
                                  ? "待核对"
                                  : f.status === "confirmed"
                                    ? "已确认"
                                    : "已排除"}
                              </option>
                            ))}
                          </select>
                        </label>
                      </div>
                      <div className="fact-heading">
                        <span>{currentFact.category}</span>
                        <Badge status={currentFact.status} />
                      </div>
                      {currentFact.scheduled_date && (
                        <h3 className="fact-date">
                          {shortDate(currentFact.scheduled_date)}{" "}
                          {currentFact.scheduled_time || "时间未指定"}
                          {currentFact.scheduled_end_date && (
                            <>
                              {" 至 "}
                              {shortDate(currentFact.scheduled_end_date)}{" "}
                              {currentFact.scheduled_end_time || "时间未指定"}
                            </>
                          )}
                        </h3>
                      )}
                      <div className="recognized-editor">
                        <div className="recognized-heading">
                          <span>识别内容</span>
                          <small>可对照左侧原件直接修改</small>
                        </div>
                        <textarea
                          aria-label="识别内容"
                          maxLength={1200}
                          value={factValue}
                          onChange={(e) => setFactValue(e.target.value)}
                        />
                        <div className="recognized-actions">
                          <small>原始 OCR 摘录会保留，便于后续追溯。</small>
                          <button
                            className="outline small"
                            disabled={
                              busy ||
                              !factValue.trim() ||
                              factValue.trim() === currentFact.value
                            }
                            onClick={() => void saveFactText()}
                          >
                            保存文字
                          </button>
                        </div>
                      </div>
                      <p className="source-hint">
                        <ShieldCheck size={16} />
                        {currentFact.location} · 摘录自原文
                      </p>
                      {!currentFact.scheduled_date &&
                        ["复诊", "检查", "治疗", "用药"].includes(
                          currentFact.category,
                        ) && (
                          <p className="notice-box">
                            这条信息没有明确可执行日期，确认后会保留在档案中，不自动生成日程。
                          </p>
                        )}
                      {currentFact.schedule_basis && (
                        <p className="notice-box">{currentFact.schedule_basis}</p>
                      )}
                      {["复诊", "检查", "治疗", "用药"].includes(
                        currentFact.category,
                      ) && (
                        <div className="schedule-editor">
                          <label className="field">
                            开始日期
                            <input
                              type="date"
                              value={scheduleDate}
                              onChange={(e) => setScheduleDate(e.target.value)}
                            />
                          </label>
                          <label className="field">
                            开始时间
                            <input
                              type="time"
                              value={scheduleTime}
                              onChange={(e) => setScheduleTime(e.target.value)}
                            />
                          </label>
                          <label className="field">
                            结束日期（可选）
                            <input
                              type="date"
                              value={scheduleEndDate}
                              onChange={(e) => setScheduleEndDate(e.target.value)}
                            />
                          </label>
                          <label className="field">
                            结束时间（可选）
                            <input
                              type="time"
                              value={scheduleEndTime}
                              onChange={(e) => setScheduleEndTime(e.target.value)}
                            />
                          </label>
                        </div>
                      )}
                      {currentFact.conflict && (
                        <p className="notice-box">
                          与已有资料中的安排可能不同。请对照两份资料，并填写核对说明。
                        </p>
                      )}
                      <label className="field">
                        核对备注{currentFact.conflict ? "（必填）" : "（可选）"}
                        <textarea
                          maxLength={500}
                          value={note}
                          placeholder="填写需要保留的核对说明…"
                          onChange={(e) => setNote(e.target.value)}
                        />
                      </label>
                      {currentFact.note && (
                        <p className="muted">上次说明：{currentFact.note}</p>
                      )}
                      <div className="review-actions">
                        <button
                          className="primary"
                          disabled={busy || !factValue.trim()}
                          onClick={() => void review("confirmed")}
                        >
                          <CheckCircle2 size={19} />
                          确认并继续
                        </button>
                        <button
                          className="outline"
                          disabled={busy || !factValue.trim()}
                          onClick={() => void review("rejected")}
                        >
                          有误，暂不加入
                        </button>
                        {currentFact.status !== "pending" && (
                          <button
                            className="text-btn"
                            disabled={busy}
                            onClick={() => void review("pending")}
                          >
                            撤回确认，重新核对
                          </button>
                        )}
                      </div>
                    </>
                  ) : (
                    <Empty
                      title="暂时没有可核对事项"
                      text="如果资料仍在处理中，请稍后返回。"
                    />
                  )}
                </section>
              </div>
              <div className="review-summary">
                <span>
                  <CheckCircle2 size={20} />
                  已确认{" "}
                  <b>
                    {docFacts.filter((f) => f.status === "confirmed").length}
                  </b>
                </span>
                <span>
                  <Clock size={20} />
                  待核对{" "}
                  <b>{docFacts.filter((f) => f.status === "pending").length}</b>
                </span>
              </div>
            </>
          )}
          {page === "care" && (
            <>
              <div className="page-title">
                <div>
                  <h1>照护计划</h1>
                  <p>每一个安排，都有确认过的资料作为依据。</p>
                </div>
              </div>
              <div className="care-grid">
                <section>
                  <div className="filterbar">
                    <div className="tabs">
                      {[
                        ["upcoming", "待完成"],
                        ["selected", shortDate(selected)],
                        ["completed", "已完成"],
                        ["all", "全部"],
                      ].map(([v, l]) => (
                        <button
                          className={taskFilter === v ? "active" : ""}
                          key={v}
                          onClick={() => setTaskFilter(v)}
                        >
                          {l}
                        </button>
                      ))}
                    </div>
                  </div>
                  <div className="panel">
                    {shownTasks.length ? (
                      taskRows(shownTasks)
                    ) : (
                      <Empty
                        title="暂无符合条件的安排"
                        text="核对资料中的明确日期后，安排会出现在这里。"
                        action={
                          <button
                            className="outline"
                            onClick={() => navigate("documents")}
                          >
                            去核对资料
                          </button>
                        }
                      />
                    )}
                  </div>
                </section>
                <Calendar
                  month={month}
                  selected={selected}
                  tasks={activeTasks}
                  onMonth={setMonth}
                  onSelect={(d) => {
                    setSelected(d);
                    setTaskFilter("selected");
                  }}
                />
              </div>
            </>
          )}
          {page === "chat" && (
            <Chat
              onError={setError}
              onChanged={refresh}
              onOpenReview={openReview}
            />
          )}
          {page === "settings" && (
            <>
              <div className="page-title">
                <div>
                  <h1>个人设置</h1>
                  <p>你的资料，由你管理。</p>
                </div>
              </div>
              <div className="settings-grid">
                <section className="panel">
                  <h2>我的账户</h2>
                  <div className="account-summary">
                    <span className="avatar large">{user.name.slice(-1)}</span>
                    <div>
                      <h3>{user.name}</h3>
                      <p>
                        {user.demo
                          ? "独立演示空间 · 仅使用虚构或脱敏资料"
                          : "个人照护空间"}
                      </p>
                    </div>
                  </div>
                  <p>
                    档案和任务保存在服务端，页面刷新不会清空。退出后需重新登录。
                  </p>
                  <button className="outline" onClick={() => void logout()}>
                    <LogOut size={18} />
                    退出登录
                  </button>
                </section>
                <section className="panel">
                  <h2>服务与资料</h2>
                  <div className="setting-row">
                    <span>图片与扫描件识别</span>
                    <Badge
                      status={service?.ocr_ready ? "已连接" : "尚未连接"}
                    />
                  </div>
                  <div className="setting-row">
                    <span>智能摘录与问答</span>
                    <Badge
                      status={service?.ai_ready ? "已连接" : "原文整理模式"}
                    />
                  </div>
                  <div className="setting-row">
                    <span>真实资料上传</span>
                    <Badge
                      status={service?.real_uploads ? "已开放" : "尚未开放"}
                    />
                  </div>
                  <p className="muted">
                    服务配置由管理员完成。未连接时，文件处理会保留明确状态，不会显示伪造的识别结果。
                  </p>
                </section>
                <section className="panel danger-panel">
                  <h2>删除账户与资料</h2>
                  <p>
                    此操作会删除当前账户、原始文件、核对记录、对话和照护计划，无法从页面恢复。
                  </p>
                  <DeleteAccount
                    onDeleted={() => {
                      resetWorkspace();
                    }}
                    onError={setError}
                  />
                </section>
              </div>
            </>
          )}
          {page === "institution" && <Institution onError={setError} />}
        </main>
      </div>
      <nav className="mobile-nav" aria-label="手机导航">
        {nav.map((n) => (
          <button
            key={n.key}
            className={page === n.key ? "active" : ""}
            onClick={() => navigate(n.key)}
          >
            <n.icon size={21} />
            <span>
              {n.key === "home"
                ? "首页"
                : n.key === "documents"
                  ? "档案"
                  : n.key === "care"
                    ? "照护"
                    : "问答"}
            </span>
          </button>
        ))}
      </nav>
      {toast && (
        <div className="toast" role="status">
          <CheckCircle2 size={18} />
          {toast}
        </div>
      )}
      {uploadOpen && (
        <UploadModal
          onClose={() => setUploadOpen(false)}
          onDone={async (success, documentId, interrupted) => {
            await refresh();
            if (success && documentId) {
              openReview(documentId);
              notice("资料整理完成，请核对结果。");
            } else if (interrupted) {
              navigate("documents");
              notice("连接等待已结束，资料会继续整理，请查看列表状态。");
            }
          }}
        />
      )}
      {confirmDelete && (
        <Modal title="删除这份资料？" onClose={() => setConfirmDelete(null)}>
          <p>
            “{confirmDelete.name}”及其关联事实和任务将被删除，其他资料不受影响。
          </p>
          <div className="modal-actions">
            <button className="outline" onClick={() => setConfirmDelete(null)}>
              保留资料
            </button>
            <button
              className="primary"
              disabled={busy}
              onClick={() =>
                void action(async () => {
                  await api("/documents/" + confirmDelete.id, {
                    method: "DELETE",
                  });
                  setConfirmDelete(null);
                }, "资料已删除。")
              }
            >
              确认删除
            </button>
          </div>
        </Modal>
      )}
      {report && (
        <Modal title="照护摘要" onClose={() => setReport(null)} wide>
          <p className="muted">{report.notice}</p>
          {report.facts.length ? (
            report.facts.map((f) => (
              <div className="report-fact" key={f.id}>
                <Badge status="confirmed" />
                <h3>{f.category}</h3>
                <p>{f.value}</p>
                <button
                  className="text-btn"
                  onClick={() => {
                    setReport(null);
                    openReview(f.document_id, f.id);
                  }}
                >
                  查看来源
                  <ArrowRight size={15} />
                </button>
              </div>
            ))
          ) : (
            <Empty
              title="还没有已确认资料"
              text="先核对资料，再生成你的摘要。"
            />
          )}
          <button
            className="outline"
            onClick={() => {
              const b = new Blob(
                [
                  report.notice +
                    "\n\n" +
                    report.facts
                      .map(
                        (f) =>
                          `${f.category}\n${f.value}\n来源：${f.document_id} ${f.location}`,
                      )
                      .join("\n\n"),
                ],
                { type: "text/plain;charset=utf-8" },
              );
              const u = URL.createObjectURL(b);
              const a = document.createElement("a");
              a.href = u;
              a.download = "照护摘要.txt";
              a.click();
              setTimeout(() => URL.revokeObjectURL(u), 30000);
            }}
          >
            <Download size={17} />
            导出摘要
          </button>
        </Modal>
      )}
    </div>
  );
}

function Auth({
  onAuth,
  error,
}: {
  onAuth: (v: { user: User; csrf: string }) => void;
  error: string;
}) {
  const [mode, setMode] = useState<"login" | "register">("login"),
    [username, setUsername] = useState(""),
    [password, setPassword] = useState(""),
    [name, setName] = useState(""),
    [busy, setBusy] = useState(false),
    [err, setErr] = useState(error);
  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setErr("");
    try {
      onAuth(
        await api("/auth/" + mode, {
          method: "POST",
          body: JSON.stringify({ username, password, name }),
        }),
      );
    } catch (e) {
      setErr((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="auth-page">
      <div className="auth-art">
        <div className="auth-brand">
          <Ribbon size={40} />
          APEX
        </div>
        <h1>
          把今天，
          <br />
          照顾好。
        </h1>
        <p>让资料有序，让照护清晰。</p>
        <img src="/art/plant.png" alt="珊瑚色水彩植物" />
      </div>
      <section className="auth-card">
        <span className="eyebrow">APEX 照护伙伴</span>
        <h2>{mode === "login" ? "回到你的照护空间" : "建立你的照护空间"}</h2>
        <p className="muted">资料、核对记录与安排，在这里延续。</p>
        <form onSubmit={submit}>
          {mode === "register" && (
            <label className="field">
              怎么称呼你
              <input
                value={name}
                maxLength={40}
                onChange={(e) => setName(e.target.value)}
                autoComplete="nickname"
              />
            </label>
          )}
          <label className="field">
            账户名称
            <input
              required
              minLength={3}
              maxLength={100}
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              autoComplete="username"
              placeholder="英文字母、数字或邮箱格式"
            />
          </label>
          <label className="field">
            密码
            <input
              required
              minLength={10}
              maxLength={128}
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete={
                mode === "login" ? "current-password" : "new-password"
              }
              placeholder="至少10位"
            />
          </label>
          {err && (
            <p className="form-error" role="alert">
              {err}
            </p>
          )}
          <button className="primary full" disabled={busy}>
            {busy ? <LoaderCircle className="spin" size={18} /> : null}
            {mode === "login" ? "登录" : "创建账户"}
          </button>
        </form>
        <button
          className="text-btn auth-switch"
          onClick={() => setMode(mode === "login" ? "register" : "login")}
        >
          {mode === "login" ? "还没有账户？创建账户" : "已有账户？返回登录"}
        </button>
        <div className="auth-demo">
          <span>先了解一下</span>
          <button
            className="outline full"
            disabled={busy}
            onClick={async () => {
              setBusy(true);
              setErr("");
              try {
                onAuth(await api("/auth/demo", { method: "POST" }));
              } catch (e) {
                setErr((e as Error).message);
              } finally {
                setBusy(false);
              }
            }}
          >
            体验独立演示空间
            <ArrowRight size={18} />
          </button>
          <small>仅含虚构资料，与你的个人档案分开。</small>
        </div>
      </section>
    </div>
  );
}

function UploadModal({
  onClose,
  onDone,
}: {
  onClose: () => void;
  onDone: (
    success: boolean,
    documentId?: string,
    interrupted?: boolean,
  ) => Promise<void>;
}) {
  const [files, setFiles] = useState<File[]>([]),
    [busy, setBusy] = useState(false),
    [error, setError] = useState(""),
    [progress, setProgress] = useState(0);
  const input = useRef<HTMLInputElement>(null);
  function choose(values: FileList | null) {
    if (!values) return;
    const list = Array.from(values);
    if (list.some((f) => f.size > 10 * 1024 * 1024)) {
      setError("每个文件不能超过10MB。");
      return;
    }
    if (files.length + list.length > 10) {
      setError("每批最多10个文件。");
      return;
    }
    setFiles((old) => [...old, ...list]);
    setError("");
  }
  async function upload() {
    setBusy(true);
    setError("");
    setProgress(0);
    let completed = 0;
    let lastDocumentId: string | undefined;
    try {
      for (const f of files) {
        const form = new FormData();
        form.append("file", f);
        const uploaded = await api<{ id: string }>("/documents", {
          method: "POST",
          body: form,
        });
        lastDocumentId = uploaded.id;
        completed++;
        setProgress(completed);
      }
      await onDone(true, lastDocumentId);
      onClose();
    } catch (e) {
      const interrupted = e instanceof TypeError;
      setError(
        interrupted
          ? "连接等待已结束，资料可能仍在后台整理。"
          : (e as Error).message,
      );
      setFiles((f) => f.slice(completed));
      await onDone(false, undefined, interrupted);
      if (interrupted) onClose();
    } finally {
      setBusy(false);
    }
  }
  return (
    <Modal
      title="添加新资料"
      onClose={() => {
        if (!busy) onClose();
      }}
    >
      <p className="muted">
        上传后会先整理为待核对事项，不会直接改变照护计划。
      </p>
      <button
        className="dropzone"
        onClick={() => input.current?.click()}
        disabled={busy}
        onDragOver={(e) => e.preventDefault()}
        onDrop={(e) => {
          e.preventDefault();
          if (!busy) choose(e.dataTransfer.files);
        }}
      >
        <UploadCloud size={38} />
        <strong>点击选择，或把文件拖到这里</strong>
        <span>PDF、DOCX、TXT、JPG、PNG、WebP</span>
        <small>每个文件不超过10MB，每批最多10个</small>
      </button>
      <input
        ref={input}
        hidden
        type="file"
        multiple
        accept=".pdf,.docx,.txt,.jpg,.jpeg,.png,.webp"
        onChange={(e) => {
          choose(e.target.files);
          e.target.value = "";
        }}
      />
      <div className="upload-list">
        {files.map((f, i) => (
          <div key={i}>
            <FileText size={18} />
            <span>{f.name}</span>
            <small>{(f.size / 1024).toFixed(0)} KB</small>
            <button
              className="icon-btn"
              disabled={busy}
              aria-label={"移除" + f.name}
              onClick={() => setFiles((v) => v.filter((_, j) => j !== i))}
            >
              <X size={16} />
            </button>
          </div>
        ))}
      </div>
      {error && (
        <p className="form-error" role="alert">
          {error}
        </p>
      )}
      <div className="modal-actions">
        <button className="outline" disabled={busy} onClick={onClose}>
          稍后再说
        </button>
        <button
          className="primary"
          disabled={!files.length || busy}
          onClick={() => void upload()}
        >
          {busy ? (
            <>
              <LoaderCircle className="spin" size={18} />
              正在识别与整理 {progress}/{files.length}
            </>
          ) : (
            <>
              保存并整理
              <ArrowRight size={17} />
            </>
          )}
        </button>
      </div>
    </Modal>
  );
}

function CalendarActionCard({
  action,
  onSaved,
  onOpenReview,
}: {
  action: Fact;
  onSaved: () => Promise<void>;
  onOpenReview: (documentId: string, factId?: string) => void;
}) {
  const [date, setDate] = useState(action.scheduled_date || ""),
    [clock, setClock] = useState(action.scheduled_time || ""),
    [endDate, setEndDate] = useState(action.scheduled_end_date || ""),
    [endClock, setEndClock] = useState(action.scheduled_end_time || ""),
    [busy, setBusy] = useState(false),
    [error, setError] = useState("");
  async function save(status: "confirmed" | "rejected") {
    setBusy(true);
    setError("");
    try {
      await api("/facts/" + action.id, {
        method: "PATCH",
        body: JSON.stringify({
          status,
          version: action.version,
          note: "通过照护 Agent 核对",
          scheduled_date: date || null,
          scheduled_time: clock || null,
          scheduled_end_date: endDate || null,
          scheduled_end_time: endClock || null,
        }),
      });
      await onSaved();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <section className="agent-action-card">
      <div className="agent-action-head">
        <span className="agent-action-kicker">
          <CalendarDays size={15} /> 日历草稿
        </span>
        <Badge status={action.status} />
      </div>
      <strong>{action.value}</strong>
      <p>{action.quote}</p>
      <div className="agent-action-grid">
        <label>
          日期
          <input type="date" value={date} onChange={(e) => setDate(e.target.value)} />
        </label>
        <label>
          时间（可选）
          <input type="time" value={clock} onChange={(e) => setClock(e.target.value)} />
        </label>
        {(endDate || action.scheduled_end_date) && (
          <>
            <label>
              结束日期
              <input type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} />
            </label>
            <label>
              结束时间
              <input type="time" value={endClock} onChange={(e) => setEndClock(e.target.value)} />
            </label>
          </>
        )}
      </div>
      {action.schedule_basis && <small>{action.schedule_basis}</small>}
      {error && <p className="form-error">{error}</p>}
      <div className="agent-action-buttons">
        <button
          className="primary"
          disabled={!date || busy}
          onClick={() => void save("confirmed")}
        >
          <CheckCircle2 size={17} />
          {action.status === "confirmed" ? "更新照护计划" : "确认加入日历"}
        </button>
        {action.status === "pending" && (
          <button className="outline" disabled={busy} onClick={() => void save("rejected")}>
            暂不加入
          </button>
        )}
        <button className="text-btn" onClick={() => onOpenReview(action.document_id, action.id)}>
          查看原始依据
        </button>
      </div>
    </section>
  );
}

function Chat({
  onError,
  onChanged,
  onOpenReview,
}: {
  onError: (e: string) => void;
  onChanged: () => Promise<void>;
  onOpenReview: (documentId: string, factId?: string) => void;
}) {
  const [messages, setMessages] = useState<Message[]>([]),
    [question, setQuestion] = useState(""),
    [attachment, setAttachment] = useState<File | null>(null),
    [busy, setBusy] = useState(false),
    [agentStatus, setAgentStatus] = useState("");
  const bottom = useRef<HTMLDivElement>(null);
  const fileInput = useRef<HTMLInputElement>(null);
  const reloadMessages = useCallback(async () => {
    setMessages(await api<Message[]>("/messages"));
  }, []);
  useEffect(() => {
    reloadMessages().catch((e) => onError(e.message));
  }, [onError, reloadMessages]);
  useEffect(() => {
    bottom.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, busy]);
  async function send(q = question) {
    if ((!q.trim() && !attachment) || busy) return;
    const prompt = q.trim(),
      selectedFile = attachment,
      userId = "pending-user-" + Date.now(),
      answerId = "pending-answer-" + Date.now();
    setBusy(true);
    setQuestion("");
    setAttachment(null);
    setMessages((current) => [
      ...current,
      {
        id: userId,
        role: "user",
        text: [selectedFile ? `上传资料：${selectedFile.name}` : "", prompt]
          .filter(Boolean)
          .join("\n"),
        citations: [],
        status: "supported",
        actions: [],
      },
    ]);
    try {
      if (selectedFile) {
        setAgentStatus("正在识别图片并整理可执行安排…");
        const form = new FormData();
        form.append("file", selectedFile);
        const uploaded = await api<{ id: string }>("/documents", {
          method: "POST",
          body: form,
        });
        await api(`/agent/documents/${uploaded.id}`, {
          method: "POST",
          body: JSON.stringify({
            question: prompt || "请识别资料里的安排并整理成日历草稿。",
          }),
        });
        await Promise.all([reloadMessages(), onChanged()]);
        return;
      }
      setAgentStatus("正在判断是否需要调用日历工具…");
      const routed = await api<{ handled: boolean }>("/agent/calendar", {
        method: "POST",
        body: JSON.stringify({ question: prompt }),
      });
      if (routed.handled) {
        await Promise.all([reloadMessages(), onChanged()]);
        return;
      }
      setAgentStatus("正在核对相关依据…");
      let streamError = "";
      await streamQuestion(prompt, (event) => {
        if (event.type === "delta")
          setMessages((current) =>
            current.some((m) => m.id === answerId)
              ? current.map((m) =>
                  m.id === answerId ? { ...m, text: m.text + event.text } : m,
                )
              : [
                  ...current,
                  {
                    id: answerId,
                    role: "assistant",
                    text: event.text,
                    citations: [],
                    status: "supported",
                    actions: [],
                  },
                ],
          );
        if (event.type === "done")
          setMessages((current) =>
            current.map((m) =>
              m.id === answerId
                ? {
                    ...m,
                    id: event.id,
                    citations: event.citations,
                    status: event.status,
                  }
                : m,
            ),
          );
        if (event.type === "error") streamError = event.message;
      });
      if (streamError) throw new Error(streamError);
      await reloadMessages();
    } catch (e) {
      setMessages((current) =>
        current.filter((m) => m.id !== userId && m.id !== answerId),
      );
      setQuestion(prompt);
      setAttachment(selectedFile);
      onError((e as Error).message);
    } finally {
      setBusy(false);
      setAgentStatus("");
    }
  }
  return (
    <div className="chat-layout">
      <div className="page-title">
        <div>
          <h1>有疑问，慢慢说</h1>
          <p>有来源的知识，陪你做好就诊准备。</p>
        </div>
        <ShieldCheck className="coral" size={28} />
      </div>
      <section className="chat-messages">
        {!messages.length && (
          <div className="chat-welcome">
            <img src="/art/care-heart.png" alt="" />
            <h2>从你关心的问题开始</h2>
            <p>这里帮助理解知识和整理问题，不替代治疗团队。</p>
            <div className="suggestions">
              {[
                "复诊前可以准备哪些问题？",
                "治疗期间疲劳应该记录什么？",
                "如何整理后续随访安排？",
                "根据已确认资料生成规范照护报告",
              ].map((q) => (
                <button
                  className="outline"
                  key={q}
                  onClick={() => void send(q)}
                >
                  {q}
                  <ArrowRight size={16} />
                </button>
              ))}
            </div>
          </div>
        )}
        {messages.map((m) => (
          <div key={m.id} className={"message " + m.role}>
            <div className="message-avatar">
              {m.role === "user" ? "我" : <Heart size={17} />}
            </div>
            <div className="message-body">
              <p>{m.text}</p>
              {m.citations.length > 0 && (
                <div className="citations">
                  <strong>
                    <ShieldCheck size={15} />
                    参考来源
                  </strong>
                  {m.citations.map((c) => (
                    <details key={c.id}>
                      <summary>
                        {c.source_type === "personal"
                          ? `你的资料 · ${c.title}${c.page ? ` · 第${c.page}页` : ""}`
                          : `${c.publisher} · ${c.title}`}
                      </summary>
                      <p>{c.text}</p>
                      {c.source_type === "personal" && c.document_id ? (
                        <a
                          href={`/api/documents/${c.document_id}/file?inline=true`}
                          target="_blank"
                          rel="noreferrer"
                        >
                          打开原始资料 ↗
                        </a>
                      ) : (
                        <a href={c.url} target="_blank" rel="noreferrer">
                          打开来源页面 ↗
                        </a>
                      )}
                      <small>
                        {c.source_type === "personal"
                          ? `核对状态：已确认${c.location ? ` · ${c.location}` : ""}`
                          : `资料库审核标记：${c.reviewed_at}`}
                      </small>
                    </details>
                  ))}
                </div>
              )}
              {(m.actions || []).map((action) => (
                <CalendarActionCard
                  key={action.id}
                  action={action}
                  onOpenReview={onOpenReview}
                  onSaved={async () => {
                    await Promise.all([reloadMessages(), onChanged()]);
                  }}
                />
              ))}
              {m.role === "assistant" && m.status !== "supported" && (
                <span className="badge pending">
                  {m.status === "safety_escalation"
                    ? "请及时联系医疗团队"
                    : "证据不足"}
                </span>
              )}
            </div>
          </div>
        ))}
        {busy && (
          <div className="message assistant">
            <div className="message-avatar">
              <Heart size={17} />
            </div>
            <div className="message-body">
              <LoaderCircle size={18} className="spin" />
              {agentStatus || "正在整理…"}
            </div>
          </div>
        )}
        <div ref={bottom} />
      </section>
      <form
        className="chat-composer"
        onSubmit={(e) => {
          e.preventDefault();
          void send();
        }}
      >
        <input
          ref={fileInput}
          className="visually-hidden"
          type="file"
          accept=".jpg,.jpeg,.png,.webp,.pdf,.docx,.txt"
          onChange={(e) => {
            const file = e.target.files?.[0] || null;
            if (file && file.size > 10 * 1024 * 1024) {
              onError("每个文件不能超过10MB。");
              e.target.value = "";
              return;
            }
            setAttachment(file);
            e.target.value = "";
          }}
        />
        <button
          type="button"
          className="chat-attach"
          aria-label="上传病历图片"
          disabled={busy}
          onClick={() => fileInput.current?.click()}
        >
          <ImagePlus size={20} />
        </button>
        <div className="chat-input-stack">
          {attachment && (
            <div className="attachment-chip">
              <ImagePlus size={15} />
              <span>{attachment.name}</span>
              <button type="button" aria-label="移除附件" onClick={() => setAttachment(null)}>
                <X size={14} />
              </button>
            </div>
          )}
        <textarea
          aria-label="你的问题"
          placeholder="问问题，或说“明天上午9点复诊，加入日历”…"
          value={question}
          maxLength={1500}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={(e) => {
            if (
              e.key === "Enter" &&
              !e.shiftKey &&
              !e.nativeEvent.isComposing
            ) {
              e.preventDefault();
              void send();
            }
          }}
        />
        </div>
        <button
          className="primary"
          disabled={(!question.trim() && !attachment) || busy}
          aria-label="发送给照护 Agent"
        >
          <Send size={20} />
        </button>
      </form>
      <p className="chat-footnote">
        Agent 只会生成待确认草稿；涉及治疗与用药，请以治疗团队意见为准。
      </p>
    </div>
  );
}
function DeleteAccount({
  onDeleted,
  onError,
}: {
  onDeleted: () => void;
  onError: (s: string) => void;
}) {
  const [open, setOpen] = useState(false),
    [confirm, setConfirm] = useState(""),
    [busy, setBusy] = useState(false);
  return (
    <>
      <button className="outline danger" onClick={() => setOpen(true)}>
        <Trash2 size={17} />
        删除账户与全部资料
      </button>
      {open && (
        <Modal title="删除账户与全部资料" onClose={() => setOpen(false)}>
          <p>此操作无法撤销。输入“删除”确认。</p>
          <input
            aria-label="输入删除确认"
            value={confirm}
            onChange={(e) => setConfirm(e.target.value)}
          />
          <div className="modal-actions">
            <button className="outline" onClick={() => setOpen(false)}>
              取消
            </button>
            <button
              className="primary"
              disabled={confirm !== "删除" || busy}
              onClick={async () => {
                setBusy(true);
                try {
                  await api("/account", { method: "DELETE" });
                  onDeleted();
                } catch (e) {
                  onError((e as Error).message);
                } finally {
                  setBusy(false);
                }
              }}
            >
              永久删除
            </button>
          </div>
        </Modal>
      )}
    </>
  );
}
