from __future__ import annotations

import argparse
import csv
from pathlib import Path


def read_csv(path: Path) -> list[dict]:
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        return list(csv.DictReader(fh))


def write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--scaffold", default="text_baseline_comparison_scaffold_2026-04-25.csv")
    parser.add_argument("--genagents-row", default="genagents_table2_row_2026-04-25.csv")
    parser.add_argument("--output", default="text_baseline_comparison_merged_2026-04-25.csv")
    args = parser.parse_args()

    script_path = Path(__file__).resolve()
    repo_root = script_path.parents[6]
    scaffold_path = (
        repo_root
        / "experiments"
        / "paper_method_view"
        / "2_table2_text_planning"
        / "summary_tables"
        / args.scaffold
    )
    genagents_row_path = (
        repo_root
        / "experiments"
        / "paper_method_view"
        / "2_table2_text_planning"
        / "summary_tables"
        / args.genagents_row
    )
    output_path = (
        repo_root
        / "experiments"
        / "paper_method_view"
        / "2_table2_text_planning"
        / "summary_tables"
        / args.output
    )

    scaffold_rows = read_csv(scaffold_path)
    genagents_rows = read_csv(genagents_row_path)
    if not genagents_rows:
        raise RuntimeError("GenAgents row file is empty")
    gen_row = genagents_rows[0]

    out_rows = []
    replaced = False
    for row in scaffold_rows:
        if row.get("system") == "GenAgents":
            out_rows.append(gen_row)
            replaced = True
        else:
            out_rows.append(row)

    if not replaced:
        out_rows.append(gen_row)

    fieldnames = list(out_rows[0].keys()) if out_rows else list(gen_row.keys())
    write_csv(output_path, out_rows, fieldnames)
    print(f"Wrote merged table2 scaffold to: {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
