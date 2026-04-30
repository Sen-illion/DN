from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

from experiments.baseline_integration.adapters.playable_protocol import normalize_playable_response, summarize_playable_runs


def pick_actions(response_text: str) -> list[str]:
    lines = [line.strip(' -*0123456789.\t') for line in str(response_text).splitlines()]
    actions = [line for line in lines if line and len(line) > 8][:4]
    if not actions:
        actions = ['Advance using the most concrete next step in the response.']
    return actions


def convert_turn(baseline_id: str, benchmark_id: str, turn: dict[str, Any], mode: str, player_state: str) -> dict[str, Any]:
    latency = float(turn.get('latency_s') or 0.0)
    response_text = str(turn.get('response') or '')
    scene_setup = response_text.split('?')[0].strip() if '?' in response_text else response_text[:120].strip()
    request_start_ts = 0.0
    finish_ts = latency
    run = normalize_playable_response(
        baseline_id=baseline_id,
        benchmark_id=benchmark_id,
        raw_output=turn,
        scene_setup=scene_setup,
        player_state=player_state,
        narrative_response=response_text,
        candidate_actions=pick_actions(response_text),
        suggested_next_step='Continue from the same state with one concrete action.',
        supports_next_turn=True,
        request_start_ts=request_start_ts,
        first_playable_ts=finish_ts,
        finish_ts=finish_ts,
        error=turn.get('blocked_reason'),
    )
    run['mode'] = mode
    run['input_bundle'] = {'turn_index': turn.get('turn_index')}
    run['latency_s'] = latency
    return run


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = ['baseline_id', 'benchmark_id', 'mode', 'success', 'latency_s', 'scene_setup']
    with path.open('w', encoding='utf-8', newline='') as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    'baseline_id': row['baseline_id'],
                    'benchmark_id': row['benchmark_id'],
                    'mode': row['mode'],
                    'success': row['success'],
                    'latency_s': row['latency_s'],
                    'scene_setup': row['normalized_response'].get('scene_setup', ''),
                }
            )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True)
    parser.add_argument('--output-json', required=True)
    parser.add_argument('--output-csv', required=True)
    parser.add_argument('--summary-json', required=True)
    args = parser.parse_args()

    payload = json.loads(Path(args.input).read_text(encoding='utf-8'))
    native_runs = payload.get('raw_output', {}).get('native_run', {}).get('runs', [])

    first_runs = []
    next_runs = []
    for item in native_runs:
        benchmark_id = item['benchmark_id']
        theme = item.get('theme', '')
        player_state = f'You are the acting character inside the theme {theme}.'.strip()
        turns = item.get('turn_outputs') or []
        if turns:
            first_runs.append(convert_turn('genagents', benchmark_id, turns[0], 'first_playable', player_state))
        for turn in turns[1:]:
            next_runs.append(convert_turn('genagents', benchmark_id, turn, 'next_turn', player_state))

    all_runs = first_runs + next_runs
    out_json = Path(args.output_json)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps({'runs': all_runs}, ensure_ascii=False, indent=2), encoding='utf-8')
    write_csv(Path(args.output_csv), all_runs)

    summary = {
        'first_playable': summarize_playable_runs('genagents', first_runs, 'first_playable'),
        'next_turn': summarize_playable_runs('genagents', next_runs, 'next_turn'),
    }
    summary_path = Path(args.summary_json)
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
