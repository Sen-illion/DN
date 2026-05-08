import json, statistics, csv
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
base = PROJECT_ROOT / "experiments" / "benchmark" / "standard_runs"
raw70 = json.loads((base / 'benchmark_v13_readwait_70s_8v8_summary.json').read_text(encoding='utf-8'))
off_raw = json.loads((base / 'benchmark_v13_readwait_off_70s_8.json').read_text(encoding='utf-8'))
on_raw = json.loads((base / 'benchmark_v13_readwait_on_70s_8.json').read_text(encoding='utf-8'))

INVALID_BENCHMARK_ID = 'DNQBV1_008'


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
        return {'count': 0}
    return {
        'count': len(values),
        'min': round(min(values), 3),
        'max': round(max(values), 3),
        'mean': round(statistics.mean(values), 3),
        'median': round(statistics.median(values), 3),
        'p95': round(percentile(values, 0.95), 3),
    }

def summarize_runs(runs):
    second = [r['second_click']['elapsed_s'] for r in runs if r.get('second_click', {}).get('status') == 'success']
    real_runs = [r for r in runs if r.get('second_click', {}).get('status') == 'success' and not r.get('second_click', {}).get('is_placeholder', True)]
    real_second = [r['second_click']['elapsed_s'] for r in real_runs]
    hits = sum(1 for r in runs if r.get('second_click', {}).get('inferred_cache_result') == 'likely_hit')
    return {
        'sample_size': len(runs),
        'success_count': sum(1 for r in runs if r.get('second_click', {}).get('status') == 'success'),
        'second_click': summarize(second),
        'real_scene_count': len(real_runs),
        'real_scene_rate': round(len(real_runs) / len(runs), 3) if runs else 0.0,
        'real_scene_second_click': summarize(real_second),
        'likely_hit_count': hits,
        'likely_hit_rate': round(hits / len(runs), 3) if runs else 0.0,
    }

off_runs_clean = [r for r in off_raw['runs'] if r.get('benchmark_id') != INVALID_BENCHMARK_ID]
on_runs_clean = list(on_raw['runs'])

clean_summary = {
    'experiment': 'benchmark_v13_readwait_70s_7v8_cleaned',
    'invalidated_sample': {
        'benchmark_id': INVALID_BENCHMARK_ID,
        'reason': 'External interruption: screen sleep / display off during run; user-confirmed non-engineering anomaly.',
    },
    'source_files': {
        'off_raw': str(base / 'benchmark_v13_readwait_off_70s_8.json'),
        'on_raw': str(base / 'benchmark_v13_readwait_on_70s_8.json'),
    },
    'summary': {
        'off': summarize_runs(off_runs_clean),
        'on': summarize_runs(on_runs_clean),
    },
}
(base / 'benchmark_v13_readwait_70s_7v8_cleaned_summary.json').write_text(json.dumps(clean_summary, ensure_ascii=False, indent=2), encoding='utf-8')

# update threshold table with cleaned 70s off
summary50 = json.loads((base / 'benchmark_v10_readwait_50s_8v8_summary.json').read_text(encoding='utf-8'))
summary55 = json.loads((base / 'benchmark_v11_readwait_55s_8v8_summary.json').read_text(encoding='utf-8'))
summary60 = json.loads((base / 'benchmark_v9_readwait_60s_merged_12v12_summary.json').read_text(encoding='utf-8'))
summary65 = json.loads((base / 'benchmark_v12_readwait_65s_8v8_summary.json').read_text(encoding='utf-8'))
summary70_clean = clean_summary
rows = []
for wait_s, payload in [(50, summary50), (55, summary55), (60, summary60), (65, summary65), (70, summary70_clean)]:
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
with (base / 'benchmark_v13_threshold_50_55_60_65_70_table_cleaned.csv').open('w', encoding='utf-8-sig', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)

print(base / 'benchmark_v13_readwait_70s_7v8_cleaned_summary.json')
print(base / 'benchmark_v13_threshold_50_55_60_65_70_table_cleaned.csv')
