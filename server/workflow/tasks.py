from __future__ import annotations

from dataclasses import dataclass

from .workers import build_celery_app


@dataclass
class WorkflowTaskRunner:
    service: any
    settings: any

    def __post_init__(self):
        self.celery_app = build_celery_app(self.settings)

    def dispatch_text(self, branch_id: str, text_id: str, priority: str = "high"):
        return self.service.generate_text_node(branch_id=branch_id, text_id=text_id, priority=priority)

    def dispatch_image(self, branch_id: str, anchor_text_id: str, priority: str = "high"):
        return self.service.generate_image(anchor_text_id=anchor_text_id, branch_id=branch_id, priority=priority)

    def dispatch_scene_prepare(self, branch_id: str, to_scene_id: int, priority: str = "low"):
        return self.service.prepare_next_scene(branch_id=branch_id, to_scene_id=to_scene_id, priority=priority)

    def dispatch_branch_prune(self, branch_id: str):
        return self.service.abandon_branch(branch_id=branch_id, reason="branch.prune")
