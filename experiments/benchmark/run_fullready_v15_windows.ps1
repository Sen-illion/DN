param(
    [string]$PythonExe = "D:\Projects\DN\.venv\Scripts\python.exe",
    [string]$RepoRoot = "D:\Projects\DN",
    [string]$NormalOutput = "benchmark_v15_fullready_nextturn_normal20.json",
    [string]$PregenOutput = "benchmark_v15_fullready_nextturn_pregen60s20.json",
    [int]$Limit = 20
)

$ErrorActionPreference = "Stop"

function Start-DnServer {
    param(
        [string]$Mode,
        [int]$Port
    )

    $bootPath = Join-Path $RepoRoot "logs\fullready_server_$Mode`_boot.py"
    $stdoutPath = Join-Path $RepoRoot "logs\fullready_server_$Mode.log"
    $stderrPath = Join-Path $RepoRoot "logs\fullready_server_$Mode.err.log"
    $pregenEnabled = "true"

    @"
import os, sys
root = r"$RepoRoot"
if root not in sys.path:
    sys.path.insert(0, root)
os.chdir(root)
os.environ["PREGENERATION_ENABLED"] = "$pregenEnabled"
os.environ.setdefault("PYTHONUTF8", "1")
os.environ["DN_BENCHMARK_STRICT_FULLREADY"] = "1"
os.environ["GENERATE_OPTION_BLOCK_FOR_IMAGE"] = "1"
os.environ["GENERATE_OPTION_SYNC_BACKFILL_IMAGE"] = "1"
os.environ["PREGEN_LAYER2_IMAGE_ENABLED"] = "false"
from game_server import app
app.run(host="127.0.0.1", port=$Port, debug=False, threaded=True)
"@ | Set-Content -Encoding UTF8 $bootPath

    if (Test-Path $stdoutPath) { Remove-Item $stdoutPath -Force }
    if (Test-Path $stderrPath) { Remove-Item $stderrPath -Force }

    $proc = Start-Process $PythonExe -ArgumentList $bootPath -WorkingDirectory $RepoRoot -RedirectStandardOutput $stdoutPath -RedirectStandardError $stderrPath -PassThru -WindowStyle Hidden
    Start-Sleep -Seconds 20
    try {
        Invoke-WebRequest -UseBasicParsing "http://127.0.0.1:$Port/" -TimeoutSec 5 | Out-Null
    } catch {
        throw "Failed to start DN server mode=$Mode on port $Port. See $stderrPath"
    }
    return $proc
}

function Stop-ProcessSafe {
    param([System.Diagnostics.Process]$Process)
    if ($null -ne $Process -and -not $Process.HasExited) {
        Stop-Process -Id $Process.Id -Force
    }
}

Push-Location $RepoRoot
try {
    $sharedServer = Start-DnServer -Mode "shared" -Port 5003
    & $PythonExe "$RepoRoot\experiments\benchmark\pregen_read_wait_runner.py" `
        --name benchmark_v15_fullready_nextturn_normal20 `
        --output $NormalOutput `
        --read-wait 0 `
        --limit $Limit `
        --base-url http://127.0.0.1:5003 `
        --full-ready `
        --image-timeout 240 `
        --profile fullready_strict `
        --second-click-placeholder-retries 0 `
        --notes "v15 strict normal20 keeps pregeneration on with zero dwell time, but benchmark-only strict full-ready flags block for image, sync backfill image, and suppress background main-character contention."
    & $PythonExe "$RepoRoot\experiments\benchmark\pregen_read_wait_runner.py" `
        --name benchmark_v15_fullready_nextturn_pregen60s20 `
        --output $PregenOutput `
        --read-wait 60 `
        --limit $Limit `
        --base-url http://127.0.0.1:5003 `
        --full-ready `
        --image-timeout 240 `
        --profile fullready_pregen60 `
        --second-click-placeholder-retries 0 `
        --notes "v15 strict pregen60s20 keeps the same production pregeneration path and 60-second dwell interval, while benchmark-only strict full-ready flags reduce placeholder and async image fallback long tails."
    Stop-ProcessSafe $sharedServer

    & $PythonExe "$RepoRoot\experiments\benchmark\build_fullready_nextturn_outputs.py" `
        --normal-run "$RepoRoot\experiments\benchmark\standard_runs\$NormalOutput" `
        --pregen-run "$RepoRoot\experiments\benchmark\standard_runs\$PregenOutput" `
        --first-turn-csv "$RepoRoot\experiments\handoff_2026-04-30_main_experiments\01_main_tables\first_turn_formal20_summary.csv" `
        --next-turn-csv "$RepoRoot\experiments\handoff_2026-04-30_main_experiments\01_main_tables\next_turn_formal20_latency_summary.csv" `
        --summary-json "$RepoRoot\experiments\benchmark\standard_runs\benchmark_v15_fullready_nextturn_20_summary.json" `
        --per-item-csv "$RepoRoot\experiments\benchmark\standard_runs\benchmark_v15_fullready_nextturn_20_table.csv" `
        --strict-main-csv "$RepoRoot\experiments\handoff_2026-04-30_main_experiments\01_main_tables\strict_fullready_main_comparison_2026-05-01_v2.csv"
}
finally {
    Pop-Location
}
