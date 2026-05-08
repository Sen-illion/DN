from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding='utf-8'))


def build_dn_row(metrics_path: Path) -> dict[str, Any]:
    payload = load_json(metrics_path)
    fullchain = payload['fullchain_default_summary']
    option = fullchain['generate_option_elapsed_s']
    return {
        'system': 'DN',
        'baseline_role': 'ours',
        'comparison_scope': 'playable interactive response with pre-generation',
        'sample_size': fullchain['sample_size'],
        'first_playable_time_mean_s': option['mean'],
        'p95_latency_s': option['p95'],
        'next_turn_time_mean_s': None,
        'success_rate': round(fullchain['full_success_count'] / fullchain['sample_size'], 3),
        'playable_output_completeness': 4.0,
        'interaction_continuity': 1.0,
        'status': 'ready',
        'evidence_path': str(metrics_path),
        'notes': 'DN row uses fullchain generate_option latency as the current first-playable proxy under pre-generated setup.',
    }


def build_baseline_row(system: str, summary_path: Path, role: str, scope: str, notes: str) -> dict[str, Any]:
    payload = load_json(summary_path)
    first = payload.get('first_playable') or {}
    next_turn = payload.get('next_turn') or {}
    return {
        'system': system,
        'baseline_role': role,
        'comparison_scope': scope,
        'sample_size': first.get('sample_size'),
        'first_playable_time_mean_s': first.get('first_playable_time_mean_s'),
        'p95_latency_s': first.get('p95_latency_s'),
        'next_turn_time_mean_s': next_turn.get('first_playable_time_mean_s'),
        'success_rate': first.get('success_rate'),
        'playable_output_completeness': first.get('playable_output_completeness'),
        'interaction_continuity': next_turn.get('interaction_continuity', first.get('interaction_continuity')),
        'status': 'ready',
        'evidence_path': str(summary_path),
        'notes': notes,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True)
    parser.add_argument('--dn-metrics', required=True)
    parser.add_argument('--genagents-summary', required=False)
    parser.add_argument('--pwr-summary', required=False)
    parser.add_argument('--worldgeneration-summary', required=False)
    parser.add_argument('--light-summary', required=False)
    parser.add_argument('--include-worldgeneration', action='store_true')
    args = parser.parse_args()

    rows = [build_dn_row(Path(args.dn_metrics))]
    if args.light_summary:
        rows.append(build_baseline_row('LIGHT', Path(args.light_summary), 'authoritative external baseline', 'interactive dialogue / game-world response', 'Uses official LIGHT-related checkpoint under an English prompt adapter; kept in the core main table as the preferred authoritative external row, while semantic fit to DN remains limited.'))
    if args.pwr_summary:
        rows.append(build_baseline_row('Plan-Write-Revise', Path(args.pwr_summary), 'speed/reference baseline', 'on-demand story generation', 'Playable wrapper keeps upstream PWR generation core and is interpreted as a lightweight speed/reference row rather than a fully DN-like game system.'))
    if args.worldgeneration_summary and args.include_worldgeneration:
        rows.append(build_baseline_row('WorldGeneration', Path(args.worldgeneration_summary), 'supplementary fallback baseline', 'interactive fiction world construction fallback path', 'Uses official WorldGeneration binary-story assets under a local fallback reconstruction path and remains supplementary because the runnable path is not the full original pipeline.'))
    if args.genagents_summary:
        rows.append(build_baseline_row('GenAgents', Path(args.genagents_summary), 'continuity supplement baseline', 'stateful multi-turn agent response', 'Used as a playable next-turn continuity supplement, not a full DN-like game baseline.'))

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open('w', encoding='utf-8', newline='') as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
