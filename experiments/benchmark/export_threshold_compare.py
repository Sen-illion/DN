import csv, json
from pathlib import Path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
base = PROJECT_ROOT / "experiments" / "benchmark" / "standard_runs"
summary50 = json.loads((base / 'benchmark_v10_readwait_50s_8v8_summary.json').read_text(encoding='utf-8'))
summary60 = json.loads((base / 'benchmark_v9_readwait_60s_merged_12v12_summary.json').read_text(encoding='utf-8'))
rows = []
for wait_s, payload in [(50, summary50), (60, summary60)]:
    for group in ('off','on'):
        s = payload['summary'][group]
        rows.append({
            'read_wait_s': wait_s,
            'group': group,
            'sample_size': s['sample_size'],
            'second_click_mean_s': s['second_click']['mean'],
            'second_click_median_s': s['second_click']['median'],
            'second_click_p95_s': s['second_click']['p95'],
            'real_scene_count': s['real_scene_count'],
            'real_scene_rate': s['real_scene_rate'],
            'real_scene_mean_s': s['real_scene_second_click'].get('mean'),
            'real_scene_median_s': s['real_scene_second_click'].get('median'),
        })
out = base / 'benchmark_v10_threshold_50s_vs_60s_table.csv'
with out.open('w', encoding='utf-8-sig', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)
print(out)
