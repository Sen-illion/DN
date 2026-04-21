# -*- coding: utf-8 -*-
"""SQLite persistence for the narrative v2 system.

Design choices:
  - One connection per thread via `threading.local`. SQLite's default `:memory:`
    or shared-cache mode would force serialization; per-thread connections plus
    `PRAGMA journal_mode=WAL` give us safe concurrent reads + serialized writes
    with zero external dependencies.
  - All writes go through `transaction()` (a context manager) to ensure
    BEGIN IMMEDIATE / COMMIT / ROLLBACK semantics.
  - An `events` table uses a UNIQUE idempotency_key column to dedupe job
    requests across retries / out-of-order arrivals.
  - A `dead_letters` table holds tasks whose retry budget is exhausted (used
    by step-15 retry/dlq).

Table summary:
  text_nodes(pk={game_id}_{text_id})
  image_tasks(pk={game_id}_{anchor_text_id}_image)
  branch_states(pk={game_id}_{branch_id})
  events(pk=idempotency_key UNIQUE)
  dead_letters(pk=auto)
"""
from __future__ import annotations

import os
import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional

from .models import (
    BranchState,
    ImageDeps,
    ImageStatus,
    ImageTask,
    TextNode,
    TextStatus,
    deps_from_json,
    deps_to_json,
    options_from_json,
    options_to_json,
    _now_iso,
)

# ---------------------------------------------------------------------------
# Connection management (per-thread)
# ---------------------------------------------------------------------------

DEFAULT_DB_PATH = str(Path(__file__).resolve().parents[2] / "data" / "narrative.db")
_DB_PATH_OVERRIDE: Optional[str] = None
_thread_local = threading.local()


def set_db_path(path: str) -> None:
    """Override the DB path (used by tests). Closes any per-thread connection."""
    global _DB_PATH_OVERRIDE
    _DB_PATH_OVERRIDE = path
    _close_thread_conn()


def get_db_path() -> str:
    if _DB_PATH_OVERRIDE is not None:
        return _DB_PATH_OVERRIDE
    return os.environ.get("NARRATIVE_DB_PATH", DEFAULT_DB_PATH)


def _close_thread_conn() -> None:
    conn = getattr(_thread_local, "conn", None)
    if conn is not None:
        try:
            conn.close()
        except Exception:
            pass
        _thread_local.conn = None


def _connect() -> sqlite3.Connection:
    path = get_db_path()
    if path != ":memory:":
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, timeout=30.0, isolation_level=None,
                           check_same_thread=False)
    conn.row_factory = sqlite3.Row
    # WAL gives concurrent readers + a single writer without serializing reads.
    if path != ":memory:":
        try:
            conn.execute("PRAGMA journal_mode=WAL")
        except sqlite3.DatabaseError:
            pass
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("PRAGMA synchronous=NORMAL")
    return conn


def get_conn() -> sqlite3.Connection:
    conn = getattr(_thread_local, "conn", None)
    if conn is None:
        conn = _connect()
        _thread_local.conn = conn
        _ensure_schema(conn)
    return conn


