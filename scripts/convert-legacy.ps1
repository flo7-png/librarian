# Convert legacy Office files (.doc/.xls/.ppt) to modern twins (.docx/.xlsx/.pptx)
# alongside the originals in D:\References. Originals are NEVER modified or deleted.
# List source: D:\AI\librarian\data\legacy-files.json
param()
$ErrorActionPreference = 'Continue'
$ProgressPreference = 'SilentlyContinue'

$root = 'D:\AI\librarian'
$listPath = Join-Path $root 'data\legacy-files.json'
$logPath = Join-Path $root 'logs\convert-legacy.log'
$resultPath = Join-Path $root 'logs\convert-legacy-results.json'
New-Item -ItemType Directory -Path (Split-Path $logPath) -Force | Out-Null

function Log([string]$m) {
    $line = "$(Get-Date -Format 'HH:mm:ss') $m"
    Add-Content -Path $logPath -Value $line
    Write-Output $line
}

$files = Get-Content $listPath -Raw | ConvertFrom-Json
Log "starting conversion of $($files.Count) legacy files"

$results = @()
$word = $null; $excel = $null; $ppt = $null

foreach ($srcItem in $files) {
    $src = ([string]$srcItem).Replace('/', '\')
    if (-not (Test-Path -LiteralPath $src)) {
        $results += [pscustomobject]@{ src = $src; status = 'missing' }
        continue
    }
    $base = [IO.Path]::GetFileNameWithoutExtension($src)
    $ext = [IO.Path]::GetExtension($src).ToLower()
    $outExt = switch ($ext) { '.doc' { '.docx' } '.xls' { '.xlsx' } '.ppt' { '.pptx' } default { $null } }
    if (-not $outExt) { continue }
    $out = [IO.Path]::ChangeExtension($src, $outExt)

    if (Test-Path -LiteralPath $out) {
        $results += [pscustomobject]@{ src = $src; status = 'twin_exists' }
        continue
    }

    try {
        switch ($ext) {
            '.doc' {
                if (-not $word) {
                    $word = New-Object -ComObject Word.Application
                    $word.Visible = $false
                    $word.DisplayAlerts = 0
                    $word.AutomationSecurity = 3
                }
                $d = $word.Documents.Open($src, $false, $true, $false)
                $d.SaveAs2($out, 16)
                $d.Close($false)
            }
            '.xls' {
                if (-not $excel) {
                    $excel = New-Object -ComObject Excel.Application
                    $excel.Visible = $false
                    $excel.DisplayAlerts = $false
                    $excel.AutomationSecurity = 3
                }
                $wb = $excel.Workbooks.Open($src, 0, $true)
                $wb.SaveAs($out, 51)
                $wb.Close($false)
            }
            '.ppt' {
                if (-not $ppt) {
                    $ppt = New-Object -ComObject PowerPoint.Application
                }
                $pres = $ppt.Presentations.Open($src, -1, 0, 0)
                $pres.SaveAs($out, 24)
                $pres.Close()
            }
        }
        if (Test-Path -LiteralPath $out) {
            $results += [pscustomobject]@{ src = $src; status = 'converted' }
            Log "OK   $base$ext"
        } else {
            $results += [pscustomobject]@{ src = $src; status = 'no_output' }
            Log "MISS $base$ext (no file written)"
        }
    }
    catch {
        $results += [pscustomobject]@{ src = $src; status = 'failed'; error = $_.Exception.Message }
        Log "FAIL $base$ext :: $($_.Exception.Message)"
        # Best-effort close of whatever is stuck open
        try { if ($d) { $d.Close($false) } } catch {}; $d = $null
        try { if ($wb) { $wb.Close($false) } } catch {}; $wb = $null
        try { if ($pres) { $pres.Close() } } catch {}; $pres = $null
        # Recreate the app if it looks unhealthy (simple heuristic: retry flag on next file)
        try {
            switch ($ext) {
                '.doc' { if ($word) { $null = $word.Version } }
                '.xls' { if ($excel) { $null = $excel.Version } }
                '.ppt' { if ($ppt) { $null = $ppt.Version } }
            }
        } catch {
            Log "app unhealthy, releasing for recreate"
            try { if ($word) { $word.Quit() } } catch {}
            try { if ($excel) { $excel.Quit() } } catch {}
            try { if ($ppt) { $ppt.Quit() } } catch {}
            $word = $null; $excel = $null; $ppt = $null
        }
    }
}

# Release all COM instances we created
try { if ($word) { $word.Quit() } } catch {}
try { if ($excel) { $excel.Quit() } } catch {}
try { if ($ppt) { $ppt.Quit() } } catch {}
foreach ($app in @($word, $excel, $ppt)) {
    if ($app) { try { [void][Runtime.InteropServices.Marshal]::ReleaseComObject($app) } catch {} }
}
[System.GC]::Collect()

$summary = $results | Group-Object status | ForEach-Object { "$($_.Name)=$($_.Count)" }
Log ("done: " + ($summary -join ', '))
$results | ConvertTo-Json -Depth 3 | Set-Content -Path $resultPath -Encoding UTF8
Log "results -> $resultPath"
