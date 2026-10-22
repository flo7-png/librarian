# sync-main.ps1 - canonical pre-work sync for the Librarian repository.
# See AGENTS.md "Repository Sync": before ANY work in this repo, sync to the
# latest main branch and confirm the working tree is clean.
#
#   powershell -ExecutionPolicy Bypass -File scripts\sync-main.ps1
#
# Exit codes:
#   0  on latest origin/main, working tree clean - safe to start work
#   1  working tree dirty (or repo has no commits yet) - resolve first
#   2  no 'origin' remote configured - add it: git remote add origin <url>
#   3  git fetch failed
#   4  git checkout main failed
#   5  git pull --ff-only failed
#   6  sync completed but tree is dirty afterwards

$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath (Split-Path -Parent $PSScriptRoot)

# --- 1. Refuse to sync over uncommitted work --------------------------------
$dirty = @(git status --porcelain)
if ($dirty.Count -gt 0) {
    Write-Host 'Working tree is NOT clean:' -ForegroundColor Red
    $dirty | ForEach-Object { Write-Host "  $_" }
    $unborn = $false
    try {
        git rev-parse --verify HEAD 2>$null | Out-Null
        if ($LASTEXITCODE -ne 0) { $unborn = $true }
    } catch {
        $unborn = $true
    }
    Write-Host ''
    if ($unborn) {
        Write-Host 'This repository has no commits yet, so "clean" is impossible.' -ForegroundColor Yellow
        Write-Host 'Resolve with an owner-approved initial commit:'
        Write-Host '  git add -A'
        Write-Host '  git commit -m "chore: initial import"'
    } else {
        Write-Host 'Resolve or stash the above before syncing (never sync over local changes).' -ForegroundColor Yellow
    }
    exit 1
}

# --- 2. origin must be configured -------------------------------------------
$origin = git config --get remote.origin.url
if (-not $origin) {
    Write-Host "No 'origin' remote configured in this repository." -ForegroundColor Yellow
    Write-Host 'Add the remote first:  git remote add origin <url>'
    exit 2
}
Write-Host "origin = $origin"

# --- 3. Fetch and land on latest main (fast-forward only, never force) ------
git fetch origin main
if ($LASTEXITCODE -ne 0) { exit 3 }
git checkout main
if ($LASTEXITCODE -ne 0) { exit 4 }
git pull --ff-only origin main
if ($LASTEXITCODE -ne 0) { exit 5 }

# --- 4. Re-confirm and report ------------------------------------------------
$dirty = @(git status --porcelain)
if ($dirty.Count -gt 0) {
    Write-Host 'Sync finished but left the tree dirty:' -ForegroundColor Red
    $dirty | ForEach-Object { Write-Host "  $_" }
    exit 6
}
git --no-pager log --oneline -1
Write-Host 'OK: on main synced with origin/main, working tree clean.' -ForegroundColor Green
exit 0
