import argparse
import json
import subprocess
import sys
from pathlib import Path


COMMANDS = {
    "sdm_v2": ["run_sdm_v2.py", "--output_dir", "outputs/image/sdm_v2"],
    "storydiffusion": [
        "run_storydiffusion.py",
        "--output_dir",
        "outputs/image/StoryDiffusion",
        "--prepare_only",
    ],
    "iclora": [
        "run_iclora.py",
        "--output_dir",
        "outputs/image/In-Context-LoRA",
        "--prepare_only",
    ],
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run configured baseline wrappers in sequence.")
    parser.add_argument("--input", default="data/input_samples.jsonl")
    parser.add_argument(
        "--baselines",
        default="sdm_v2,storydiffusion,iclora",
        help="Comma-separated names. Available: " + ", ".join(COMMANDS),
    )
    parser.add_argument("--stop_on_error", action="store_true")
    parser.add_argument("--summary", default="outputs/baseline_run_summary.json")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    script_dir = Path(__file__).resolve().parent
    results = []
    for name in [part.strip() for part in args.baselines.split(",") if part.strip()]:
        if name not in COMMANDS:
            raise SystemExit(f"Unknown baseline '{name}'. Available: {', '.join(COMMANDS)}")
        command = [sys.executable, str(script_dir / COMMANDS[name][0]), "--input", args.input] + COMMANDS[name][1:]
        print("Running:", " ".join(command))
        proc = subprocess.run(command, text=True, capture_output=True)
        result = {
            "baseline": name,
            "command": command,
            "returncode": proc.returncode,
            "stdout": proc.stdout,
            "stderr": proc.stderr,
            "status": "passed" if proc.returncode == 0 else "failed",
        }
        results.append(result)
        if proc.stdout:
            print(proc.stdout.rstrip())
        if proc.stderr:
            print(proc.stderr.rstrip(), file=sys.stderr)
        if proc.returncode != 0 and args.stop_on_error:
            break

    summary_path = Path(args.summary)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote run summary to {summary_path}")
    if any(item["returncode"] != 0 for item in results):
        raise SystemExit(1)


if __name__ == "__main__":
    main()
