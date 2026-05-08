from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from flask import Flask, jsonify, request, send_from_directory


CURRENT_DIR = Path(__file__).resolve().parent
if (CURRENT_DIR / "index.html").exists():
    SITE_ROOT = CURRENT_DIR
    REPO_ROOT = CURRENT_DIR.parent if (CURRENT_DIR.parent / "outputs").exists() else CURRENT_DIR
else:
    REPO_ROOT = CURRENT_DIR.parent
    SITE_ROOT = REPO_ROOT / "human_eval_site"
DATA_ROOT = SITE_ROOT / "data"
RESULTS_ROOT = SITE_ROOT / "collected_results"
THEME_CATALOG_PATH = DATA_ROOT / "theme_catalog.json"
INVITE_TOKENS_PATH = DATA_ROOT / "invite_tokens.json"
WRITE_LOCK = threading.Lock()


app = Flask(__name__, static_folder=str(SITE_ROOT), static_url_path="")


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def load_json(path: Path, default: Any) -> Any:
    if not path.exists():
      return default
    return json.loads(path.read_text(encoding="utf-8-sig"))


def save_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def sanitize_segment(value: str) -> str:
    cleaned = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in value)
    return cleaned.strip("_") or "unknown"


def display_path(path: Path) -> str:
    try:
        return str(path.relative_to(REPO_ROOT)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


def load_theme_catalog() -> dict[str, Any]:
    catalog = load_json(THEME_CATALOG_PATH, {})
    if not catalog or not catalog.get("themes"):
        raise FileNotFoundError(
            "theme_catalog.json is missing. Run human_eval_site/tools/build_theme_catalog.py first."
        )
    return catalog


def load_invites() -> dict[str, Any]:
    invites = load_json(INVITE_TOKENS_PATH, {})
    if not invites or not invites.get("tokens"):
        raise FileNotFoundError(
            "invite_tokens.json is missing. Run human_eval_site/tools/generate_invites.py first."
        )
    return invites


def get_assignment(token: str) -> dict[str, Any]:
    invites = load_invites()
    for item in invites["tokens"]:
        if item.get("token") == token:
            return item
    raise KeyError(f"Unknown token: {token}")


def get_dataset_for_theme(theme_id: str) -> dict[str, Any]:
    catalog = load_theme_catalog()
    for theme in catalog["themes"]:
        if theme.get("themeId") == theme_id:
            return {
                "studyTitle": catalog.get("studyTitle", "文本与图片一致性人类测评"),
                "instructions": catalog.get("instructions", []),
                "dimensions": catalog.get("dimensions", []),
                "cases": [theme["case"]],
            }
    raise KeyError(f"Unknown theme: {theme_id}")


def append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False) + "\n")


@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type"
    response.headers["Access-Control-Allow-Methods"] = "GET,POST,OPTIONS"
    return response


@app.route("/api/session", methods=["GET", "OPTIONS"])
def session():
    if request.method == "OPTIONS":
        return ("", 204)

    token = str(request.args.get("token") or "").strip()
    if not token:
        return jsonify({"error": "Missing token"}), 400

    try:
        invites = load_invites()
        assignment = None
        for item in invites["tokens"]:
            if item.get("token") == token:
                assignment = item
                break
        if assignment is None:
            raise KeyError(f"Unknown token: {token}")
        dataset = get_dataset_for_theme(assignment["themeId"])
    except FileNotFoundError as exc:
        return jsonify({"error": str(exc)}), 500
    except KeyError as exc:
        return jsonify({"error": str(exc)}), 404

    if not assignment.get("claimedAt"):
        assignment["claimedAt"] = utc_now_iso()
        save_json(INVITE_TOKENS_PATH, invites)

    return jsonify(
        {
            "assignment": {
                "token": assignment.get("token"),
                "themeId": assignment.get("themeId"),
                "themeTitle": assignment.get("themeTitle"),
                "batchId": assignment.get("batchId"),
                "slotIndex": assignment.get("slotIndex"),
                "claimedAt": assignment.get("claimedAt"),
                "submittedAt": assignment.get("submittedAt"),
                "submissionCount": assignment.get("submissionCount", 0),
                "evaluatorId": assignment.get("evaluatorId", ""),
            },
            "dataset": dataset,
        }
    )


