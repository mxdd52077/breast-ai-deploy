"""Copy approved server-only configuration to the linked Vercel project."""
from __future__ import annotations

import subprocess
from pathlib import Path

from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]
local = dotenv_values(ROOT / "app" / ".env")
values = {
    "SUPABASE_URL": "https://wvnkdfxrzrbcnsjonydy.supabase.co",
    "SUPABASE_STORAGE_BUCKET": "patient-documents",
    "APEX_AUTO_CREATE_DB": "false",
    "APEX_WORKER": "false",
    "APEX_ALLOW_DEMO": "true",
    "APEX_ALLOW_REAL_UPLOADS": "false",
    "APEX_OCR_PROVIDER": "baidu_paddle",
    "APEX_LLM_BASE_URL": "https://api.moonshot.cn/v1",
    "APEX_LLM_MODEL": "kimi-k3",
    "APEX_LLM_REASONING_EFFORT": "low",
    "LANGSMITH_TRACING": "false",
    "LANGCHAIN_TRACING_V2": "false",
}
for key in [
    "BAIDU_OCR_APP_ID",
    "BAIDU_OCR_API_KEY",
    "BAIDU_OCR_SECRET_KEY",
    "APEX_LLM_API_KEY",
]:
    if local.get(key):
        values[key] = str(local[key])

for key, value in values.items():
    result = subprocess.run(
        [
            "npx.cmd",
            "--yes",
            "vercel@59.11.7",
            "env",
            "add",
            key,
            "production",
            "--force",
            "--sensitive",
            "--yes",
        ],
        cwd=ROOT,
        input=value + "\n",
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=90,
    )
    if result.returncode:
        raise SystemExit(f"Failed to configure {key}")
    print(f"configured {key}")
