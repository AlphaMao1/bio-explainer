$ErrorActionPreference = "Stop"

$AppRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $AppRoot

Write-Host ""
Write-Host "Bio Explainer 启动器" -ForegroundColor Cyan
Write-Host "应用目录：$AppRoot"
Write-Host ""

if (-not (Get-Command uv -ErrorAction SilentlyContinue)) {
    Write-Host "没有检测到 uv。" -ForegroundColor Red
    Write-Host "请先安装 uv：https://docs.astral.sh/uv/"
    Write-Host "安装完成后，重新双击 start_windows.bat。"
    Write-Host ""
    Read-Host "按回车退出"
    exit 1
}

Write-Host "正在安装或检查依赖..."
uv sync

Write-Host ""
Write-Host "服务即将启动。" -ForegroundColor Green
Write-Host "如果浏览器没有自动打开，请手动访问：http://127.0.0.1:8000"
Write-Host "关闭这个窗口即可停止服务。"
Write-Host ""

Start-Process "http://127.0.0.1:8000"
uv run uvicorn server.main:app --host 127.0.0.1 --port 8000
