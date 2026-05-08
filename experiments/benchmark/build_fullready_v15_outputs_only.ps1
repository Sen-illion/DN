param(
    [string]$PythonExe = "D:\Projects\DN\.venv\Scripts\python.exe",
    [string]$RepoRoot = "D:\Projects\DN",
    [string]$NormalOutput = "benchmark_v15_fullready_nextturn_normal20.json",
    [string]$PregenOutput = "benchmark_v15_fullready_nextturn_pregen60s20.json"
)

$ErrorActionPreference = "Stop"

& $PythonExe "$RepoRoot\experiments\benchmark\build_fullready_nextturn_outputs.py" `
    --normal-run "$RepoRoot\experiments\benchmark\standard_runs\$NormalOutput" `
    --pregen-run "$RepoRoot\experiments\benchmark\standard_runs\$PregenOutput" `
    --first-turn-csv "$RepoRoot\experiments\handoff_2026-04-30_main_experiments\01_main_tables\first_turn_formal20_summary.csv" `
    --next-turn-csv "$RepoRoot\experiments\handoff_2026-04-30_main_experiments\01_main_tables\next_turn_formal20_latency_summary.csv" `
    --summary-json "$RepoRoot\experiments\benchmark\standard_runs\benchmark_v15_fullready_nextturn_20_summary.json" `
    --per-item-csv "$RepoRoot\experiments\benchmark\standard_runs\benchmark_v15_fullready_nextturn_20_table.csv" `
    --strict-main-csv "$RepoRoot\experiments\handoff_2026-04-30_main_experiments\01_main_tables\strict_fullready_main_comparison_2026-05-01_v2.csv"
