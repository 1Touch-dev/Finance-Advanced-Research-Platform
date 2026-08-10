# Start full stack with Docker Compose and bootstrap the API database.
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

Write-Host "Building and starting services..." -ForegroundColor Cyan
docker compose up --build -d
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Write-Host "Waiting for API..." -ForegroundColor Cyan
$ok = $false
for ($i = 0; $i -lt 60; $i++) {
    try {
        $r = Invoke-WebRequest -Uri "http://localhost:3001/health" -UseBasicParsing -TimeoutSec 2
        if ($r.StatusCode -eq 200) { $ok = $true; break }
    } catch { Start-Sleep -Seconds 2 }
}
if (-not $ok) {
    Write-Host "API did not become healthy in time. Check: docker compose logs api" -ForegroundColor Yellow
    exit 1
}

Write-Host "Bootstrapping database..." -ForegroundColor Cyan
Invoke-WebRequest -Uri "http://localhost:3001/bootstrap" -Method POST -UseBasicParsing | Out-Null

Write-Host ""
Write-Host "Stack is up:" -ForegroundColor Green
Write-Host "  Web:   http://localhost:3000"
Write-Host "  API:   http://localhost:3001"
Write-Host "  Admin: http://localhost:3002"
