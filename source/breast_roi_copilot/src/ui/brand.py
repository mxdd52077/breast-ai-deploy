"""APEX visual system and an accessible GSAP brand header."""

import streamlit as st

PATIENT_PATHS = {"patient-profile", "patient_report", "patient_tasks", "patient_knowledge"}


def role_for_path(path: str) -> str:
    """Return the product surface associated with a Streamlit URL path."""
    normalized = path.strip("/")
    return "患者陪伴助手" if normalized in PATIENT_PATHS else "机构决策平台"


GLOBAL_CSS = """
<style>
:root {
  --apex-accent: var(--st-primary-color);
  --apex-ink: var(--st-text-color);
  --apex-surface: var(--st-background-color);
  --apex-soft: var(--st-secondary-background-color);
  --apex-border: var(--st-border-color);
  --apex-shadow: color-mix(in srgb, var(--st-text-color) 10%, transparent);
}

.stApp {
  background:
    radial-gradient(circle at 92% 4%, color-mix(in srgb, var(--apex-accent) 7%, transparent), transparent 28rem),
    linear-gradient(180deg, var(--apex-surface), color-mix(in srgb, var(--apex-soft) 34%, var(--apex-surface)));
}

[data-testid="stMainBlockContainer"] {
  max-width: 1180px;
  padding-top: 1.15rem;
  padding-bottom: 5rem;
}

[data-testid="stHeader"] {
  background: color-mix(in srgb, var(--apex-surface) 90%, transparent);
  border-bottom: 1px solid color-mix(in srgb, var(--apex-border) 72%, transparent);
  backdrop-filter: blur(18px) saturate(120%);
}

[data-testid="stSidebar"] {
  border-right: 1px solid var(--apex-border);
}

.apex-role-switch {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: .45rem;
  margin: -.25rem 0 .8rem;
}

.apex-role-switch a {
  min-height: 2.55rem;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  color: var(--apex-ink);
  text-decoration: none;
  font-weight: 650;
  border: 1px solid var(--apex-border);
  border-radius: 10px;
  background: color-mix(in srgb, var(--apex-surface) 70%, transparent);
  transition: transform 180ms cubic-bezier(.16, 1, .3, 1), border-color 180ms ease;
}

.apex-role-switch a:hover {
  color: var(--apex-accent);
  border-color: color-mix(in srgb, var(--apex-accent) 52%, var(--apex-border));
  transform: translateY(-1px);
}

.apex-role-switch a:active {
  transform: translateY(1px) scale(.99);
}

h1, h2, h3 {
  letter-spacing: -0.025em;
  text-wrap: balance;
}

h3 {
  margin-top: 1.5rem;
}

p, li, label {
  line-height: 1.68;
}

[data-testid="stVerticalBlockBorderWrapper"] {
  border-color: color-mix(in srgb, var(--apex-border) 88%, transparent);
  box-shadow: 0 16px 40px -30px var(--apex-shadow);
  transition: transform 240ms cubic-bezier(.16, 1, .3, 1), border-color 240ms ease, box-shadow 240ms ease;
}

[data-testid="stVerticalBlockBorderWrapper"]:hover {
  border-color: color-mix(in srgb, var(--apex-accent) 32%, var(--apex-border));
  box-shadow: 0 22px 48px -32px color-mix(in srgb, var(--apex-accent) 24%, transparent);
}

[data-testid="stMetric"] {
  border-top: 3px solid var(--apex-accent) !important;
  min-height: 7.5rem;
}

[data-testid="stMetricValue"] {
  font-variant-numeric: tabular-nums;
  letter-spacing: -0.045em;
}

[data-testid="stAlert"] {
  border: 1px solid color-mix(in srgb, var(--apex-border) 82%, transparent);
  border-left: 4px solid var(--apex-accent);
  box-shadow: none;
}

.stButton > button,
.stLinkButton > a,
[data-testid="stFormSubmitButton"] > button {
  min-height: 2.75rem;
  font-weight: 650;
  letter-spacing: -0.01em;
  white-space: nowrap;
  transition: transform 180ms cubic-bezier(.16, 1, .3, 1), box-shadow 180ms ease, border-color 180ms ease;
}

.stButton > button:hover,
.stLinkButton > a:hover,
[data-testid="stFormSubmitButton"] > button:hover {
  transform: translateY(-1px);
  box-shadow: 0 10px 24px -16px color-mix(in srgb, var(--apex-accent) 52%, transparent);
}

.stButton > button:active,
.stLinkButton > a:active,
[data-testid="stFormSubmitButton"] > button:active {
  transform: translateY(1px) scale(.99);
}

button:focus-visible,
a:focus-visible,
input:focus-visible,
textarea:focus-visible {
  outline: 3px solid color-mix(in srgb, var(--apex-accent) 34%, transparent) !important;
  outline-offset: 3px;
}

[data-testid="stFileUploaderDropzone"] {
  border: 1px dashed color-mix(in srgb, var(--apex-accent) 45%, var(--apex-border));
  background: color-mix(in srgb, var(--apex-accent) 4%, var(--apex-soft));
  min-height: 8rem;
}

[data-testid="stDataFrame"] {
  border: 1px solid var(--apex-border);
  border-radius: var(--st-base-radius);
  overflow: hidden;
}

[data-testid="stChatMessage"] {
  border: 1px solid var(--apex-border);
  border-radius: 16px;
  padding: .9rem 1rem;
  margin-bottom: .65rem;
  background: color-mix(in srgb, var(--apex-soft) 62%, transparent);
}

[data-testid="stCaptionContainer"] {
  letter-spacing: .01em;
}

@media (max-width: 768px) {
  [data-testid="stMainBlockContainer"] {
    padding: .8rem 1rem 3rem;
  }

  [data-testid="stHorizontalBlock"] {
    gap: .75rem;
  }

  [data-testid="stMetric"] {
    min-height: 6.5rem;
  }

  .stButton > button,
  .stLinkButton > a,
  [data-testid="stFormSubmitButton"] > button {
    width: 100%;
  }
}

@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    scroll-behavior: auto !important;
    transition-duration: .01ms !important;
    animation-duration: .01ms !important;
    animation-iteration-count: 1 !important;
  }
}
</style>
"""


