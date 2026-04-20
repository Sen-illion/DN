#!/usr/bin/env python
import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path


def percentile(values, ratio):
    if not values:
        return None
    ordered = sorted(values)
    index = int(round((len(ordered) - 1) * ratio))
    index = max(0, min(index, len(ordered) - 1))
    return ordered[index]


def safe_avg(values):
    return round(sum(values) / len(values), 2) if values else None


def build_group_summary(events):
    queue_wait_ms = [e["queue_wait_ms"] for e in events if isinstance(e.get("queue_wait_ms"), (int, float))]
    latency_ms = [e["latency_ms"] for e in events if isinstance(e.get("latency_ms"), (int, float))]
    statuses = defaultdict(int)
    priorities = defaultdict(int)
    status_codes = defaultdict(int)

    for event in events:
        statuses[str(event.get("status", "unknown"))] += 1
        priorities[str(event.get("priority", "unknown"))] += 1
        if event.get("status_code") is not None:
            status_codes[str(event.get("status_code"))] += 1

    return {
        "events": len(events),
        "statuses": dict(sorted(statuses.items())),
        "priorities": dict(sorted(priorities.items())),
        "status_codes": dict(sorted(status_codes.items())),
        "queue_wait_ms": {
            "avg": safe_avg(queue_wait_ms),
            "p50": percentile(queue_wait_ms, 0.5),
            "p95": percentile(queue_wait_ms, 0.95),
            "max": max(queue_wait_ms) if queue_wait_ms else None,
        },
        "latency_ms": {
            "avg": safe_avg(latency_ms),
            "p50": percentile(latency_ms, 0.5),
            "p95": percentile(latency_ms, 0.95),
            "max": max(latency_ms) if latency_ms else None,
        },
    }


def load_events(path):
    events = []
    with path.open("r", encoding="utf-8") as fh:
        for line_no, line in enumerate(fh, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                events.append(json.loads(line))
            except json.JSONDecodeError:
                events.append({"status": "invalid_json", "line_no": line_no})
    return events


def build_summary(events):
    grouped = defaultdict(list)
    for event in events:
        key = (
            str(event.get("kind", "unknown")),
            str(event.get("provider", "unknown")),
            str(event.get("request_type", "unknown")),
        )
        grouped[key].append(event)

    by_group = {}
    for key, items in sorted(grouped.items()):
        by_group[" / ".join(key)] = build_group_summary(items)

    rate_limited = [e for e in events if e.get("status") == "rate_limited"]
    acquired = [e for e in events if e.get("status") == "acquired"]

    return {
        "total_events": len(events),
        "groups": by_group,
        "headline": {
            "rate_limited_events": len(rate_limited),
            "acquired_events": len(acquired),
            "avg_queue_wait_ms": safe_avg(
                [e["queue_wait_ms"] for e in acquired if isinstance(e.get("queue_wait_ms"), (int, float))]
            ),
            "p95_queue_wait_ms": percentile(
                [e["queue_wait_ms"] for e in acquired if isinstance(e.get("queue_wait_ms"), (int, float))],
                0.95,
            ),
        },
    }


def render_markdown(summary, source_path):
    lines = [
        "# Provider Events Summary",
        "",
        f"- source: `{source_path}`",
        f"- total events: `{summary['total_events']}`",
        f"- rate limited events: `{summary['headline']['rate_limited_events']}`",
        f"- acquired events: `{summary['headline']['acquired_events']}`",
        f"- avg queue wait: `{summary['headline']['avg_queue_wait_ms']}` ms",
        f"- p95 queue wait: `{summary['headline']['p95_queue_wait_ms']}` ms",
        "",
        "## Groups",
        "",
    ]
    for name, group in summary["groups"].items():
        lines.extend(
            [
                f"### {name}",
                "",
                f"- events: `{group['events']}`",
                f"- statuses: `{json.dumps(group['statuses'], ensure_ascii=False)}`",
                f"- priorities: `{json.dumps(group['priorities'], ensure_ascii=False)}`",
                f"- status codes: `{json.dumps(group['status_codes'], ensure_ascii=False)}`",
                f"- queue wait(ms): `{json.dumps(group['queue_wait_ms'], ensure_ascii=False)}`",
                f"- latency(ms): `{json.dumps(group['latency_ms'], ensure_ascii=False)}`",
                "",
            ]
        )
    return "\n".join(lines)


def build_csv_rows(summary):
    rows = []
    for group_name, group in summary["groups"].items():
        rows.append(
            {
                "group": group_name,
                "events": group["events"],
                "statuses": json.dumps(group["statuses"], ensure_ascii=False, sort_keys=True),
                "priorities": json.dumps(group["priorities"], ensure_ascii=False, sort_keys=True),
                "status_codes": json.dumps(group["status_codes"], ensure_ascii=False, sort_keys=True),
                "queue_wait_avg_ms": group["queue_wait_ms"]["avg"],
                "queue_wait_p50_ms": group["queue_wait_ms"]["p50"],
                "queue_wait_p95_ms": group["queue_wait_ms"]["p95"],
                "queue_wait_max_ms": group["queue_wait_ms"]["max"],
                "latency_avg_ms": group["latency_ms"]["avg"],
                "latency_p50_ms": group["latency_ms"]["p50"],
                "latency_p95_ms": group["latency_ms"]["p95"],
                "latency_max_ms": group["latency_ms"]["max"],
            }
        )
    return rows


def main():
    parser = argparse.ArgumentParser(description="Summarize DN provider event logs.")
    parser.add_argument(
        "--input",
        default="logs/provider_events.jsonl",
        help="Path to provider event JSONL file.",
    )
    parser.add_argument(
        "--output-json",
        default="logs/provider_events_summary.json",
        help="Where to write the aggregated JSON summary.",
    )
    parser.add_argument(
        "--output-md",
        default="logs/provider_events_summary.md",
        help="Where to write the markdown summary.",
    )
    parser.add_argument(
        "--output-csv",
        default="logs/provider_events_summary.csv",
        help="Where to write the flat CSV summary.",
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        raise SystemExit(f"Input file not found: {input_path}")

    events = load_events(input_path)
    summary = build_summary(events)

    output_json = Path(args.output_json)
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    output_md = Path(args.output_md)
    output_md.parent.mkdir(parents=True, exist_ok=True)
    output_md.write_text(render_markdown(summary, input_path), encoding="utf-8")

    output_csv = Path(args.output_csv)
    output_csv.parent.mkdir(parents=True, exist_ok=True)
    rows = build_csv_rows(summary)
    with output_csv.open("w", encoding="utf-8-sig", newline="") as fh:
        fieldnames = [
            "group",
            "events",
            "statuses",
            "priorities",
            "status_codes",
            "queue_wait_avg_ms",
            "queue_wait_p50_ms",
            "queue_wait_p95_ms",
            "queue_wait_max_ms",
            "latency_avg_ms",
            "latency_p50_ms",
            "latency_p95_ms",
            "latency_max_ms",
        ]
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote JSON summary to {output_json}")
    print(f"Wrote Markdown summary to {output_md}")
    print(f"Wrote CSV summary to {output_csv}")


if __name__ == "__main__":
    main()
