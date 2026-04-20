from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any

from .repository import WorkflowRepository
from .types import BranchState, GameState, ImageDeps, ImageTask, OptionRef, TextNode


class SqliteWorkflowRepository(WorkflowRepository):
    def __init__(self, database_path: str):
        self.database_path = str(database_path)
        Path(self.database_path).parent.mkdir(parents=True, exist_ok=True)
        self.init_schema()

    @contextmanager
    def _conn(self):
        conn = sqlite3.connect(self.database_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def init_schema(self) -> None:
        with self._conn() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS game_states (
                    game_id TEXT PRIMARY KEY,
                    active_branch_id TEXT NOT NULL,
                    current_scene_id INTEGER NOT NULL,
                    turn_in_scene INTEGER NOT NULL,
                    scene_switch_threshold INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS text_nodes (
                    game_id TEXT NOT NULL,
                    text_id TEXT NOT NULL,
                    scene_id INTEGER NOT NULL,
                    image_index_in_scene INTEGER NOT NULL,
                    branch_id TEXT NOT NULL,
                    parent_text_id TEXT,
                    content TEXT NOT NULL,
                    options_json TEXT NOT NULL,
                    status TEXT NOT NULL,
                    choice_index INTEGER,
                    is_scene_entry INTEGER NOT NULL,
                    anchor_image_task_id TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (game_id, text_id)
                );
                CREATE TABLE IF NOT EXISTS image_tasks (
                    game_id TEXT NOT NULL,
                    anchor_text_id TEXT NOT NULL,
                    scene_id INTEGER NOT NULL,
                    branch_id TEXT NOT NULL,
                    deps_json TEXT NOT NULL,
                    status TEXT NOT NULL,
                    retry_count INTEGER NOT NULL,
                    error TEXT,
                    result_url TEXT,
                    cancel_requested INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (game_id, anchor_text_id)
                );
                CREATE TABLE IF NOT EXISTS branch_states (
                    game_id TEXT NOT NULL,
                    branch_id TEXT NOT NULL,
                    scene_id INTEGER NOT NULL,
                    status TEXT NOT NULL,
                    current_text_id TEXT,
                    last_anchor_text_id TEXT,
                    last_scene_image_id TEXT,
                    depth INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (game_id, branch_id)
                );
                CREATE TABLE IF NOT EXISTS event_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    game_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    payload_json TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                """
            )

    def save_game_state(self, state: GameState) -> GameState:
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO game_states(game_id, active_branch_id, current_scene_id, turn_in_scene,
                    scene_switch_threshold, status, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(game_id) DO UPDATE SET
                    active_branch_id=excluded.active_branch_id,
                    current_scene_id=excluded.current_scene_id,
                    turn_in_scene=excluded.turn_in_scene,
                    scene_switch_threshold=excluded.scene_switch_threshold,
                    status=excluded.status,
                    updated_at=excluded.updated_at
                """,
                (
                    state.game_id, state.active_branch_id, state.current_scene_id,
                    state.turn_in_scene, state.scene_switch_threshold, state.status,
                    state.created_at.isoformat(), state.updated_at.isoformat(),
                ),
            )
        return state

    def get_game_state(self, game_id: str) -> GameState | None:
        with self._conn() as conn:
            row = conn.execute("SELECT * FROM game_states WHERE game_id = ?", (game_id,)).fetchone()
        return self._row_to_game_state(row) if row else None

    def save_text_node(self, node: TextNode) -> TextNode:
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO text_nodes(game_id, text_id, scene_id, image_index_in_scene, branch_id,
                    parent_text_id, content, options_json, status, choice_index, is_scene_entry,
                    anchor_image_task_id, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(game_id, text_id) DO UPDATE SET
                    scene_id=excluded.scene_id,
                    image_index_in_scene=excluded.image_index_in_scene,
                    branch_id=excluded.branch_id,
                    parent_text_id=excluded.parent_text_id,
                    content=excluded.content,
                    options_json=excluded.options_json,
                    status=excluded.status,
                    choice_index=excluded.choice_index,
                    is_scene_entry=excluded.is_scene_entry,
                    anchor_image_task_id=excluded.anchor_image_task_id,
                    updated_at=excluded.updated_at
                """,
                (
                    node.game_id, node.text_id, node.scene_id, node.image_index_in_scene,
                    node.branch_id, node.parent_text_id, node.content,
                    json.dumps([option.__dict__ for option in node.options], ensure_ascii=False),
                    node.status, node.choice_index, 1 if node.is_scene_entry else 0,
                    node.anchor_image_task_id, node.created_at.isoformat(), node.updated_at.isoformat(),
                ),
            )
        return node

    def get_text_node(self, game_id: str, text_id: str) -> TextNode | None:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM text_nodes WHERE game_id = ? AND text_id = ?", (game_id, text_id)
            ).fetchone()
        return self._row_to_text_node(row) if row else None

    def list_text_nodes(self, game_id: str, branch_id: str | None = None) -> list[TextNode]:
        query = "SELECT * FROM text_nodes WHERE game_id = ?"
        params: list[Any] = [game_id]
        if branch_id is not None:
            query += " AND branch_id = ?"
            params.append(branch_id)
        query += " ORDER BY text_id"
        with self._conn() as conn:
            rows = conn.execute(query, params).fetchall()
        return [self._row_to_text_node(row) for row in rows]

    def save_image_task(self, task: ImageTask) -> ImageTask:
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO image_tasks(game_id, anchor_text_id, scene_id, branch_id, deps_json,
                    status, retry_count, error, result_url, cancel_requested, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(game_id, anchor_text_id) DO UPDATE SET
                    scene_id=excluded.scene_id,
                    branch_id=excluded.branch_id,
                    deps_json=excluded.deps_json,
                    status=excluded.status,
                    retry_count=excluded.retry_count,
                    error=excluded.error,
                    result_url=excluded.result_url,
                    cancel_requested=excluded.cancel_requested,
                    updated_at=excluded.updated_at
                """,
                (
                    task.game_id, task.anchor_text_id, task.scene_id, task.branch_id,
                    json.dumps(task.deps.__dict__, ensure_ascii=False), task.status,
                    task.retry_count, task.error, task.result_url,
                    1 if task.cancel_requested else 0,
                    task.created_at.isoformat(), task.updated_at.isoformat(),
                ),
            )
        return task

    def get_image_task(self, game_id: str, anchor_text_id: str) -> ImageTask | None:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM image_tasks WHERE game_id = ? AND anchor_text_id = ?",
                (game_id, anchor_text_id),
            ).fetchone()
        return self._row_to_image_task(row) if row else None

    def list_image_tasks(self, game_id: str, branch_id: str | None = None) -> list[ImageTask]:
        query = "SELECT * FROM image_tasks WHERE game_id = ?"
        params: list[Any] = [game_id]
        if branch_id is not None:
            query += " AND branch_id = ?"
            params.append(branch_id)
        query += " ORDER BY anchor_text_id"
        with self._conn() as conn:
            rows = conn.execute(query, params).fetchall()
        return [self._row_to_image_task(row) for row in rows]

    def save_branch_state(self, state: BranchState) -> BranchState:
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO branch_states(game_id, branch_id, scene_id, status, current_text_id,
                    last_anchor_text_id, last_scene_image_id, depth, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(game_id, branch_id) DO UPDATE SET
                    scene_id=excluded.scene_id,
                    status=excluded.status,
                    current_text_id=excluded.current_text_id,
                    last_anchor_text_id=excluded.last_anchor_text_id,
                    last_scene_image_id=excluded.last_scene_image_id,
                    depth=excluded.depth,
                    updated_at=excluded.updated_at
                """,
                (
                    state.game_id, state.branch_id, state.scene_id, state.status,
                    state.current_text_id, state.last_anchor_text_id, state.last_scene_image_id,
                    state.depth, state.created_at.isoformat(), state.updated_at.isoformat(),
                ),
            )
        return state

    def get_branch_state(self, game_id: str, branch_id: str) -> BranchState | None:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM branch_states WHERE game_id = ? AND branch_id = ?",
                (game_id, branch_id),
            ).fetchone()
        return self._row_to_branch_state(row) if row else None

    def list_branch_states(self, game_id: str) -> list[BranchState]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT * FROM branch_states WHERE game_id = ? ORDER BY branch_id", (game_id,)
            ).fetchall()
        return [self._row_to_branch_state(row) for row in rows]

    def append_event(self, game_id: str, event_type: str, payload: dict[str, Any]) -> None:
        created_at = payload.get("created_at") or datetime.utcnow().isoformat()
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO event_logs(game_id, event_type, payload_json, created_at) VALUES (?, ?, ?, ?)",
                (game_id, event_type, json.dumps(payload, ensure_ascii=False), created_at),
            )

    def list_events(self, game_id: str, event_type: str | None = None) -> list[dict[str, Any]]:
        query = "SELECT * FROM event_logs WHERE game_id = ?"
        params: list[Any] = [game_id]
        if event_type is not None:
            query += " AND event_type = ?"
            params.append(event_type)
        query += " ORDER BY id"
        with self._conn() as conn:
            rows = conn.execute(query, params).fetchall()
        return [json.loads(row["payload_json"]) for row in rows]

    def _row_to_game_state(self, row: sqlite3.Row) -> GameState:
        return GameState(
            game_id=row["game_id"],
            active_branch_id=row["active_branch_id"],
            current_scene_id=row["current_scene_id"],
            turn_in_scene=row["turn_in_scene"],
            scene_switch_threshold=row["scene_switch_threshold"],
            status=row["status"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

    def _row_to_text_node(self, row: sqlite3.Row) -> TextNode:
        options = [OptionRef(**item) for item in json.loads(row["options_json"])]
        return TextNode(
            game_id=row["game_id"],
            text_id=row["text_id"],
            scene_id=row["scene_id"],
            image_index_in_scene=row["image_index_in_scene"],
            branch_id=row["branch_id"],
            parent_text_id=row["parent_text_id"],
            content=row["content"],
            options=options,
            status=row["status"],
            choice_index=row["choice_index"],
            is_scene_entry=bool(row["is_scene_entry"]),
            anchor_image_task_id=row["anchor_image_task_id"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

    def _row_to_image_task(self, row: sqlite3.Row) -> ImageTask:
        deps = ImageDeps(**json.loads(row["deps_json"]))
        return ImageTask(
            game_id=row["game_id"],
            anchor_text_id=row["anchor_text_id"],
            scene_id=row["scene_id"],
            branch_id=row["branch_id"],
            deps=deps,
            status=row["status"],
            retry_count=row["retry_count"],
            error=row["error"],
            result_url=row["result_url"],
            cancel_requested=bool(row["cancel_requested"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )

    def _row_to_branch_state(self, row: sqlite3.Row) -> BranchState:
        return BranchState(
            game_id=row["game_id"],
            branch_id=row["branch_id"],
            scene_id=row["scene_id"],
            status=row["status"],
            current_text_id=row["current_text_id"],
            last_anchor_text_id=row["last_anchor_text_id"],
            last_scene_image_id=row["last_scene_image_id"],
            depth=row["depth"],
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )
