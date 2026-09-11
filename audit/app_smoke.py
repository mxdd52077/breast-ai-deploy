"""Offline Streamlit runtime checks. Does not call external AI or PubMed."""
import json
import os
import sys
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "source/breast_roi_copilot"
sys.path.insert(0, str(SRC))
os.chdir(SRC)
from streamlit.testing.v1 import AppTest
from src.patient_companion.demo_provider import build_demo_case
from src.patient_companion.review import apply_fact_review

results = []
for role in ["institution", "patient"]:
    app = AppTest.from_file(str(SRC/"app.py"),default_timeout=30)
    app.query_params["workspace"] = role
    app.run()
    results.append({"check":f"entry-{role}","exceptions":[x.message for x in app.exception]})

case = build_demo_case("endocrine")
case = apply_fact_review(case,{f.id:"已确认" for f in case.facts})
for e in case.events:
    e.scheduled_date = date.today() - timedelta(days=1)
states = {f"task-{e.id}":"已完成" for e in case.events}

app = AppTest.from_file(str(SRC/"app_pages/patient_tasks.py"),default_timeout=30)
app.session_state["patient_case"] = case
app.session_state["patient_task_status"] = states.copy()
app.run()
texts = [x.value for x in app.markdown]
results.append({"check":"completed-past-task-overdue", "exceptions":[x.message for x in app.exception],
    "reproduced":any("已逾期" in t for t in texts), "badges":[t for t in texts if "已逾期" in t]})

app = AppTest.from_file(str(SRC/"app_pages/patient_profile.py"),default_timeout=30)
app.session_state["patient_case"] = case
app.session_state["patient_task_status"] = states.copy()
with patch("streamlit.page_link", return_value=None):
    # Standalone page lacks the entrypoint's registered navigation; stub only links.
    app.run()
    save = next((b for b in app.button if b.label=="保存核对结果"),None)
    if save:
        save.click().run()
results.append({"check":"review-resave-clears-task-status", "exceptions":[x.message for x in app.exception],
    "reproduced":save is not None and app.session_state["patient_task_status"] == {},
    "harness":"Only streamlit.page_link stubbed; review and session state run unchanged."})

out = ROOT/"deliverables/verification/app-smoke.json"
out.write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding="utf-8")
print(json.dumps(results,ensure_ascii=False,indent=2))
