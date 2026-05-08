param(
    [string]$PythonExe = "D:\Projects\DN\.venv\Scripts\python.exe",
    [string]$RepoRoot = "D:\Projects\DN",
    [int]$Port = 5005,
    [ValidateSet("smoke3", "formal20")]
    [string]$Mode = "smoke3",
    [string]$BenchmarkFile = "D:\Projects\DN\baselines\subsets\dn_style_formal20.json",
    [int]$TurnCount = 4,
    [double]$ReadWait = 60,
    [int]$FirstClickTimeout = 180,
    [int]$TurnClickTimeout = 180,
    [int]$ImageTimeout = 120
)

$ErrorActionPreference = "Stop"

if ($Mode -eq "smoke3" -and $ReadWait -eq 60) {
    $ReadWait = 10
}

$limit = if ($Mode -eq "smoke3") { 3 } else { 20 }
$runTag = if ($Mode -eq "smoke3") { "smoke3" } else { "formal20" }

function Start-DnServer {
    param([int]$ServerPort)

    $bootPath = Join-Path $RepoRoot "logs\pregendepth_v16_server_boot.py"
    $stdoutPath = Join-Path $RepoRoot "logs\pregendepth_v16_server.log"
    $stderrPath = Join-Path $RepoRoot "logs\pregendepth_v16_server.err.log"

@"
import os, sys
root = r"$RepoRoot"
if root not in sys.path:
    sys.path.insert(0, root)
os.chdir(root)
os.environ["PREGENERATION_ENABLED"] = "true"
os.environ["PREGEN_LAYER2_IMAGE_ENABLED"] = "false"
os.environ["GENERATE_OPTION_BLOCK_FOR_IMAGE"] = "1"
os.environ["GENERATE_OPTION_SYNC_BACKFILL_IMAGE"] = "1"
os.environ["GENERATE_OPTION_BLOCK_FOR_IMAGE_MAX_WAIT_SECONDS"] = "45"
os.environ["GENERATE_OPTION_SKIP_SYNC_BACKFILL_AFTER_BLOCK_TIMEOUT"] = "1"
os.environ["PREGEN_IMAGE_CACHE_WRITE_MAX_WAIT_SECONDS"] = "45"
os.environ["DN_BENCHMARK_PREGEN_SEMANTICS"] = "fixed_path"
os.environ["DN_BENCHMARK_SELECTION_POLICY"] = "first_option"
os.environ.setdefault("PYTHONUTF8", "1")
from game_server import app
app.run(host="127.0.0.1", port=$ServerPort, debug=False, threaded=True)
"@ | Set-Content -Encoding UTF8 $bootPath

    if (Test-Path $stdoutPath) { Remove-Item $stdoutPath -Force }
    if (Test-Path $stderrPath) { Remove-Item $stderrPath -Force }

    $proc = Start-Process $PythonExe -ArgumentList $bootPath -WorkingDirectory $RepoRoot -RedirectStandardOutput $stdoutPath -RedirectStandardError $stderrPath -PassThru -WindowStyle Hidden
    Start-Sleep -Seconds 20
    try {
        Invoke-WebRequest -UseBasicParsing "http://127.0.0.1:$ServerPort/" -TimeoutSec 5 | Out-Null
    } catch {
        throw "Failed to start DN server on port $ServerPort. See $stderrPath"
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
    $server = Start-DnServer -ServerPort $Port
    foreach ($depth in @(1,2,3,4)) {
        $outputName = "benchmark_v16_pregendepth_d${depth}_turn4_rw60_${runTag}.json"
        $datasetPack = "depth_${depth}_${runTag}"
        & $PythonExe "$RepoRoot\experiments\benchmark\pregen_depth_turn4_runner.py" `
            --name "benchmark_v16_pregendepth_d${depth}_turn4_rw60_${runTag}" `
            --output $outputName `
            --benchmark-file $BenchmarkFile `
            --base-url "http://127.0.0.1:$Port" `
            --pregen-depth $depth `
            --turn-count $TurnCount `
            --read-wait $ReadWait `
            --limit $limit `
            --offset 0 `
            --image-timeout $ImageTimeout `
            --image-poll-interval 1.5 `
            --first-click-timeout $FirstClickTimeout `
            --turn-click-timeout $TurnClickTimeout `
            --profile pregen_depth_fixed_path `
            --dataset-root "$RepoRoot\experiments\organized\ablations\02_pregeneration_ablation\datasets" `
            --dataset-pack-name $datasetPack `
            --notes "v16 fixed-path pregen depth=$depth, turn_count=$TurnCount, read_wait=$ReadWait, mode=$Mode"
    }

    if ($Mode -eq "formal20") {
        & $PythonExe "$RepoRoot\experiments\benchmark\build_pregendepth_v16_outputs.py" `
            --d1 "$RepoRoot\experiments\benchmark\standard_runs\benchmark_v16_pregendepth_d1_turn4_rw60_formal20.json" `
            --d2 "$RepoRoot\experiments\benchmark\standard_runs\benchmark_v16_pregendepth_d2_turn4_rw60_formal20.json" `
            --d3 "$RepoRoot\experiments\benchmark\standard_runs\benchmark_v16_pregendepth_d3_turn4_rw60_formal20.json" `
            --d4 "$RepoRoot\experiments\benchmark\standard_runs\benchmark_v16_pregendepth_d4_turn4_rw60_formal20.json" `
            --summary-json "$RepoRoot\experiments\benchmark\standard_runs\benchmark_v16_pregendepth_turn4_formal20_summary.json" `
            --table-csv "$RepoRoot\experiments\benchmark\standard_runs\benchmark_v16_pregendepth_turn4_formal20_table.csv" `
            --paper-table-csv "$RepoRoot\experiments\benchmark\standard_runs\benchmark_v16_pregendepth_turn4_formal20_paper_table.csv"
    }
}
finally {
    if ($server) { Stop-ProcessSafe $server }
    Pop-Location
}
