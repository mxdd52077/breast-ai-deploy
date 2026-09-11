"""Entry point and navigation for Breast ROI Copilot."""

from urllib.parse import urlsplit

import streamlit as st

from src.ui import inject_global_styles, render_brand_header, role_for_path

st.set_page_config(
    page_title="乳腺筛查循证 ROI 智能决策平台",
    page_icon=":material/health_metrics:",
    layout="wide",
)

inject_global_styles()

st.session_state["app_language"] = "中文"

institution_home = st.Page(
    "app_pages/decision_assistant.py",
    title="AI 决策助手",
    icon=":material/assistant:",
    default=True,
)
institution_data = st.Page(
    "app_pages/data_intake.py",
    title="上传与检查",
    icon=":material/upload_file:",
)
institution_evidence = st.Page(
    "app_pages/evidence_value_library.py",
    title="证据与参数",
    icon=":material/library_books:",
)
institution_roi = st.Page(
    "app_pages/roi_simulation.py",
    title="高级 ROI 仿真",
    icon=":material/analytics:",
)
institution_outreach = st.Page(
    "app_pages/risk_prioritization.py",
    title="外展资源优化",
    icon=":material/social_leaderboard:",
)

patient_home = st.Page(
    "app_pages/patient_profile.py",
    title="我的档案",
    icon=":material/folder_shared:",
    url_path="patient-profile",
)
patient_report = st.Page(
    "app_pages/patient_report.py",
    title="照护报告",
    icon=":material/assignment:",
)
patient_tasks = st.Page(
    "app_pages/patient_tasks.py",
    title="照护日历",
    icon=":material/calendar_month:",
)
patient_knowledge = st.Page(
    "app_pages/patient_knowledge.py",
    title="知识问答",
    icon=":material/forum:",
)

current_path = urlsplit(st.context.url).path.strip("/")
requested_workspace = st.query_params.get("workspace")
if requested_workspace == "patient":
    st.session_state.workspace_role = "患者陪伴助手"
elif requested_workspace == "institution":
    st.session_state.workspace_role = "机构决策平台"
elif current_path:
    st.session_state.workspace_role = role_for_path(current_path)
else:
    st.session_state.setdefault("workspace_role", "机构决策平台")
current_role = st.session_state.workspace_role
institution_entry_class = "entry-card is-active" if current_role == "机构决策平台" else "entry-card"
patient_entry_class = "entry-card is-active" if current_role == "患者陪伴助手" else "entry-card"
st.sidebar.html(
    f"""
    <style>
      .entry-panel {{ --ink:#152321; --muted:#687571; --line:#cbd5d1; --paper:#f7f9f8;
        --accent:#b33a48; font-family:'IBM Plex Sans','Noto Sans SC',sans-serif; margin:.2rem 0 1rem; }}
      .entry-eyebrow {{ color:var(--accent); font-size:.68rem; font-weight:700; letter-spacing:.16em; margin:0 0 .2rem; }}
      .entry-title {{ color:var(--ink); font-size:1.05rem; font-weight:700; letter-spacing:-.02em; margin:0 0 .75rem; }}
      .entry-list {{ display:grid; gap:.55rem; }}
      .entry-card {{ position:relative; display:grid; grid-template-columns:2rem 1fr auto; gap:.65rem;
        align-items:center; min-height:4.25rem; padding:.7rem .75rem; color:var(--ink); text-decoration:none;
        border:1px solid var(--line); border-radius:12px; background:rgba(255,255,255,.52);
        transition:transform 160ms ease,border-color 160ms ease,background 160ms ease; overflow:hidden; }}
      .entry-card::before {{ content:''; position:absolute; inset:0 auto 0 0; width:3px; background:transparent; }}
      .entry-card:hover {{ transform:translateY(-1px); border-color:#9eaaa6; background:#fff; }}
      .entry-card:focus-visible {{ outline:3px solid rgba(179,58,72,.22); outline-offset:2px; }}
      .entry-card.is-active {{ border-color:rgba(179,58,72,.38); background:#fff; box-shadow:0 12px 26px -22px #6d1f2a; }}
      .entry-card.is-active::before {{ background:var(--accent); }}
      .entry-index {{ width:2rem; height:2rem; display:grid; place-items:center; border-radius:8px;
        color:var(--muted); background:#e8edeb; font-size:.7rem; font-weight:700; letter-spacing:.04em; }}
      .is-active .entry-index {{ color:#fff; background:var(--accent); }}
      .entry-copy {{ min-width:0; }}
      .entry-copy strong {{ display:block; font-size:.92rem; line-height:1.25; }}
      .entry-copy small {{ display:block; color:var(--muted); font-size:.7rem; line-height:1.35; margin-top:.16rem; }}
      .entry-state {{ color:var(--accent); font-size:.66rem; font-weight:700; }}
      .entry-note {{ color:var(--muted); font-size:.67rem; line-height:1.45; margin:.65rem .1rem 0; }}
    </style>
    <section class="entry-panel">
      <p class="entry-eyebrow">APEX WORKSPACE</p>
      <h2 class="entry-title">选择工作区</h2>
      <nav class="entry-list" aria-label="使用入口">
        <a class="{institution_entry_class}" href="/?workspace=institution">
          <span class="entry-index">01</span>
          <span class="entry-copy"><strong>机构决策平台</strong><small>筛查决策与 ROI 管理</small></span>
          {"<span class='entry-state'>当前</span>" if current_role == "机构决策平台" else ""}
        </a>
        <a class="{patient_entry_class}" href="/?workspace=patient">
          <span class="entry-index">02</span>
          <span class="entry-copy"><strong>患者陪伴助手</strong><small>个人资料与照护追踪</small></span>
          {"<span class='entry-state'>当前</span>" if current_role == "患者陪伴助手" else ""}
        </a>
      </nav>
      <p class="entry-note">两端工作流相互隔离，切换不会改变另一端的数据状态。</p>
    </section>
    """
)

if current_role == "患者陪伴助手":
    pages = {
        "": [patient_home, patient_report, patient_tasks, patient_knowledge],
    }
else:
    pages = {
        "": [
            institution_home,
            institution_data,
            institution_evidence,
            institution_roi,
            institution_outreach,
        ],
    }

page = st.navigation(pages, position="top")

with st.container(key=f"apex-role-content-{current_role}"):
    render_brand_header(current_role, page.title)
    page.run()
