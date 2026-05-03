param(
    [string]$PythonExe = "D:\Projects\DN\.venv\Scripts\python.exe",
    [string]$RepoRoot = "D:\Projects\DN",
    [string]$NormalOutput = "benchmark_v15_fullready_nextturn_normal20.json",
    [int]$Limit = 20,
    [int]$Offset = 0,
    [int]$Port = 5003,
    [double]$AbortOnFullReadyOver = 60,
    [int]$FirstClickTimeout = 180,
    [int]$SecondClickTimeout = 60,
    [int]$ImageTimeout = 60
)

$ErrorActionPreference = "Stop"

function Start-DnServer {
    param([int]$ServerPort)

    $bootPath = Join-Path $RepoRoot "logs\fullready_server_normal20_only_boot.py"
    $stdoutPath = Join-Path $RepoRoot "logs\fullready_server_normal20_only.log"
    $stderrPath = Join-Path $RepoRoot "logs\fullready_server_normal20_only.err.log"

    @"
import os, sys
root = r"$RepoRoot"
if root not in sys.path:
    sys.path.insert(0, root)
os.chdir(root)
os.environ["PREGENERATION_ENABLED"] = "true"
os.environ.setdefault("PYTHONUTF8", "1")
os.environ["DN_BENCHMARK_STRICT_FULLREADY"] = "1"
os.environ["GENERATE_OPTION_BLOCK_FOR_IMAGE"] = "1"
os.environ["GENERATE_OPTION_SYNC_BACKFILL_IMAGE"] = "1"
os.environ["GENERATE_OPTION_BLOCK_FOR_IMAGE_MAX_WAIT_SECONDS"] = "45"
os.environ["GENERATE_OPTION_SKIP_SYNC_BACKFILL_AFTER_BLOCK_TIMEOUT"] = "1"
os.environ["PREGEN_LAYER2_IMAGE_ENABLED"] = "false"
os.environ["PREGEN_IMAGE_CACHE_WRITE_MAX_WAIT_SECONDS"] = "45"
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
    & $PythonExe "$RepoRoot\experiments\benchmark\pregen_read_wait_runner.py" `
        --name benchmark_v15_fullready_nextturn_normal20 `
        --output $NormalOutput `
        --read-wait 0 `
        --limit $Limit `
        --offset $Offset `
        --base-url "http://127.0.0.1:$Port" `
        --full-ready `
        --image-timeout $ImageTimeout `
        --profile fullready_strict `
        --second-click-placeholder-retries 0 `
        --first-click-timeout $FirstClickTimeout `
        --second-click-timeout $SecondClickTimeout `
        --abort-on-full-ready-over $AbortOnFullReadyOver `
        --notes "v15 strict normal20 treats first click as setup with a separate timeout budget, while preserving 60s fail-fast guards for second-click request, scene-image wait, and the measured next-turn full-ready path."
}
finally {
    if ($server) { Stop-ProcessSafe $server }
    Pop-Location
}
