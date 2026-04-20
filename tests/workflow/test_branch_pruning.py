import unittest
from pathlib import Path

from server.workflow.config import WorkflowSettings
from server.workflow.enums import ImageTaskStatus
from server.workflow.orchestrator import WorkflowOrchestrator
from server.workflow.redis_store import InMemoryLeaseStore
from server.workflow.sql_store import SqliteWorkflowRepository
from server.workflow.types import BranchState, ImageDeps, ImageTask



def build_service(tmp_dir: Path) -> WorkflowOrchestrator:
    settings = WorkflowSettings(
        database_path=str(tmp_dir / "workflow.db"),
        scene_switch_threshold=6,
        text_retry_schedule=(2, 5, 15),
        image_retry_schedule=(5, 15, 30, 60),
        scene_retry_schedule=(5, 15, 30),
        task_always_eager=True,
        broker_url="redis://localhost:6379/0",
        result_backend="redis://localhost:6379/1",
        use_real_image_generator=False,
    )
    return WorkflowOrchestrator(
        settings=settings,
        repository=SqliteWorkflowRepository(settings.database_path),
        lease_store=InMemoryLeaseStore(),
    )


class TestBranchPruning(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = Path("data") / "test_branch_pruning"
        self.tmp_dir.mkdir(parents=True, exist_ok=True)
        db_path = self.tmp_dir / "workflow.db"
        if db_path.exists():
            db_path.unlink()
        self.service = build_service(self.tmp_dir)

    def test_choice_abandons_unselected_sibling_branch_and_tasks(self):
        self.service.start_game("game_branch")

        sibling = BranchState(
            game_id="game_branch",
            branch_id="b0.2",
            scene_id=1,
            current_text_id="101",
            depth=1,
        )
        self.service.repository.save_branch_state(sibling)
        image_task = ImageTask(
            game_id="game_branch",
            anchor_text_id="103",
            scene_id=1,
            branch_id="b0.2",
            deps=ImageDeps(),
            status=ImageTaskStatus.QUEUED.value,
        )
        self.service.repository.save_image_task(image_task)

        result = self.service.on_user_choice("game_branch", "b0", "101", 0)

        self.assertEqual(result["selected_branch_id"], "b0.1")
        self.assertIn("b0.2", result["abandoned_branch_ids"])
        abandoned = self.service.repository.get_branch_state("game_branch", "b0.2")
        self.assertIsNotNone(abandoned)
        self.assertEqual(abandoned.status, "abandoned")
        image = self.service.repository.get_image_task("game_branch", "103")
        self.assertIsNotNone(image)
        self.assertEqual(image.status, "abandoned")
        self.assertTrue(image.cancel_requested)


if __name__ == "__main__":
    unittest.main()
