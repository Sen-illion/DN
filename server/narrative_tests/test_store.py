# -*- coding: utf-8 -*-
"""Tests for the SQLite-backed narrative store."""
from __future__ import annotations

import os
import tempfile

import pytest

from server.narrative import store
from server.narrative.models import (
    BranchState,
    BranchStatus,
    ImageDeps,
    ImageStatus,
    ImageTask,
    TextNode,
    TextStatus,
)


@pytest.fixture()
def tmp_db():
    """Fresh on-disk SQLite per test (file-based to keep WAL semantics realistic)."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    try:
        store.set_db_path(path)
        store.init_db()
        store.reset_db()
        yield path
    finally:
        # Force close per-thread connection before deleting the file (Windows)
        store._close_thread_conn()
        try:
            os.unlink(path)
        except Exception:
            pass


# ---------------------------------------------------------------------------
# TextNode
# ---------------------------------------------------------------------------

class TestTextNode:
    def test_insert_and_fetch(self, tmp_db):
        n = TextNode(
            game_id="g1", text_id="011", scene_id=1, image_index_in_scene=1,
            branch_id="b1", parent_text_id=None,
            content="hello", options=["a", "b"],
        )
        store.upsert_text_node(n)
        got = store.get_text_node("g1", "011")
        assert got is not None
        assert got.content == "hello"
        assert got.options == ["a", "b"]
        assert got.status == TextStatus.PENDING

    def test_upsert_overwrites(self, tmp_db):
        n = TextNode(game_id="g1", text_id="011", scene_id=1,
                     image_index_in_scene=1, branch_id="b1",
                     parent_text_id=None, content="v1")
        store.upsert_text_node(n)
        n.content = "v2"
        n.status = TextStatus.READY
        store.upsert_text_node(n)
        got = store.get_text_node("g1", "011")
        assert got.content == "v2"
        assert got.status == TextStatus.READY

    def test_update_status(self, tmp_db):
        n = TextNode(game_id="g1", text_id="011", scene_id=1,
                     image_index_in_scene=1, branch_id="b1",
                     parent_text_id=None)
        store.upsert_text_node(n)
        assert store.update_text_status("g1", "011", TextStatus.GENERATING) is True
        assert store.get_text_node("g1", "011").status == TextStatus.GENERATING

    def test_update_unknown_status_rejected(self, tmp_db):
        with pytest.raises(ValueError):
            store.update_text_status("g1", "011", "no-such-status")

    def test_list_by_branch_and_scene(self, tmp_db):
        for tid in ("011", "012", "013"):
            store.upsert_text_node(TextNode(
                game_id="g1", text_id=tid, scene_id=1,
                image_index_in_scene=int(tid[2]),
                branch_id="b1", parent_text_id=None,
            ))
        store.upsert_text_node(TextNode(
            game_id="g1", text_id="021", scene_id=2, image_index_in_scene=1,
            branch_id="b2", parent_text_id="013",
        ))
        b1 = store.list_text_nodes_by_branch("g1", "b1")
        assert [n.text_id for n in b1] == ["011", "012", "013"]
        s2 = store.list_text_nodes_by_scene("g1", 2)
        assert [n.text_id for n in s2] == ["021"]

    def test_returns_none_when_missing(self, tmp_db):
        assert store.get_text_node("g1", "099") is None


# ---------------------------------------------------------------------------
# ImageTask
# ---------------------------------------------------------------------------

class TestImageTask:
    def test_insert_with_deps_and_idempotency(self, tmp_db):
        deps = ImageDeps(prev_scene_image="x.png", character_refs=["a", "b"])
        t = ImageTask(
            game_id="g1", anchor_text_id="011", scene_id=1, deps=deps,
            idempotency_key="g1:011:image", branch_id="b1",
        )
        store.upsert_image_task(t)
        got = store.get_image_task("g1", "011")
        assert got is not None
        assert got.deps.prev_scene_image == "x.png"
        assert got.deps.character_refs == ["a", "b"]
        assert got.idempotency_key == "g1:011:image"

    def test_update_status_with_url(self, tmp_db):
        t = ImageTask(game_id="g1", anchor_text_id="011", scene_id=1,
                      idempotency_key="g1:011:image")
        store.upsert_image_task(t)
        ok = store.update_image_status(
            "g1", "011", ImageStatus.READY,
            image_url="http://x/y.png", prompt="a prompt", retry_count=2,
        )
        assert ok
        got = store.get_image_task("g1", "011")
        assert got.status == ImageStatus.READY
        assert got.image_url == "http://x/y.png"
        assert got.prompt == "a prompt"
        assert got.retry_count == 2

    def test_idempotency_key_is_unique(self, tmp_db):
        # different anchor_text_id but same key should violate UNIQUE
        store.upsert_image_task(ImageTask(
            game_id="g1", anchor_text_id="011", scene_id=1,
            idempotency_key="dup-key",
        ))
        import sqlite3
        with pytest.raises(sqlite3.IntegrityError):
            store.upsert_image_task(ImageTask(
                game_id="g1", anchor_text_id="013", scene_id=1,
                idempotency_key="dup-key",
            ))


# ---------------------------------------------------------------------------
# BranchState
# ---------------------------------------------------------------------------

class TestBranchState:
    def test_insert_and_status_change(self, tmp_db):
        b = BranchState(game_id="g1", branch_id="b1", parent_branch_id=None,
                        scene_id=1, root_text_id="011")
        store.upsert_branch(b)
        got = store.get_branch("g1", "b1")
        assert got is not None
        assert got.status == BranchStatus.ACTIVE
        assert store.set_branch_status("g1", "b1", BranchStatus.ABANDONED) is True
        assert store.get_branch("g1", "b1").status == BranchStatus.ABANDONED

    def test_list_by_status(self, tmp_db):
        store.upsert_branch(BranchState(game_id="g1", branch_id="b1",
                                        parent_branch_id=None, scene_id=1,
                                        root_text_id="011"))
        store.upsert_branch(BranchState(game_id="g1", branch_id="b2",
                                        parent_branch_id=None, scene_id=1,
                                        root_text_id="012",
                                        status=BranchStatus.ABANDONED))
        active = store.list_branches("g1", BranchStatus.ACTIVE)
        assert [b.branch_id for b in active] == ["b1"]
        all_b = store.list_branches("g1")
        assert sorted(b.branch_id for b in all_b) == ["b1", "b2"]


# ---------------------------------------------------------------------------
# Events idempotency log
# ---------------------------------------------------------------------------

class TestEvents:
    def test_first_record_succeeds_duplicate_returns_false(self, tmp_db):
        assert store.record_event("k1", "text.generated", "{}") is True
        assert store.record_event("k1", "text.generated", "{}") is False
        assert store.has_event("k1") is True
        assert store.has_event("k2") is False


# ---------------------------------------------------------------------------
# Dead letters
# ---------------------------------------------------------------------------

class TestDeadLetters:
    def test_push_and_list(self, tmp_db):
        rid = store.push_dead_letter(
            topic="image.triggered", payload_json="{}", error="boom",
            retry_count=4, game_id="g1", idempotency_key="g1:011:image",
        )
        assert rid > 0
        rows = store.list_dead_letters("g1")
        assert len(rows) == 1
        assert rows[0]["error"] == "boom"
        assert rows[0]["retry_count"] == 4
        assert store.list_dead_letters("g2") == []
