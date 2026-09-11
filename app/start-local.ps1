$ErrorActionPreference = 'Stop'
$apexProjectRoot = Split-Path -Parent $PSScriptRoot
$apexPython = Join-Path $apexProjectRoot '.venv/Scripts/python.exe'
if (-not (Test-Path -LiteralPath $apexPython)) {
    throw '请先按照 app/README.md 创建虚拟环境并安装依赖。'
}
if (-not (Test-Path -LiteralPath (Join-Path $PSScriptRoot 'frontend/dist/index.html'))) {
    throw '请先在 app/frontend 执行 npm ci 和 npm run build。'
}
Set-Location -LiteralPath $apexProjectRoot
Write-Host 'APEX 本地预览：http://127.0.0.1:8000；按 Ctrl+C 停止。'
& $apexPython -m uvicorn app.backend.main:app --host 127.0.0.1 --port 8000
