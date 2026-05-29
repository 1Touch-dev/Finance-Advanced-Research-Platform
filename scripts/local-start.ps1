# Start full stack locally without Docker (SQLite + optional Redis worker).
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

& "$Root\scripts\local-stop.ps1" | Out-Null
Start-Sleep -Seconds 2

if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Write-Host "Created .env from .env.example" -ForegroundColor Yellow
}

$envVars = @{}
Get-Content ".env" | ForEach-Object {
    if ($_ -match '^\s*#' -or $_ -match '^\s*$') { return }
    $n, $v = $_ -split '=', 2
    if ($n -and $null -ne $v) {
        $val = $v.Trim()
        Set-Item -Path "env:$n" -Value $val
        $envVars[$n.Trim()] = $val
    }
}

if (-not $env:DATABASE_URL) { $env:DATABASE_URL = "sqlite:///./local.db" }

Write-Host "Installing Python dependencies..." -ForegroundColor Cyan
Set-Location "$Root\apps\api"
pip install -e . -q
pip install -e "$Root\packages\finance" -q

Write-Host "Installing Node apps (web, admin, worker)..." -ForegroundColor Cyan
foreach ($app in @("web", "admin", "worker")) {
    Set-Location "$Root\apps\$app"
    if (-not (Test-Path "node_modules")) { npm install --no-audit --no-fund 2>&1 | Out-Null }
}

function Start-NpmApp {
    param([string]$Dir, [hashtable]$ExtraEnv, [string]$Label, [string]$LogName)
    $logs = "$Root\.local-logs"
    New-Item -ItemType Directory -Force -Path $logs | Out-Null
    $logFile = "$logs\$LogName.log"
    $envLines = ($ExtraEnv.GetEnumerator() | ForEach-Object { "set `"$($_.Key)=$($_.Value)`"" }) -join " && "
    $cmd = if ($envLines) { "$envLines && npm start" } else { "npm start" }
    $cmd = "$cmd > `"$logFile`" 2>&1"
    Write-Host "Starting $Label ..." -ForegroundColor Cyan
    return Start-Process -FilePath "cmd.exe" `
        -ArgumentList "/c", $cmd `
        -WorkingDirectory $Dir `
        -WindowStyle Minimized `
        -PassThru
}

Write-Host "Starting API on http://127.0.0.1:3001 (DB: $($env:DATABASE_URL)) ..." -ForegroundColor Cyan
$apiProc = Start-Process -FilePath "cmd.exe" -ArgumentList "/c", `
    "set DATABASE_URL=$($env:DATABASE_URL) && set JWT_SECRET=$($env:JWT_SECRET) && python -m uvicorn app.main:app --host 127.0.0.1 --port 3001" `
    -WorkingDirectory "$Root\apps\api" `
    -WindowStyle Hidden `
    -PassThru

Start-Sleep -Seconds 5

$ok = $false
for ($i = 0; $i -lt 40; $i++) {
    try {
        $r = Invoke-WebRequest -Uri "http://127.0.0.1:3001/health" -UseBasicParsing -TimeoutSec 2
        if ($r.StatusCode -eq 200) { $ok = $true; break }
    } catch { Start-Sleep -Seconds 1 }
}
if (-not $ok) {
    Write-Host "API failed to start. Check apps\api\local.db permissions or run manually:" -ForegroundColor Red
    Write-Host "  cd apps\api && python -m uvicorn app.main:app --port 3001" -ForegroundColor Gray
    exit 1
}

Write-Host "Bootstrapping database..." -ForegroundColor Cyan
try {
    Invoke-WebRequest -Uri "http://127.0.0.1:3001/bootstrap" -Method POST -UseBasicParsing -TimeoutSec 30 | Out-Null
} catch {
    Write-Host "Bootstrap warning: $($_.Exception.Message) (API may still be usable)" -ForegroundColor Yellow
}

$webProc = Start-NpmApp -Dir "$Root\apps\web" -ExtraEnv @{ NEXT_PUBLIC_API_URL = "http://localhost:3001" } -Label "Web http://localhost:3000" -LogName "web"
$adminProc = Start-NpmApp -Dir "$Root\apps\admin" -ExtraEnv @{
    PORT = "3002"
    BROWSER = "none"
    HOST = "0.0.0.0"
    NODE_OPTIONS = "--openssl-legacy-provider"
} -Label "Admin http://localhost:3002" -LogName "admin"

$workerPid = $null
$redisUp = (Test-NetConnection -ComputerName localhost -Port 6379 -WarningAction SilentlyContinue).TcpTestSucceeded
if ($redisUp) {
    $w = Start-NpmApp -Dir "$Root\apps\worker" -ExtraEnv @{ REDIS_URL = "redis://127.0.0.1:6379" } -Label "Worker" -LogName "worker"
    $workerPid = $w.Id
} else {
    Write-Host "Skipping worker (Redis not on port 6379)." -ForegroundColor Yellow
}

@{
    api_pid = $apiProc.Id
    web_pid = $webProc.Id
    admin_pid = $adminProc.Id
    worker_pid = $workerPid
    started_at = (Get-Date).ToString("o")
} | ConvertTo-Json | Set-Content "$Root\.local-pids.json"

Write-Host ""
Write-Host "Local stack is running (no Docker):" -ForegroundColor Green
Write-Host "  Web:   http://localhost:3000"
Write-Host "  API:   http://localhost:3001"
Write-Host "  Admin: http://localhost:3002"
Write-Host ""
Write-Host "Stop with: .\scripts\local-stop.ps1" -ForegroundColor Gray
