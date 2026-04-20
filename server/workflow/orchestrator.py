from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .branch_rules import child_branch_id, is_branch_descendant, mark_branch_abandoned
from .config import WorkflowSettings
from .enums import BranchStatus, GameStatus, ImageTaskStatus, TextNodeStatus
from .events_bus import WorkflowEventBus
from .ids import image_task_pk, next_text_id, parse_text_id
from .image_rules import build_image_deps, should_trigger_image
from .redis_store import InMemoryLeaseStore, RedisLeaseStore
from .scene_rules import build_scene_option_refs, next_scene_id, should_prepare_scene
from .sql_store import SqliteWorkflowRepository
from .state_machine import ensure_image_transition, ensure_text_transition
from .tasks import WorkflowTaskRunner
from .types import BranchState, GameState, ImageTask, OptionRef, TextNode

try:
    from PIL import Image, ImageDraw
except Exception:
    Image = None
    ImageDraw = None


class WorkflowOrchestrator:
    def __init__(self, settings: WorkflowSettings | None = None, repository=None, lease_store=None):
        self.settings = settings or WorkflowSettings.from_env()
        self.repository = repository or SqliteWorkflowRepository(self.settings.database_path)
        self.lease_store = lease_store or RedisLeaseStore.from_settings(self.settings)
        if getattr(self.lease_store, "client", None) is None and not isinstance(self.lease_store, InMemoryLeaseStore):
            self.lease_store = InMemoryLeaseStore()
        self.events = WorkflowEventBus(self.repository)
        self.tasks = WorkflowTaskRunner(self, self.settings)

    def start_game(self, game_id: str) -> dict[str, Any]:
        existing = self.repository.get_game_state(game_id)
        if existing:
            text_node = self.repository.get_text_node(game_id, "101")
            image_task = self.repository.get_image_task(game_id, "101")
            return {
                "game_id": game_id,
                "active_branch_id": existing.active_branch_id,
                "text_node": text_node.to_dict() if text_node else None,
                "image_task": image_task.to_dict() if image_task else None,
                "stream_url": f"/games/{game_id}/stream",
            }

        now = self._utc_now()
        game_state = GameState(
            game_id=game_id,
            active_branch_id="b0",
            current_scene_id=1,
            turn_in_scene=0,
            scene_switch_threshold=self.settings.scene_switch_threshold,
            status=GameStatus.ACTIVE.value,
            created_at=now,
            updated_at=now,
        )
        branch = BranchState(
            game_id=game_id,
            branch_id="b0",
            scene_id=1,
            status=BranchStatus.ACTIVE.value,
            depth=0,
            created_at=now,
            updated_at=now,
        )
        self.repository.save_game_state(game_state)
        self.repository.save_branch_state(branch)
        text_node = self.generate_text_node(branch_id="b0", text_id="101", priority="high")
        image_task = self.trigger_image_if_needed(branch_id="b0", current_text_id="101", priority="high")
        return {
            "game_id": game_id,
            "active_branch_id": "b0",
            "text_node": text_node.to_dict(),
            "image_task": image_task.to_dict() if image_task else None,
            "stream_url": f"/games/{game_id}/stream",
        }

    def generate_text_node(self, branch_id: str, text_id: str, priority: str = "high") -> TextNode:
        branch = self._require_branch(branch_id)
        idem_key = f"idem:text:{branch.game_id}:{branch_id}:{text_id}"
        lease = self.lease_store.acquire(idem_key, "generating", 60)
        existing = self.repository.get_text_node(branch.game_id, text_id)
        if existing and existing.status in {TextNodeStatus.READY.value, TextNodeStatus.CONSUMED.value}:
            return existing
        if not lease.acquired and existing:
            return existing

        parsed = parse_text_id(text_id)
        now = self._utc_now()
        if existing is None:
            node = TextNode(
                game_id=branch.game_id,
                text_id=text_id,
                scene_id=parsed.scene_id,
                image_index_in_scene=parsed.image_index_in_scene,
                branch_id=branch.branch_id,
                parent_text_id=branch.current_text_id,
                content="",
                options=[],
                status=TextNodeStatus.PENDING.value,
                is_scene_entry=parsed.image_index_in_scene == 1,
                created_at=now,
                updated_at=now,
            )
        else:
            node = existing

        ensure_text_transition(node.status, TextNodeStatus.GENERATING.value)
        node.status = TextNodeStatus.GENERATING.value
        node.updated_at = now
        self.repository.save_text_node(node)

        node.content = self._build_text_content(branch, node)
        node.options = self._build_option_refs(branch.branch_id, node.text_id)
        ensure_text_transition(node.status, TextNodeStatus.READY.value)
        node.status = TextNodeStatus.READY.value
        node.updated_at = self._utc_now()
        self.repository.save_text_node(node)

        branch.current_text_id = node.text_id
        branch.scene_id = node.scene_id
        branch.updated_at = node.updated_at
        self.repository.save_branch_state(branch)

        self.events.emit(
            "text.generated",
            {
                "game_id": node.game_id,
                "branch_id": node.branch_id,
                "text_id": node.text_id,
                "scene_id": node.scene_id,
                "image_index_in_scene": node.image_index_in_scene,
                "parent_text_id": node.parent_text_id,
                "is_scene_entry": node.is_scene_entry,
                "option_count": len(node.options),
                "content": node.content,
                "priority": priority,
            },
            publish_to_sse=True,
        )
        self.lease_store.mark_completed(idem_key, "ready", 3600)
        return node

    def trigger_image_if_needed(self, branch_id: str, current_text_id: str, priority: str = "high") -> ImageTask | None:
        branch = self._require_branch(branch_id)
        if not should_trigger_image(branch.last_anchor_text_id, current_text_id):
            return None
        event = self.events.emit(
            "image.triggered",
            {
                "game_id": branch.game_id,
                "branch_id": branch.branch_id,
                "anchor_text_id": current_text_id,
                "scene_id": parse_text_id(current_text_id).scene_id,
                "deps": build_image_deps(
                    branch.game_id,
                    prev_scene_image=branch.last_scene_image_id,
                    scene_anchor=branch.last_scene_image_id,
                ).__dict__,
                "reason": "rule.match",
                "priority": priority,
            },
            publish_to_sse=False,
        )
        return self.generate_image(anchor_text_id=current_text_id, branch_id=branch_id, priority=priority, emitted_event=event)

    def generate_image(
        self,
        *,
        anchor_text_id: str,
        branch_id: str,
        priority: str = "high",
        emitted_event: dict[str, Any] | None = None,
    ) -> ImageTask:
        branch = self._require_branch(branch_id)
        existing = self.repository.get_image_task(branch.game_id, anchor_text_id)
        idem_key = f"idem:image:{branch.game_id}:{anchor_text_id}"
        lease = self.lease_store.acquire(idem_key, "generating", 120)
        if existing and existing.status == ImageTaskStatus.READY.value:
            return existing
        if not lease.acquired and existing:
            return existing

        parsed = parse_text_id(anchor_text_id)
        deps = build_image_deps(
            branch.game_id,
            prev_scene_image=branch.last_scene_image_id,
            scene_anchor=branch.last_scene_image_id,
        )
        now = self._utc_now()
        task = existing or ImageTask(
            game_id=branch.game_id,
            anchor_text_id=anchor_text_id,
            scene_id=parsed.scene_id,
            branch_id=branch.branch_id,
            deps=deps,
            created_at=now,
            updated_at=now,
        )
        ensure_image_transition(task.status, ImageTaskStatus.QUEUED.value)
        task.status = ImageTaskStatus.QUEUED.value
        task.updated_at = now
        self.repository.save_image_task(task)

        ensure_image_transition(task.status, ImageTaskStatus.GENERATING.value)
        task.status = ImageTaskStatus.GENERATING.value
        task.updated_at = self._utc_now()
        self.repository.save_image_task(task)

        result_url = self._render_placeholder_image(branch.game_id, anchor_text_id, branch.branch_id)
        latest_branch = self._require_branch(branch_id)
        if latest_branch.status != BranchStatus.ACTIVE.value:
            task.status = ImageTaskStatus.ABANDONED.value
            task.cancel_requested = True
            task.updated_at = self._utc_now()
            self.repository.save_image_task(task)
            return task

        ensure_image_transition(task.status, ImageTaskStatus.READY.value)
        task.status = ImageTaskStatus.READY.value
        task.result_url = result_url
        task.updated_at = self._utc_now()
        self.repository.save_image_task(task)

        branch.last_anchor_text_id = anchor_text_id
        branch.last_scene_image_id = result_url
        branch.scene_id = parsed.scene_id
        branch.updated_at = task.updated_at
        self.repository.save_branch_state(branch)

        text_node = self.repository.get_text_node(branch.game_id, anchor_text_id)
        if text_node:
            text_node.anchor_image_task_id = image_task_pk(branch.game_id, anchor_text_id)
            text_node.updated_at = task.updated_at
            self.repository.save_text_node(text_node)

        payload = {
            "game_id": branch.game_id,
            "branch_id": branch.branch_id,
            "anchor_text_id": anchor_text_id,
            "scene_id": parsed.scene_id,
            "image_task_id": image_task_pk(branch.game_id, anchor_text_id),
            "result_url": result_url,
            "priority": priority,
        }
        if emitted_event:
            payload["trigger_event_id"] = emitted_event.get("event_id")
        self.events.emit("image.generated", payload, publish_to_sse=True)
        self.lease_store.mark_completed(idem_key, "ready", 3600)
        return task

    def next_text(self, game_id: str, branch_id: str, from_text_id: str) -> dict[str, Any]:
        branch = self._require_branch(branch_id, game_id=game_id)
        if branch.status != BranchStatus.ACTIVE.value:
            raise ValueError(f"branch {branch_id} is not active")
        parsed = parse_text_id(from_text_id)
        text_id = next_text_id(parsed.scene_id, parsed.image_index_in_scene)
        text_node = self.generate_text_node(branch_id=branch_id, text_id=text_id, priority="high")
        image_task = self.trigger_image_if_needed(branch_id=branch_id, current_text_id=text_id, priority="high")
        return {
            "text_node": text_node.to_dict(),
            "triggered_image_task_id": image_task_pk(game_id, image_task.anchor_text_id) if image_task else None,
        }

    def on_user_choice(self, game_id: str, branch_id: str, text_id: str, choice_index: int) -> dict[str, Any]:
        idem_key = f"idem:choice:{game_id}:{branch_id}:{text_id}:{choice_index}"
        lease = self.lease_store.acquire(idem_key, "running", 120)
        if not lease.acquired:
            state = self.get_state(game_id)
            return {
                "selected_branch_id": state["game_state"]["active_branch_id"],
                "abandoned_branch_ids": [],
                "next_text_node": None,
                "prepared_scene_summary": None,
            }

        game_state = self._require_game(game_id)
        branch = self._require_branch(branch_id, game_id=game_id)
        node = self.repository.get_text_node(game_id, text_id)
        if node is None:
            raise ValueError(f"text node not found: {text_id}")
        if node.status != TextNodeStatus.READY.value:
            raise ValueError(f"text node {text_id} is not ready")
        if choice_index < 0 or choice_index >= len(node.options):
            raise ValueError("choice_index out of range")

        ensure_text_transition(node.status, TextNodeStatus.CONSUMED.value)
        node.status = TextNodeStatus.CONSUMED.value
        node.choice_index = choice_index
        node.updated_at = self._utc_now()
        self.repository.save_text_node(node)

        selected_option = node.options[choice_index]
        selected_branch = self.repository.get_branch_state(game_id, selected_option.branch_id)
        if selected_branch is None:
            selected_branch = BranchState(
                game_id=game_id,
                branch_id=selected_option.branch_id,
                scene_id=node.scene_id,
                status=BranchStatus.ACTIVE.value,
                current_text_id=node.text_id,
                last_anchor_text_id=branch.last_anchor_text_id,
                last_scene_image_id=branch.last_scene_image_id,
                depth=branch.depth + 1,
                created_at=self._utc_now(),
                updated_at=self._utc_now(),
            )
        else:
            selected_branch.status = BranchStatus.ACTIVE.value
            selected_branch.current_text_id = node.text_id
            selected_branch.scene_id = node.scene_id
            selected_branch.last_anchor_text_id = branch.last_anchor_text_id
            selected_branch.last_scene_image_id = branch.last_scene_image_id
            selected_branch.updated_at = self._utc_now()
        self.repository.save_branch_state(selected_branch)

        user_choice_event = self.events.emit(
            "user.choice.made",
            {
                "game_id": game_id,
                "branch_id": branch_id,
                "text_id": text_id,
                "chosen_option_index": choice_index,
                "next_branch_id": selected_option.branch_id,
            },
            publish_to_sse=False,
        )

        abandoned_branch_ids: list[str] = []
        for option in node.options:
            if option.branch_id == selected_option.branch_id:
                continue
            self.abandon_branch(option.branch_id, reason="user.not_selected")
            abandoned_branch_ids.append(option.branch_id)

        game_state.active_branch_id = selected_option.branch_id
        game_state.current_scene_id = node.scene_id
        game_state.turn_in_scene += 1
        game_state.updated_at = self._utc_now()
        self.repository.save_game_state(game_state)

        prepared_scene_summary = None
        next_text_node = None
        if should_prepare_scene(game_state.turn_in_scene, game_state.scene_switch_threshold):
            prepared_scene_summary = self.prepare_next_scene(
                branch_id=selected_option.branch_id,
                to_scene_id=next_scene_id(node.scene_id),
                priority="low",
            )
            game_state.turn_in_scene = 0
            game_state.current_scene_id = next_scene_id(node.scene_id)
            game_state.updated_at = self._utc_now()
            self.repository.save_game_state(game_state)
        else:
            next_text_node = self.generate_text_node(
                branch_id=selected_option.branch_id,
                text_id=next_text_id(node.scene_id, parse_text_id(node.text_id).image_index_in_scene),
                priority="high",
            )
            self.trigger_image_if_needed(
                branch_id=selected_option.branch_id,
                current_text_id=next_text_node.text_id,
                priority="high",
            )

        self.lease_store.mark_completed(idem_key, user_choice_event["event_id"], 3600)
        return {
            "selected_branch_id": selected_option.branch_id,
            "abandoned_branch_ids": abandoned_branch_ids,
            "next_text_node": next_text_node.to_dict() if next_text_node else None,
            "prepared_scene_summary": prepared_scene_summary,
        }

    def prepare_next_scene(self, branch_id: str, to_scene_id: int, priority: str = "low") -> dict[str, Any]:
        branch = self._require_branch(branch_id)
        idem_key = f"idem:scene_prepare:{branch.game_id}:{branch_id}:{to_scene_id}"
        lease = self.lease_store.acquire(idem_key, "running", 300)
        if not lease.acquired:
            return {
                "from_scene_id": branch.scene_id,
                "to_scene_id": to_scene_id,
                "prepared_branch_ids": [],
                "prepared_text_ids": [],
            }

        labels = [
            f"Transition into scene {to_scene_id} through the bold route",
            f"Transition into scene {to_scene_id} through the cautious route",
        ]
        option_refs = build_scene_option_refs(branch.branch_id, labels)
        prepared_branch_ids: list[str] = []
        prepared_text_ids: list[str] = []
        summary_items: list[dict[str, Any]] = []
        for option in option_refs:
            prepared_branch = self.repository.get_branch_state(branch.game_id, option.branch_id)
            if prepared_branch is None:
                prepared_branch = BranchState(
                    game_id=branch.game_id,
                    branch_id=option.branch_id,
                    scene_id=to_scene_id,
                    status=BranchStatus.ACTIVE.value,
                    current_text_id=None,
                    last_anchor_text_id=None,
                    last_scene_image_id=branch.last_scene_image_id,
                    depth=branch.depth + 1,
                    created_at=self._utc_now(),
                    updated_at=self._utc_now(),
                )
            self.repository.save_branch_state(prepared_branch)
            text_id = next_text_id(to_scene_id, None)
            text_node = self.generate_text_node(branch_id=option.branch_id, text_id=text_id, priority=priority)
            image_task = self.generate_image(anchor_text_id=text_id, branch_id=option.branch_id, priority=priority)
            prepared_branch_ids.append(option.branch_id)
            prepared_text_ids.append(text_node.text_id)
            summary_items.append({
                "branch_id": option.branch_id,
                "text_id": text_node.text_id,
                "image_task_id": image_task_pk(branch.game_id, text_node.text_id),
            })

        event = self.events.emit(
            "scene.switch.prepared",
            {
                "game_id": branch.game_id,
                "from_scene_id": branch.scene_id,
                "to_scene_id": to_scene_id,
                "source_branch_id": branch.branch_id,
                "prepared_branch_ids": prepared_branch_ids,
                "prepared_text_ids": prepared_text_ids,
            },
            publish_to_sse=True,
        )
        self.lease_store.mark_completed(idem_key, event["event_id"], 3600)
        return {
            "from_scene_id": branch.scene_id,
            "to_scene_id": to_scene_id,
            "prepared_branch_ids": prepared_branch_ids,
            "prepared_text_ids": prepared_text_ids,
            "items": summary_items,
        }

    def abandon_branch(self, branch_id: str, reason: str = "branch.abandoned") -> dict[str, Any]:
        branch = self._find_branch(branch_id)
        if branch is None:
            game_id = branch_id.split(":", 1)[0] if ":" in branch_id else ""
            payload = {
                "game_id": game_id,
                "branch_id": branch_id,
                "reason": reason,
                "abandoned_text_ids": [],
                "abandoned_image_task_ids": [],
            }
            self.events.emit("branch.abandoned", payload, publish_to_sse=True)
            return payload

        abandoned_text_ids, abandoned_image_task_ids = mark_branch_abandoned(
            self.repository, branch.game_id, branch_id
        )
        payload = {
            "game_id": branch.game_id,
            "branch_id": branch_id,
            "reason": reason,
            "abandoned_text_ids": abandoned_text_ids,
            "abandoned_image_task_ids": abandoned_image_task_ids,
        }
        self.events.emit("branch.abandoned", payload, publish_to_sse=True)
        return payload

    def get_state(self, game_id: str) -> dict[str, Any]:
        game_state = self._require_game(game_id)
        branches = self.repository.list_branch_states(game_id)
        text_nodes = self.repository.list_text_nodes(game_id)
        image_tasks = self.repository.list_image_tasks(game_id)
        prepared_events = self.repository.list_events(game_id, "scene.switch.prepared")
        return {
            "game_state": game_state.to_dict(),
            "active_branches": [b.to_dict() for b in branches if b.status == BranchStatus.ACTIVE.value],
            "latest_text_nodes": [node.to_dict() for node in text_nodes[-10:]],
            "latest_image_tasks": [task.to_dict() for task in image_tasks[-10:]],
            "scene_prepare_status": prepared_events[-1] if prepared_events else None,
        }

    def _build_option_refs(self, branch_id: str, text_id: str) -> list[OptionRef]:
        parsed = parse_text_id(text_id)
        labels = [
            f"Push branch {branch_id} toward conflict at {text_id}",
            f"Probe branch {branch_id} for hidden context at {text_id}",
        ]
        return [
            OptionRef(index=index, label=label, branch_id=child_branch_id(branch_id, index))
            for index, label in enumerate(labels)
        ]

    def _build_text_content(self, branch: BranchState, node: TextNode) -> str:
        return (
            f"Scene {node.scene_id}, text {node.text_id}, branch {branch.branch_id}. "
            f"This beat extends the active storyline in a deterministic MVP workflow."
        )

    def _render_placeholder_image(self, game_id: str, anchor_text_id: str, branch_id: str) -> str:
        output_dir = Path("image_cache") / "workflow"
        output_dir.mkdir(parents=True, exist_ok=True)
        file_name = f"{game_id}_{anchor_text_id}_{branch_id.replace('.', '_')}.png"
        file_path = output_dir / file_name
        if file_path.exists():
            return f"/image_cache/workflow/{file_name}"
        if Image is None:
            file_path.write_bytes(b"")
            return f"/image_cache/workflow/{file_name}"
        image = Image.new("RGB", (1024, 768), color=(28, 36, 58))
        draw = ImageDraw.Draw(image)
        lines = [
            f"Game: {game_id}",
            f"Anchor: {anchor_text_id}",
            f"Branch: {branch_id}",
            "Workflow placeholder image",
        ]
        y = 120
        for line in lines:
            draw.text((80, y), line, fill=(240, 240, 240))
            y += 80
        image.save(file_path)
        return f"/image_cache/workflow/{file_name}"

    def _require_game(self, game_id: str) -> GameState:
        state = self.repository.get_game_state(game_id)
        if state is None:
            raise ValueError(f"game not found: {game_id}")
        return state

    def _find_branch(self, branch_id: str) -> BranchState | None:
        for game_state in []:
            _ = game_state
        # SQLite repo indexes by (game_id, branch_id), so scan is simplest for MVP.
        repo = self.repository
        if hasattr(repo, "_conn"):
            pass
        for maybe_game in self._list_known_games():
            branch = repo.get_branch_state(maybe_game, branch_id)
            if branch is not None:
                return branch
        return None

    def _require_branch(self, branch_id: str, game_id: str | None = None) -> BranchState:
        if game_id:
            branch = self.repository.get_branch_state(game_id, branch_id)
            if branch is not None:
                return branch
        branch = self._find_branch(branch_id)
        if branch is None:
            raise ValueError(f"branch not found: {branch_id}")
        return branch

    def _list_known_games(self) -> list[str]:
        repo = self.repository
        if hasattr(repo, "_conn"):
            with repo._conn() as conn:
                rows = conn.execute("SELECT game_id FROM game_states ORDER BY game_id").fetchall()
            return [row[0] for row in rows]
        return []

    def _utc_now(self):
        return datetime.now(timezone.utc)


_workflow_service: WorkflowOrchestrator | None = None



def get_workflow_service() -> WorkflowOrchestrator:
    global _workflow_service
    if _workflow_service is None:
        _workflow_service = WorkflowOrchestrator()
    return _workflow_service