BRAND_HEADER_HTML = """
<section class="apex-brand" aria-labelledby="apex-page-title">
  <div class="apex-copy">
    <p class="apex-kicker"><span>APEX</span><b aria-hidden="true">/</b><em></em></p>
    <h1 id="apex-page-title"></h1>
    <p class="apex-description"></p>
  </div>
  <div class="apex-signal" aria-hidden="true">
    <i></i><i></i><i></i><i></i>
  </div>
</section>
"""


BRAND_HEADER_CSS = """
:host {
  display: block;
  color: var(--st-text-color);
  font-family: var(--st-font);
}

.apex-brand {
  position: relative;
  display: grid;
  grid-template-columns: minmax(0, 1fr) 240px;
  align-items: end;
  gap: 3rem;
  min-height: 168px;
  margin: 0 0 2rem;
  padding: 1.45rem 0 1.6rem;
  border-bottom: 1px solid var(--st-border-color);
  overflow: hidden;
}

.apex-copy { position: relative; z-index: 1; }
.apex-kicker {
  display: flex;
  align-items: center;
  gap: .65rem;
  margin: 0 0 .85rem;
  color: color-mix(in srgb, var(--st-text-color) 62%, transparent);
  font-size: .72rem;
  font-style: normal;
  font-weight: 700;
  letter-spacing: .13em;
}
.apex-kicker span { color: var(--st-primary-color); }
.apex-kicker b { color: var(--st-border-color); }
.apex-kicker em { font-style: normal; }

h1 {
  max-width: 780px;
  margin: 0;
  color: var(--st-text-color);
  font-family: var(--st-heading-font), var(--st-font);
  font-size: clamp(2.25rem, 5vw, 4.4rem);
  font-weight: 720;
  letter-spacing: -.055em;
  line-height: 1.02;
  text-wrap: balance;
}

.apex-description {
  max-width: 58ch;
  margin: 1rem 0 0;
  color: color-mix(in srgb, var(--st-text-color) 68%, transparent);
  font-size: .96rem;
  line-height: 1.6;
}

.apex-signal {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  align-items: end;
  height: 92px;
  padding-bottom: .4rem;
}
.apex-signal i {
  display: block;
  width: 1px;
  height: var(--h, 52%);
  justify-self: center;
  background: linear-gradient(to top, var(--st-primary-color), transparent);
  transform-origin: bottom;
}
.apex-signal i:nth-child(1) { --h: 34%; }
.apex-signal i:nth-child(2) { --h: 78%; }
.apex-signal i:nth-child(3) { --h: 52%; }
.apex-signal i:nth-child(4) { --h: 100%; }

@media (max-width: 768px) {
  .apex-brand {
    grid-template-columns: 1fr;
    min-height: 142px;
    gap: .5rem;
    padding-top: .8rem;
  }
  h1 { font-size: clamp(2.15rem, 12vw, 3.25rem); }
  .apex-signal {
    position: absolute;
    right: 0;
    bottom: 0;
    width: 84px;
    height: 42px;
    opacity: .56;
  }
  .apex-description { max-width: calc(100% - 40px); }
}
"""


BRAND_HEADER_JS = """
export default function(component) {
  const { data, parentElement } = component;
  const title = parentElement.querySelector("#apex-page-title");
  const kicker = parentElement.querySelector(".apex-kicker em");
  const description = parentElement.querySelector(".apex-description");
  if (!title || !kicker || !description) return;

  title.textContent = data.title;
  kicker.textContent = data.kicker;
  description.textContent = data.description;

  let cancelled = false;
  let ctx;
  import("https://cdn.jsdelivr.net/npm/gsap@3.13.0/+esm").then(({ gsap }) => {
    if (cancelled || window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    ctx = gsap.context(() => {
      const timeline = gsap.timeline({ defaults: { ease: "power3.out" } });
      timeline
        .from(".apex-kicker", { opacity: 0, y: 10, duration: .45 })
        .from("h1", { opacity: 0, y: 22, duration: .72 }, "-=.2")
        .from(".apex-description", { opacity: 0, y: 12, duration: .5 }, "-=.38")
        .from(".apex-signal i", { scaleY: 0, opacity: 0, stagger: .07, duration: .6 }, "-=.48");
    }, parentElement);
  }).catch(() => {});

  return () => {
    cancelled = true;
    if (ctx) ctx.revert();
  };
}
"""


_BRAND_HEADER = st.components.v2.component(
    "apex_brand_header",
    html=BRAND_HEADER_HTML,
    css=BRAND_HEADER_CSS,
    js=BRAND_HEADER_JS,
)


def header_content(role: str, title: str) -> dict[str, str]:
    if role == "患者陪伴助手":
        return {
            "kicker": "PATIENT CARE NAVIGATOR",
            "title": title,
            "description": "把病历变成清晰的照护线索，让每一项安排都有来源、确认和下一步。",
        }
    return {
        "kicker": "SCREENING DECISION INTELLIGENCE",
        "title": title,
        "description": "把医院数据、循证依据和确定性模型连成一条可审计的决策路径。",
    }


def inject_global_styles() -> None:
    st.html(GLOBAL_CSS)


def render_brand_header(role: str, title: str) -> None:
    _BRAND_HEADER(data=header_content(role, title), height="content")
