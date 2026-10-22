#!/usr/bin/env pwsh
# Milestone 1 Quick Health Check
# Run: .\check-milestone-1.ps1

$errors = @()
$successes = @()

Write-Host "`n=== Milestone 1 Health Check ===" -ForegroundColor Cyan

# 1. Containers running?
Write-Host "`n[1/8] Checking containers..." -NoNewline
$ps = docker compose ps --format "table {{.Names}}`t{{.Status}}" 2>$null
if ($ps -match "archive_api" -and $ps -match "archive_qdrant" -and $ps -match "archive_ollama") {
    Write-Host " OK" -ForegroundColor Green
    $successes += "Containers running"
} else {
    Write-Host " FAIL" -ForegroundColor Red
    $errors += "Containers not all running"
}

# 2. API health endpoint?
Write-Host "[2/8] Checking /api/health endpoint..." -NoNewline
try {
    $health = curl -s http://127.0.0.1:8080/api/health | ConvertFrom-Json
    Write-Host " OK" -ForegroundColor Green
    $successes += "API responding"
}
catch {
    Write-Host " FAIL" -ForegroundColor Red
    $errors += "API unreachable on port 8080"
}

# 3. Qdrant reachable?
Write-Host "[3/8] Checking Qdrant on :6333..." -NoNewline
try {
    $qhealth = curl -s http://127.0.0.1:6333/health
    Write-Host " OK" -ForegroundColor Green
    $successes += "Qdrant healthy"
}
catch {
    Write-Host " FAIL" -ForegroundColor Red
    $errors += "Qdrant unreachable on port 6333"
}

# 4. Ollama reachable?
Write-Host "[4/8] Checking Ollama on :11434..." -NoNewline
try {
    $ohealth = curl -s http://127.0.0.1:11434/api/tags
    Write-Host " OK" -ForegroundColor Green
    $successes += "Ollama reachable"
}
catch {
    Write-Host " WAIT" -ForegroundColor Yellow
    $errors += "Ollama still pulling image"
}

# 5. DB initialized?
Write-Host "[5/8] Checking SQLite ledger..." -NoNewline
try {
    docker exec archive_api python -m app.db 2>&1 | Out-Null
    Write-Host " OK" -ForegroundColor Green
    $successes += "Database initialized"
}
catch {
    Write-Host " FAIL" -ForegroundColor Red
    $errors += "Database initialization failed"
}

# 6. Network OK?
Write-Host "[6/8] Checking Docker network..." -NoNewline
$net = docker network inspect archive_net 2>$null | ConvertFrom-Json
if ($net -and $net.Containers.Count -ge 2) {
    Write-Host " OK" -ForegroundColor Green
    $successes += "Network healthy"
}
else {
    Write-Host " FAIL" -ForegroundColor Red
    $errors += "Network issue"
}

# 7. Volumes OK?
Write-Host "[7/8] Checking volumes..." -NoNewline
$vols = docker volume ls --format "table {{.Name}}" | Select-String "archive_"
if ($vols.Count -ge 2) {
    Write-Host " OK" -ForegroundColor Green
    $successes += "Volumes configured"
}
else {
    Write-Host " FAIL" -ForegroundColor Red
    $errors += "Volume mounts missing"
}

# 8. API docs accessible?
Write-Host "[8/8] Checking Swagger UI..." -NoNewline
try {
    $docs = curl -s http://127.0.0.1:8080/docs
    if ($docs) {
        Write-Host " OK" -ForegroundColor Green
        $successes += "Swagger UI available"
    }
}
catch {
    Write-Host " WAIT" -ForegroundColor Yellow
    $errors += "Swagger UI not yet accessible"
}

# Summary
Write-Host "`n=== Summary ===" -ForegroundColor Cyan
Write-Host "Passed: $($successes.Count)" -ForegroundColor Green
Write-Host "Issues: $($errors.Count)" -ForegroundColor Red

if ($errors.Count -eq 0) {
    Write-Host "`n✓ MILESTONE 1 READY!" -ForegroundColor Green
    Write-Host "All criteria passed. Ready for Milestone 2.`n"
}
else {
    Write-Host "`n⏳ Still waiting..." -ForegroundColor Yellow
    $errors | ForEach-Object { Write-Host "  - $_" }
    Write-Host ""
}
