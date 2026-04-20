from __future__ import annotations

from datetime import datetime, timezone

from .enums import BranchStatus, ImageTaskStatus, TextNodeStatus


def child_branch_id(branch_id: str, choice_index: int) -> str:
    return f"{branch_id}.{choice_index + 1}"



def is_branch_descendant(candidate: str, root: str) -> bool:
    return candidate == root or candidate.startswith(root + ".")



def utc_now():
    return datetime.now(timezone.utc)



def mark_branch_abandoned(repository, game_id: str, branch_id: str) -> tuple[list[str], list[str]]:
    now = utc_now()
    abandoned_text_ids: list[str] = []
    abandoned_image_task_ids: list[str] = []

    for branch in repository.list_branch_states(game_id):
        if not is_branch_descendant(branch.branch_id, branch_id):
            continue
        if branch.status != BranchStatus.ABANDONED.value:
            branch.status = BranchStatus.ABANDONED.value
            branch.updated_at = now
            repository.save_branch_state(branch)

    for node in repository.list_text_nodes(game_id):
        if not is_branch_descendant(node.branch_id, branch_id):
            continue
        if node.status in {
            TextNodeStatus.PENDING.value,
            TextNodeStatus.GENERATING.value,
            TextNodeStatus.READY.value,
        }:
            node.status = TextNodeStatus.ABANDONED.value
            node.updated_at = now
            repository.save_text_node(node)
            abandoned_text_ids.append(node.text_id)

    for task in repository.list_image_tasks(game_id):
        if not is_branch_descendant(task.branch_id, branch_id):
            continue
        if task.status in {
            ImageTaskStatus.PENDING.value,
            ImageTaskStatus.QUEUED.value,
            ImageTaskStatus.GENERATING.value,
        }:
            task.cancel_requested = True
            task.status = ImageTaskStatus.ABANDONED.value
            task.updated_at = now
            repository.save_image_task(task)
            abandoned_image_task_ids.append(task.anchor_text_id)

    return abandoned_text_ids, abandoned_image_task_ids
