import json, statistics, csv
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
base = PROJECT_ROOT / "experiments" / "benchmark" / "standard_runs"

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
    return {'count': len(values), 'min': round(min(values),3), 'max': round(max(values),3), 'mean': round(statistics.mean(values),3), 'median': round(statistics.median(values),3), 'p95': round(percentile(values,0.95),3)}

def build_summary(off_file, on_file, out_file, exp_name, note):
    files = {'off': base / off_file, 'on': base / on_file}
    combined = {k: json.loads(v.read_text(encoding='utf-8'))['runs'] for k,v in files.items()}
    summary = {}
    for label, runs in combined.items():
        second = [r['second_click']['elapsed_s'] for r in runs if r.get('second_click', {}).get('status') == 'success']
        real_runs = [r for r in runs if r.get('second_click', {}).get('status') == 'success' and not r.get('second_click', {}).get('is_placeholder', True)]
        real_second = [r['second_click']['elapsed_s'] for r in real_runs]
        summary[label] = {
            'sample_size': len(runs),
            'success_count': sum(1 for r in runs if r.get('second_click', {}).get('status') == 'success'),
            'second_click': summarize(second),
            'real_scene_count': len(real_runs),
            'real_scene_rate': round(len(real_runs)/len(runs),3) if runs else 0.0,
            'real_scene_second_click': summarize(real_second),
            'likely_hit_count': sum(1 for r in runs if r.get('second_click', {}).get('inferred_cache_result') == 'likely_hit'),
            'likely_hit_rate': round(sum(1 for r in runs if r.get('second_click', {}).get('inferred_cache_result') == 'likely_hit')/len(runs),3) if runs else 0.0,
        }
    paired_rows = []
    off_map = {r['benchmark_id']: r for r in combined['off']}
    on_map = {r['benchmark_id']: r for r in combined['on']}
    for bid in sorted(set(off_map) & set(on_map)):
        off = off_map[bid]['second_click']; on = on_map[bid]['second_click']
        paired_rows.append({
            'benchmark_id': bid,
            'off_elapsed_s': off.get('elapsed_s'),
            'on_elapsed_s': on.get('elapsed_s'),
            'off_real': not off.get('is_placeholder', True),
            'on_real': not on.get('is_placeholder', True),
            'faster': 'on' if on.get('elapsed_s') < off.get('elapsed_s') else ('off' if off.get('elapsed_s') < on.get('elapsed_s') else 'tie'),
        })
    out = {
        'experiment': exp_name,
        'source_files': {k: str(v) for k,v in files.items()},
        'summary': summary,
        'paired': {'rows': paired_rows, 'counts': {
            'on_faster': sum(1 for r in paired_rows if r['faster']=='on'),
            'off_faster': sum(1 for r in paired_rows if r['faster']=='off'),
            'tie': sum(1 for r in paired_rows if r['faster']=='tie'),
            'both_real_count': sum(1 for r in paired_rows if r['off_real'] and r['on_real']),
            'on_faster_when_both_real': sum(1 for r in paired_rows if r['off_real'] and r['on_real'] and r['faster']=='on'),
            'off_faster_when_both_real': sum(1 for r in paired_rows if r['off_real'] and r['on_real'] and r['faster']=='off'),
        }},
        'notes': [note, 'real_scene is approximated by second_click.is_placeholder == false.']
    }
    (base / out_file).write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding='utf-8')
    return out

summary70 = build_summary('benchmark_v13_readwait_off_70s_8.json', 'benchmark_v13_readwait_on_70s_8.json', 'benchmark_v13_readwait_70s_8v8_summary.json', 'benchmark_v13_readwait_70s_8v8', '70s run is a threshold exploration experiment.')

summary50 = json.loads((base / 'benchmark_v10_readwait_50s_8v8_summary.json').read_text(encoding='utf-8'))
summary55 = json.loads((base / 'benchmark_v11_readwait_55s_8v8_summary.json').read_text(encoding='utf-8'))
summary60 = json.loads((base / 'benchmark_v9_readwait_60s_merged_12v12_summary.json').read_text(encoding='utf-8'))
summary65 = json.loads((base / 'benchmark_v12_readwait_65s_8v8_summary.json').read_text(encoding='utf-8'))
summary70 = json.loads((base / 'benchmark_v13_readwait_70s_8v8_summary.json').read_text(encoding='utf-8'))
rows = []
for wait_s, payload in [(50, summary50), (55, summary55), (60, summary60), (65, summary65), (70, summary70)]:
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
with (base / 'benchmark_v13_threshold_50_55_60_65_70_table.csv').open('w', encoding='utf-8-sig', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
    writer.writeheader()
    writer.writerows(rows)
print(base / 'benchmark_v13_readwait_70s_8v8_summary.json')
print(base / 'benchmark_v13_threshold_50_55_60_65_70_table.csv')
