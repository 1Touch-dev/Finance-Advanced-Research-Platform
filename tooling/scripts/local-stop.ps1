# Stop processes started by local-start.ps1 (and free ports 3000-3002).
$ErrorActionPreference = "SilentlyContinue"
$Root = Split-Path -Parent $PSScriptRoot
$pidFile = "$Root\.local-pids.json"

if (Test-Path $pidFile) {
    $info = Get-Content $pidFile | ConvertFrom-Json
    foreach ($key in @("api_pid", "web_pid", "admin_pid", "worker_pid")) {
        $id = $info.$key
        if ($id) { Stop-Process -Id $id -Force }
    }
    Remove-Item $pidFile
}

foreach ($port in @(3000, 3001, 3002)) {
    Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue |
        ForEach-Object { Stop-Process -Id $_.OwningProcess -Force }
}

Write-Host "Stopped local stack (ports 3000-3002)." -ForegroundColor Green