@app.route("/api/submit", methods=["POST", "OPTIONS"])
def submit():
    if request.method == "OPTIONS":
        return ("", 204)

    body = request.get_json(silent=True) or {}
    token = str(body.get("token") or "").strip()
    if not token:
        return jsonify({"error": "Missing token"}), 400

    evaluator_id = str(body.get("evaluatorId") or "").strip()
    payload = body.get("payload")
    if not isinstance(payload, dict):
        return jsonify({"error": "Missing payload"}), 400

    try:
        catalog = load_theme_catalog()
        invites = load_invites()
    except FileNotFoundError as exc:
        return jsonify({"error": str(exc)}), 500

    assignment = None
    for item in invites["tokens"]:
        if item.get("token") == token:
            assignment = item
            break
    if assignment is None:
        return jsonify({"error": f"Unknown token: {token}"}), 404

    theme_id = assignment.get("themeId") or payload.get("assignment", {}).get("themeId") or "unknown_theme"
    theme_title = assignment.get("themeTitle") or theme_id
    saved_at = utc_now_iso()

    submission_record = {
        "savedAt": saved_at,
        "token": token,
        "themeId": theme_id,
        "themeTitle": theme_title,
        "evaluatorId": evaluator_id,
        "remoteAddr": request.headers.get("X-Forwarded-For", request.remote_addr),
        "userAgent": request.headers.get("User-Agent", ""),
        "payload": payload,
    }

    timestamp_label = saved_at.replace(":", "-")
    result_dir = RESULTS_ROOT / sanitize_segment(theme_id)
    result_path = result_dir / f"{timestamp_label}__{sanitize_segment(token)}.json"
    index_path = RESULTS_ROOT / "submissions_index.jsonl"
    summary_path = RESULTS_ROOT / "latest_submission_summary.json"

    with WRITE_LOCK:
        result_dir.mkdir(parents=True, exist_ok=True)
        result_path.write_text(json.dumps(submission_record, ensure_ascii=False, indent=2), encoding="utf-8")
        append_jsonl(index_path, {
            "savedAt": saved_at,
            "token": token,
            "themeId": theme_id,
            "themeTitle": theme_title,
            "evaluatorId": evaluator_id,
            "file": display_path(result_path),
        })

        assignment["claimedAt"] = assignment.get("claimedAt") or saved_at
        assignment["submittedAt"] = saved_at
        assignment["evaluatorId"] = evaluator_id
        assignment["submissionCount"] = int(assignment.get("submissionCount", 0)) + 1
        assignment["latestResultFile"] = display_path(result_path)
        save_json(INVITE_TOKENS_PATH, invites)

        save_json(
            summary_path,
            {
                "updatedAt": saved_at,
                "themeCount": len(catalog.get("themes", [])),
                "tokenCount": len(invites.get("tokens", [])),
                "submittedCount": sum(1 for item in invites["tokens"] if item.get("submittedAt")),
                "latestSubmission": {
                    "token": token,
                    "themeId": theme_id,
                    "themeTitle": theme_title,
                    "evaluatorId": evaluator_id,
                        "file": display_path(result_path),
                },
            },
        )

    return jsonify(
        {
            "ok": True,
            "savedAt": saved_at,
            "themeId": theme_id,
            "file": display_path(result_path),
        }
    )


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"ok": True, "time": utc_now_iso()})


@app.route("/outputs/<path:filename>", methods=["GET"])
def outputs(filename: str):
    return send_from_directory(REPO_ROOT / "outputs", filename)


@app.route("/data/<path:filename>", methods=["GET"])
def data_files(filename: str):
    return send_from_directory(DATA_ROOT, filename)


@app.route("/", methods=["GET"])
def index():
    return send_from_directory(SITE_ROOT, "index.html")


@app.route("/<path:filename>", methods=["GET"])
def static_files(filename: str):
    target = SITE_ROOT / filename
    if target.exists() and target.is_file():
        return send_from_directory(SITE_ROOT, filename)
    return send_from_directory(SITE_ROOT, "index.html")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
