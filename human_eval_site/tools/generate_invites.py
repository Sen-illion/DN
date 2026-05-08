from __future__ import annotations

import argparse
import csv
import json
import secrets
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_ROOT = REPO_ROOT / "human_eval_site" / "data"
THEME_CATALOG_PATH = DATA_ROOT / "theme_catalog.json"
INVITE_TOKENS_PATH = DATA_ROOT / "invite_tokens.json"
INVITE_LINKS_CSV = DATA_ROOT / "invite_links.csv"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def load_catalog() -> dict:
    return json.loads(THEME_CATALOG_PATH.read_text(encoding="utf-8-sig"))


def load_existing_tokens() -> list[dict]:
    if not INVITE_TOKENS_PATH.exists():
        return []
    payload = json.loads(INVITE_TOKENS_PATH.read_text(encoding="utf-8-sig"))
    return list(payload.get("tokens", []))


def build_invite(base_url: str, token: str) -> str:
    separator = "&" if "?" in base_url else "?"
    return f"{base_url}{separator}token={token}"


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate invite tokens for human eval site.")
    parser.add_argument("--base-url", default="http://127.0.0.1:5000/", help="Base URL of the deployed or local site.")
    parser.add_argument("--raters-per-theme", type=int, default=1, help="How many invite links to generate for each theme.")
    parser.add_argument("--batch-id", default=None, help="Optional batch ID for bookkeeping.")
    parser.add_argument(
        "--mode",
        choices=["image", "text"],
        default="image",
        help="Evaluation mode. image = token-bound theme image eval, text = shared text eval dataset.",
    )
    args = parser.parse_args()

    catalog = load_catalog()
    batch_id = args.batch_id or f"batch_{utc_now_iso().replace(':', '-')}"
    created_at = utc_now_iso()

    existing_tokens = load_existing_tokens()
    new_tokens = []
    for theme in catalog["themes"]:
        for slot_index in range(1, args.raters_per_theme + 1):
            token = secrets.token_urlsafe(10)
            invite_url = build_invite(args.base_url.rstrip("/"), token)
            if args.mode:
                invite_url = f"{invite_url}&mode={args.mode}"
            new_tokens.append(
                {
                    "token": token,
                    "themeId": theme["themeId"],
                    "themeTitle": theme["title"],
                    "mode": args.mode,
                    "slotIndex": slot_index,
                    "batchId": batch_id,
                    "createdAt": created_at,
                    "claimedAt": None,
                    "submittedAt": None,
                    "submissionCount": 0,
                    "evaluatorId": "",
                    "inviteUrl": invite_url,
                }
            )

    tokens = existing_tokens + new_tokens
    payload = {
        "updatedAt": created_at,
        "tokens": tokens,
    }
    INVITE_TOKENS_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    with INVITE_LINKS_CSV.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["token", "themeId", "themeTitle", "mode", "slotIndex", "batchId", "inviteUrl"],
        )
        writer.writeheader()
        for item in tokens:
            writer.writerow(
                {
                    "token": item["token"],
                    "themeId": item["themeId"],
                    "themeTitle": item["themeTitle"],
                    "mode": item["mode"],
                    "slotIndex": item["slotIndex"],
                    "batchId": item["batchId"],
                    "inviteUrl": item["inviteUrl"],
                }
            )

    print(f"Wrote {len(tokens)} invite links to {INVITE_TOKENS_PATH}")
    print(f"Wrote CSV summary to {INVITE_LINKS_CSV}")


if __name__ == "__main__":
    main()
