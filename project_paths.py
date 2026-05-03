from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parent
DATASET_DIR = PROJECT_ROOT / "dataset"
SAVES_DIR = PROJECT_ROOT / "saves"
BENCHMARK_STANDARD_RUNS_DIR = PROJECT_ROOT / "experiments" / "benchmark" / "standard_runs"


def path_in_project(*parts: str) -> Path:
    return PROJECT_ROOT.joinpath(*parts)


def ensure_project_dir(*parts: str) -> Path:
    path = path_in_project(*parts)
    path.mkdir(parents=True, exist_ok=True)
    return path
