import json
import statistics
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
base = PROJECT_ROOT / "experiments" / "benchmark" / "standard_runs"
files = {
    "off": base / "benchmark_v10_readwait_off_50s_8.json",
    "on": base / "benchmark_v10_readwait_on_50s_8.json",
}

def percentile(values, p):
    if not values:
        return None
    ordered = sorted(values)
    if len(ordered) == 1:
        return float(ordered[0])
    idx = (len(ordered) - 1) * p
    lo = int(idx)
    hi = min(lo + 1, len(ordered) - 1)
    if lo == hi:
        return float(ordered[lo])
    frac = idx - lo
    return float(ordered[lo] + (ordered[hi] - ordered[lo]) * frac)

def summarize(values):
    if not values:
        return {"count": 0}
    return {
        "count": len(values),
        "min": round(min(values), 3),
        "max": round(max(values), 3),
        "mean": round(statistics.mean(values), 3),
        "median": round(statistics.median(values), 3),
        "p95": round(percentile(values, 0.95), 3),
    }

combined = {}
for label, path in files.items():
    payload = json.loads(path.read_text(encoding="utf-8"))
    combined[label] = payload["runs"]

summary = {}
for label, runs in combined.items():
    second = [r["second_click"]["elapsed_s"] for r in runs if r.get("second_click", {}).get("status") == "success"]
    real_runs = [r for r in runs if r.get("second_click", {}).get("status") == "success" and not r.get("second_click", {}).get("is_placeholder", True)]
    real_second = [r["second_click"]["elapsed_s"] for r in real_runs]
    summary[label] = {
        "sample_size": len(runs),
        "success_count": sum(1 for r in runs if r.get("second_click", {}).get("status") == "success"),
        "second_click": summarize(second),
        "real_scene_count": len(real_runs),
        "real_scene_rate": round(len(real_runs) / len(runs), 3) if runs else 0.0,
        "real_scene_second_click": summarize(real_second),
        "likely_hit_count": sum(1 for r in runs if r.get("second_click", {}).get("inferred_cache_result") == "likely_hit"),
        "likely_hit_rate": round(sum(1 for r in runs if r.get("second_click", {}).get("inferred_cache_result") == "likely_hit") / len(runs), 3) if runs else 0.0,
    }

paired_rows = []
off_map = {r["benchmark_id"]: r for r in combined["off"]}
on_map = {r["benchmark_id"]: r for r in combined["on"]}
for bid in sorted(set(off_map) & set(on_map)):
    off = off_map[bid]["second_click"]
    on = on_map[bid]["second_click"]
    off_elapsed = off.get("elapsed_s")
    on_elapsed = on.get("elapsed_s")
    paired_rows.append({
        "benchmark_id": bid,
        "off_elapsed_s": off_elapsed,
        "on_elapsed_s": on_elapsed,
        "off_real": not off.get("is_placeholder", True),
        "on_real": not on.get("is_placeholder", True),
        "faster": "on" if on_elapsed < off_elapsed else ("off" if off_elapsed < on_elapsed else "tie"),
    })

out = {
    "experiment": "benchmark_v10_readwait_50s_8v8",
    "source_files": {k: str(v) for k, v in files.items()},
    "summary": summary,
    "paired": {
        "rows": paired_rows,
        "counts": {
            "on_faster": sum(1 for r in paired_rows if r["faster"] == "on"),
            "off_faster": sum(1 for r in paired_rows if r["faster"] == "off"),
            "tie": sum(1 for r in paired_rows if r["faster"] == "tie"),
            "both_real_count": sum(1 for r in paired_rows if r["off_real"] and r["on_real"]),
            "on_faster_when_both_real": sum(1 for r in paired_rows if r["off_real"] and r["on_real"] and r["faster"] == "on"),
            "off_faster_when_both_real": sum(1 for r in paired_rows if r["off_real"] and r["on_real"] and r["faster"] == "off"),
        },
    },
    "notes": [
        "50s run is a threshold exploration experiment.",
        "real_scene is approximated by second_click.is_placeholder == false.",
    ],
}
(base / "benchmark_v10_readwait_50s_8v8_summary.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
print(base / "benchmark_v10_readwait_50s_8v8_summary.json")
