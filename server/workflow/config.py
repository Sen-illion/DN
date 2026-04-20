from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class WorkflowSettings:
    database_path: str
    scene_switch_threshold: int
    text_retry_schedule: tuple[int, ...]
    image_retry_schedule: tuple[int, ...]
    scene_retry_schedule: tuple[int, ...]
    task_always_eager: bool
    broker_url: str
    result_backend: str
    use_real_image_generator: bool

    @classmethod
    def from_env(cls) -> "WorkflowSettings":
        db_path = os.getenv("WORKFLOW_DB_PATH", str(Path("data") / "workflow.db"))
        return cls(
            database_path=db_path,
            scene_switch_threshold=max(5, min(6, int(os.getenv("WORKFLOW_SCENE_SWITCH_THRESHOLD", "6")))),
            text_retry_schedule=(2, 5, 15),
            image_retry_schedule=(5, 15, 30, 60),
            scene_retry_schedule=(5, 15, 30),
            task_always_eager=os.getenv("WORKFLOW_TASK_ALWAYS_EAGER", "true").lower() == "true",
            broker_url=os.getenv("WORKFLOW_CELERY_BROKER_URL", "redis://localhost:6379/0"),
            result_backend=os.getenv("WORKFLOW_CELERY_RESULT_BACKEND", "redis://localhost:6379/1"),
            use_real_image_generator=os.getenv("WORKFLOW_USE_REAL_IMAGE_GENERATOR", "false").lower() == "true",
        )
