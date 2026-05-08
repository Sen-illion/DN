from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

from experiments.baseline_integration.adapters.playable_protocol import summarize_playable_runs


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument('--baseline-id', required=True)
    parser.add_argument('--mode', required=True)
    parser.add_argument('--input', required=True)
    parser.add_argument('--output-json', required=True)
    parser.add_argument('--output-csv', required=True)
    args = parser.parse_args()

    in_path = Path(args.input)
    payload = json.loads(in_path.read_text(encoding='utf-8'))
    runs = payload['runs'] if isinstance(payload, dict) and 'runs' in payload else payload
    summary = summarize_playable_runs(args.baseline_id, runs, args.mode)

    out_json = Path(args.output_json)
    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')

    out_csv = Path(args.output_csv)
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    with out_csv.open('w', encoding='utf-8', newline='') as fh:
        writer = csv.DictWriter(fh, fieldnames=list(summary.keys()))
        writer.writeheader()
        writer.writerow(summary)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