@contextmanager
def transaction() -> Iterator[sqlite3.Connection]:
    """Run a block in BEGIN IMMEDIATE ... COMMIT/ROLLBACK."""
    conn = get_conn()
    conn.execute("BEGIN IMMEDIATE")
    try:
        yield conn
    except Exception:
        conn.execute("ROLLBACK")
        raise
    else:
        conn.execute("COMMIT")


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS text_nodes (
    pk                   TEXT PRIMARY KEY,
    game_id              TEXT NOT NULL,
    text_id              TEXT NOT NULL,
    scene_id             INTEGER NOT NULL,
    image_index_in_scene INTEGER NOT NULL,
    branch_id            TEXT NOT NULL,
    parent_text_id       TEXT,
    content              TEXT NOT NULL DEFAULT '',
    options_json         TEXT NOT NULL DEFAULT '[]',
    status               TEXT NOT NULL,
    created_at           TEXT NOT NULL,
    updated_at           TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_text_nodes_branch ON text_nodes(game_id, branch_id);
CREATE INDEX IF NOT EXISTS idx_text_nodes_scene  ON text_nodes(game_id, scene_id);

CREATE TABLE IF NOT EXISTS image_tasks (
    pk               TEXT PRIMARY KEY,
    game_id          TEXT NOT NULL,
    anchor_text_id   TEXT NOT NULL,
    scene_id         INTEGER NOT NULL,
    branch_id        TEXT NOT NULL DEFAULT '',
    deps_json        TEXT NOT NULL DEFAULT '{}',
    status           TEXT NOT NULL,
    retry_count      INTEGER NOT NULL DEFAULT 0,
    error            TEXT,
    idempotency_key  TEXT NOT NULL UNIQUE,
    image_url        TEXT,
    prompt           TEXT,
    created_at       TEXT NOT NULL,
    updated_at       TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_image_tasks_branch ON image_tasks(game_id, branch_id);

CREATE TABLE IF NOT EXISTS branch_states (
    pk                TEXT PRIMARY KEY,
    game_id           TEXT NOT NULL,
    branch_id         TEXT NOT NULL,
    parent_branch_id  TEXT,
    scene_id          INTEGER NOT NULL,
    root_text_id      TEXT NOT NULL,
    status            TEXT NOT NULL,
    created_at        TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_branch_game ON branch_states(game_id, status);

CREATE TABLE IF NOT EXISTS events (
    idempotency_key  TEXT PRIMARY KEY,
    topic            TEXT NOT NULL,
    payload_json     TEXT NOT NULL,
    created_at       TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_events_topic ON events(topic);

CREATE TABLE IF NOT EXISTS dead_letters (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    game_id          TEXT,
    topic            TEXT NOT NULL,
    payload_json     TEXT NOT NULL,
    error            TEXT,
    retry_count      INTEGER NOT NULL DEFAULT 0,
    idempotency_key  TEXT,
    created_at       TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_dlq_game ON dead_letters(game_id);
"""


def _ensure_schema(conn: sqlite3.Connection) -> None:
    conn.executescript(_SCHEMA_SQL)


def init_db() -> None:
    """Force schema creation in the calling thread."""
    _ensure_schema(get_conn())


def reset_db() -> None:
    """Drop & recreate all tables in the current thread (test helper)."""
    conn = get_conn()
    conn.executescript(
        """
        DROP TABLE IF EXISTS text_nodes;
        DROP TABLE IF EXISTS image_tasks;
        DROP TABLE IF EXISTS branch_states;
        DROP TABLE IF EXISTS events;
        DROP TABLE IF EXISTS dead_letters;
        """
    )
    _ensure_schema(conn)


# ---------------------------------------------------------------------------
# Row <-> dataclass mappers
# ---------------------------------------------------------------------------

def _row_to_text_node(r: sqlite3.Row) -> TextNode:
    return TextNode(
        game_id=r["game_id"],
        text_id=r["text_id"],
        scene_id=r["scene_id"],
        image_index_in_scene=r["image_index_in_scene"],
        branch_id=r["branch_id"],
        parent_text_id=r["parent_text_id"],
        content=r["content"] or "",
        options=options_from_json(r["options_json"]),
        status=r["status"],
        created_at=r["created_at"],
        updated_at=r["updated_at"],
    )


def _row_to_image_task(r: sqlite3.Row) -> ImageTask:
    return ImageTask(
        game_id=r["game_id"],
        anchor_text_id=r["anchor_text_id"],
        scene_id=r["scene_id"],
        deps=deps_from_json(r["deps_json"]),
        status=r["status"],
        retry_count=r["retry_count"],
        error=r["error"],
        idempotency_key=r["idempotency_key"],
        branch_id=r["branch_id"] or "",
        image_url=r["image_url"],
        prompt=r["prompt"],
        created_at=r["created_at"],
        updated_at=r["updated_at"],
    )


def _row_to_branch(r: sqlite3.Row) -> BranchState:
    return BranchState(
        game_id=r["game_id"],
        branch_id=r["branch_id"],
        parent_branch_id=r["parent_branch_id"],
        scene_id=r["scene_id"],
        root_text_id=r["root_text_id"],
        status=r["status"],
        created_at=r["created_at"],
    )


# ---------------------------------------------------------------------------
# TextNode CRUD
# ---------------------------------------------------------------------------

def upsert_text_node(node: TextNode) -> TextNode:
    node.updated_at = _now_iso()
    with transaction() as conn:
        conn.execute(
            """
            INSERT INTO text_nodes
                (pk, game_id, text_id, scene_id, image_index_in_scene,
                 branch_id, parent_text_id, content, options_json,
                 status, created_at, updated_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(pk) DO UPDATE SET
                content=excluded.content,
                options_json=excluded.options_json,
                status=excluded.status,
                updated_at=excluded.updated_at
            """,
            (
                node.pk, node.game_id, node.text_id, node.scene_id,
                node.image_index_in_scene, node.branch_id, node.parent_text_id,
                node.content, options_to_json(node.options),
                node.status, node.created_at, node.updated_at,
            ),
        )
    return node


def get_text_node(game_id: str, text_id: str) -> Optional[TextNode]:
    cur = get_conn().execute(
        "SELECT * FROM text_nodes WHERE pk = ?",
        (f"{game_id}_{text_id}",),
    )
    row = cur.fetchone()
    return _row_to_text_node(row) if row else None


def update_text_status(game_id: str, text_id: str, status: str) -> bool:
    if status not in TextStatus.ALL:
        raise ValueError(f"unknown text status: {status}")
    with transaction() as conn:
        cur = conn.execute(
            "UPDATE text_nodes SET status = ?, updated_at = ? WHERE pk = ?",
            (status, _now_iso(), f"{game_id}_{text_id}"),
        )
        return cur.rowcount > 0


def list_text_nodes_by_branch(game_id: str, branch_id: str) -> List[TextNode]:
    cur = get_conn().execute(
        "SELECT * FROM text_nodes WHERE game_id = ? AND branch_id = ? ORDER BY text_id",
        (game_id, branch_id),
    )
    return [_row_to_text_node(r) for r in cur.fetchall()]


def list_text_nodes_by_scene(game_id: str, scene_id: int) -> List[TextNode]:
    cur = get_conn().execute(
        "SELECT * FROM text_nodes WHERE game_id = ? AND scene_id = ? ORDER BY text_id",
        (game_id, scene_id),
    )
    return [_row_to_text_node(r) for r in cur.fetchall()]


# ---------------------------------------------------------------------------
# ImageTask CRUD
# ---------------------------------------------------------------------------

def upsert_image_task(task: ImageTask) -> ImageTask:
    task.updated_at = _now_iso()
    with transaction() as conn:
        conn.execute(
            """
            INSERT INTO image_tasks
                (pk, game_id, anchor_text_id, scene_id, branch_id,
                 deps_json, status, retry_count, error, idempotency_key,
                 image_url, prompt, created_at, updated_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT(pk) DO UPDATE SET
                deps_json=excluded.deps_json,
                status=excluded.status,
                retry_count=excluded.retry_count,
                error=excluded.error,
                image_url=excluded.image_url,
                prompt=excluded.prompt,
                updated_at=excluded.updated_at
            """,
            (
                task.pk, task.game_id, task.anchor_text_id, task.scene_id,
                task.branch_id, deps_to_json(task.deps), task.status,
                task.retry_count, task.error, task.idempotency_key,
                task.image_url, task.prompt, task.created_at, task.updated_at,
            ),
        )
    return task


def get_image_task(game_id: str, anchor_text_id: str) -> Optional[ImageTask]:
    cur = get_conn().execute(
        "SELECT * FROM image_tasks WHERE pk = ?",
        (f"{game_id}_{anchor_text_id}_image",),
    )
    row = cur.fetchone()
    return _row_to_image_task(row) if row else None


def update_image_status(
    game_id: str, anchor_text_id: str, status: str,
    *, error: Optional[str] = None,
    image_url: Optional[str] = None, prompt: Optional[str] = None,
    retry_count: Optional[int] = None,
) -> bool:
    if status not in ImageStatus.ALL:
        raise ValueError(f"unknown image status: {status}")
    pk = f"{game_id}_{anchor_text_id}_image"
    sets = ["status = ?", "updated_at = ?"]
    args: List[Any] = [status, _now_iso()]
    if error is not None:
        sets.append("error = ?")
        args.append(error)
    if image_url is not None:
        sets.append("image_url = ?")
        args.append(image_url)
    if prompt is not None:
        sets.append("prompt = ?")
        args.append(prompt)
    if retry_count is not None:
        sets.append("retry_count = ?")
        args.append(retry_count)
    args.append(pk)
    with transaction() as conn:
        cur = conn.execute(
            f"UPDATE image_tasks SET {', '.join(sets)} WHERE pk = ?",
            tuple(args),
        )
        return cur.rowcount > 0


def list_image_tasks_by_branch(game_id: str, branch_id: str) -> List[ImageTask]:
    cur = get_conn().execute(
        "SELECT * FROM image_tasks WHERE game_id = ? AND branch_id = ? ORDER BY anchor_text_id",
        (game_id, branch_id),
    )
    return [_row_to_image_task(r) for r in cur.fetchall()]


# ---------------------------------------------------------------------------
# BranchState CRUD
# ---------------------------------------------------------------------------

def upsert_branch(branch: BranchState) -> BranchState:
    with transaction() as conn:
        conn.execute(
            """
            INSERT INTO branch_states
                (pk, game_id, branch_id, parent_branch_id, scene_id,
                 root_text_id, status, created_at)
            VALUES (?,?,?,?,?,?,?,?)
            ON CONFLICT(pk) DO UPDATE SET
                status=excluded.status
            """,
            (
                branch.pk, branch.game_id, branch.branch_id,
                branch.parent_branch_id, branch.scene_id, branch.root_text_id,
                branch.status, branch.created_at,
            ),
        )
    return branch


def get_branch(game_id: str, branch_id: str) -> Optional[BranchState]:
    cur = get_conn().execute(
        "SELECT * FROM branch_states WHERE pk = ?",
        (f"{game_id}_{branch_id}",),
    )
    row = cur.fetchone()
    return _row_to_branch(row) if row else None


def set_branch_status(game_id: str, branch_id: str, status: str) -> bool:
    with transaction() as conn:
        cur = conn.execute(
            "UPDATE branch_states SET status = ? WHERE pk = ?",
            (status, f"{game_id}_{branch_id}"),
        )
        return cur.rowcount > 0


def list_branches(game_id: str, status: Optional[str] = None) -> List[BranchState]:
    if status is None:
        cur = get_conn().execute(
            "SELECT * FROM branch_states WHERE game_id = ? ORDER BY created_at",
            (game_id,),
        )
    else:
        cur = get_conn().execute(
            "SELECT * FROM branch_states WHERE game_id = ? AND status = ? ORDER BY created_at",
            (game_id, status),
        )
    return [_row_to_branch(r) for r in cur.fetchall()]


# ---------------------------------------------------------------------------
# Events (idempotency log) + Dead Letters
# ---------------------------------------------------------------------------

def record_event(idempotency_key: str, topic: str, payload_json: str) -> bool:
    """Insert event row; return False if the key already existed (duplicate)."""
    try:
        with transaction() as conn:
            conn.execute(
                "INSERT INTO events (idempotency_key, topic, payload_json, created_at)"
                " VALUES (?, ?, ?, ?)",
                (idempotency_key, topic, payload_json, _now_iso()),
            )
        return True
    except sqlite3.IntegrityError:
        return False


def has_event(idempotency_key: str) -> bool:
    cur = get_conn().execute(
        "SELECT 1 FROM events WHERE idempotency_key = ?", (idempotency_key,)
    )
    return cur.fetchone() is not None


def push_dead_letter(
    *, topic: str, payload_json: str,
    error: Optional[str], retry_count: int,
    game_id: Optional[str] = None,
    idempotency_key: Optional[str] = None,
) -> int:
    with transaction() as conn:
        cur = conn.execute(
            """
            INSERT INTO dead_letters
                (game_id, topic, payload_json, error, retry_count,
                 idempotency_key, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (game_id, topic, payload_json, error, retry_count,
             idempotency_key, _now_iso()),
        )
        return int(cur.lastrowid or 0)


def list_dead_letters(game_id: Optional[str] = None) -> List[Dict[str, Any]]:
    if game_id is None:
        cur = get_conn().execute(
            "SELECT * FROM dead_letters ORDER BY id DESC"
        )
    else:
        cur = get_conn().execute(
            "SELECT * FROM dead_letters WHERE game_id = ? ORDER BY id DESC",
            (game_id,),
        )
    return [dict(r) for r in cur.fetchall()]
