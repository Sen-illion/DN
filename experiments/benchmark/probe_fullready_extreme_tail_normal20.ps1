param(
    [string]$PythonExe = "D:\Projects\DN\.venv\Scripts\python.exe",
    [string]$RepoRoot = "D:\Projects\DN",
    [int]$Attempts = 3,
    [int]$Limit = 20,
    [double]$AbortOnFullReadyOver = 60
)

$ErrorActionPreference = "Stop"

$outDir = Join-Path $RepoRoot "experiments\benchmark\standard_runs\extreme_tail_probe_normal20"
New-Item -ItemType Directory -Force -Path $outDir | Out-Null

$rows = @()
for ($i = 1; $i -le $Attempts; $i++) {
    $outputName = "benchmark_v15_fullready_nextturn_normal20_probe_attempt_$i.json"
    Write-Host "=== extreme-tail probe attempt $i / $Attempts ==="
    powershell -ExecutionPolicy Bypass -File "$RepoRoot\experiments\benchmark\run_fullready_v15_normal20_only.ps1" `
        -PythonExe $PythonExe `
        -RepoRoot $RepoRoot `
        -NormalOutput $outputName `
        -Limit $Limit `
        -AbortOnFullReadyOver $AbortOnFullReadyOver

    $jsonPath = Join-Path $RepoRoot "experiments\benchmark\standard_runs\$outputName"
    $payload = Get-Content $jsonPath -Raw | ConvertFrom-Json
    $summary = $payload.summary
    $abort = $summary.abort_reason
    $rows += [pscustomobject]@{
        attempt = $i
        aborted = [bool]$summary.aborted
        sample_size = [int]$summary.sample_size
        success_count = [int]($summary.success_count)
        threshold_s = $AbortOnFullReadyOver
        trigger_benchmark_id = if ($abort) { $abort.benchmark_id } else { "" }
        trigger_full_ready_elapsed_s = if ($abort) { $abort.full_ready_elapsed_s } else { "" }
        trigger_ready_mode = if ($abort) { $abort.ready_mode } else { "" }
        trigger_placeholder = if ($abort) { $abort.second_click_placeholder } else { "" }
        output_json = $jsonPath
    }
    Copy-Item $jsonPath (Join-Path $outDir $outputName) -Force
}

$csvPath = Join-Path $outDir "extreme_tail_probe_summary.csv"
$jsonSummaryPath = Join-Path $outDir "extreme_tail_probe_summary.json"
$rows | Export-Csv -NoTypeInformation -Encoding UTF8 $csvPath
$rows | ConvertTo-Json -Depth 5 | Set-Content -Encoding UTF8 $jsonSummaryPath
Write-Host $csvPath
Write-Host $jsonSummaryPath
