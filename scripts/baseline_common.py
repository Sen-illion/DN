import json
from pathlib import Path
from typing import Dict, Iterable, List


def read_jsonl(path: str | Path) -> List[Dict]:
    rows: List[Dict] = []
    with Path(path).open("r", encoding="utf-8-sig") as handle:
        for line_no, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSONL at {path}:{line_no}: {exc}") from exc
    return rows


def write_jsonl(path: str | Path, rows: Iterable[Dict]) -> None:
    out_path = Path(path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def require_prompt(row: Dict) -> str:
    prompt = str(row.get("prompt", "")).strip()
    if not prompt:
        raise ValueError(f"Sample {row.get('id', '<missing id>')} has empty prompt")
    return prompt


def sample_id(row: Dict, index: int) -> str:
    return str(row.get("id") or f"sample_{index + 1:03d}")
