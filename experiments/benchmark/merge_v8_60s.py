import json
import statistics
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
base = PROJECT_ROOT / "experiments" / "benchmark" / "standard_runs"
files = {
    "off": [
        base / "benchmark_v7_readwait_off_60s_4.json",
        base / "benchmark_v8_readwait_off_60s_add4.json",
    ],
    "on": [
        base / "benchmark_v7_readwait_on_60s_4.json",
        base / "benchmark_v8_readwait_on_60s_add4.json",
    ],
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
for label, paths in files.items():
    runs = []
    for path in paths:
        payload = json.loads(path.read_text(encoding="utf-8"))
        runs.extend(payload["runs"])
    combined[label] = runs

summary = {}
for label, runs in combined.items():
    second = [r["second_click"]["elapsed_s"] for r in runs if r.get("second_click", {}).get("status") == "success"]
    real_runs = [r for r in runs if r.get("second_click", {}).get("status") == "success" and not r.get("second_click", {}).get("is_placeholder", True)]
    real_second = [r["second_click"]["elapsed_s"] for r in real_runs]
    hits = sum(1 for r in runs if r.get("second_click", {}).get("inferred_cache_result") == "likely_hit")
    summary[label] = {
        "sample_size": len(runs),
        "success_count": sum(1 for r in runs if r.get("second_click", {}).get("status") == "success"),
        "second_click": summarize(second),
        "real_scene_count": len(real_runs),
        "real_scene_rate": round(len(real_runs) / len(runs), 3) if runs else 0.0,
        "real_scene_second_click": summarize(real_second),
        "likely_hit_count": hits,
        "likely_hit_rate": round(hits / len(runs), 3) if runs else 0.0,
    }

paired_rows = []
off_map = {r["benchmark_id"]: r for r in combined["off"]}
on_map = {r["benchmark_id"]: r for r in combined["on"]}
for bid in sorted(set(off_map) & set(on_map)):
    off = off_map[bid]["second_click"]
    on = on_map[bid]["second_click"]
    off_elapsed = off.get("elapsed_s")
    on_elapsed = on.get("elapsed_s")
    row = {
        "benchmark_id": bid,
        "off_elapsed_s": off_elapsed,
        "on_elapsed_s": on_elapsed,
        "off_real": not off.get("is_placeholder", True),
        "on_real": not on.get("is_placeholder", True),
        "faster": "on" if on_elapsed < off_elapsed else ("off" if off_elapsed < on_elapsed else "tie"),
    }
    paired_rows.append(row)

paired_counts = {
    "on_faster": sum(1 for r in paired_rows if r["faster"] == "on"),
    "off_faster": sum(1 for r in paired_rows if r["faster"] == "off"),
    "tie": sum(1 for r in paired_rows if r["faster"] == "tie"),
    "both_real_count": sum(1 for r in paired_rows if r["off_real"] and r["on_real"]),
    "on_faster_when_both_real": sum(1 for r in paired_rows if r["off_real"] and r["on_real"] and r["faster"] == "on"),
    "off_faster_when_both_real": sum(1 for r in paired_rows if r["off_real"] and r["on_real"] and r["faster"] == "off"),
}

out = {
    "source_files": {k: [str(p) for p in v] for k, v in files.items()},
    "experiment": "benchmark_v8_readwait_60s_merged_8v8",
    "summary": summary,
    "paired": {
        "rows": paired_rows,
        "counts": paired_counts,
    },
    "notes": [
        "Merged post-fix 60s runs: v7 first 4 samples + v8 additional 4 samples (offset 4).",
        "real_scene is approximated by second_click.is_placeholder == false.",
        "This merged view is the current best evidence for the one-minute next-click latency question.",
    ],
}
(base / "benchmark_v8_readwait_60s_merged_8v8_summary.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")

lines = [
    "group,sample_size,success_count,real_scene_count,real_scene_rate,likely_hit_rate,second_click_mean_s,second_click_median_s,second_click_p95_s,real_scene_mean_s,real_scene_median_s,real_scene_p95_s"
]
for label in ("off", "on"):
    s = summary[label]
    all_s = s["second_click"]
    real_s = s["real_scene_second_click"]
    lines.append(
        f"{label},{s['sample_size']},{s['success_count']},{s['real_scene_count']},{s['real_scene_rate']},{s['likely_hit_rate']},"
        f"{all_s.get('mean')},{all_s.get('median')},{all_s.get('p95')},{real_s.get('mean')},{real_s.get('median')},{real_s.get('p95')}"
    )
(base / "benchmark_v8_readwait_60s_merged_8v8_table.csv").write_text("\n".join(lines), encoding="utf-8")
print(base / "benchmark_v8_readwait_60s_merged_8v8_summary.json")
print(base / "benchmark_v8_readwait_60s_merged_8v8_table.csv")
