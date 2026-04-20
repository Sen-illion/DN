import unittest
from pathlib import Path

from server.workflow.config import WorkflowSettings
from server.workflow.orchestrator import WorkflowOrchestrator
from server.workflow.redis_store import InMemoryLeaseStore
from server.workflow.sql_store import SqliteWorkflowRepository



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


class TestScenePrepare(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = Path("data") / "test_scene_prepare"
        self.tmp_dir.mkdir(parents=True, exist_ok=True)
        db_path = self.tmp_dir / "workflow.db"
        if db_path.exists():
            db_path.unlink()
        self.service = build_service(self.tmp_dir)

    def test_prepare_next_scene_after_threshold(self):
        self.service.start_game("game_scene")

        game_state = self.service.repository.get_game_state("game_scene")
        self.assertIsNotNone(game_state)
        game_state.turn_in_scene = self.service.settings.scene_switch_threshold - 1
        self.service.repository.save_game_state(game_state)

        result = self.service.on_user_choice("game_scene", "b0", "101", 0)
        prepared = result["prepared_scene_summary"]

        self.assertIsNotNone(prepared)
        self.assertEqual(prepared["to_scene_id"], 2)
        self.assertEqual(len(prepared["prepared_branch_ids"]), 2)
        self.assertTrue(all(text_id == "201" for text_id in prepared["prepared_text_ids"]))

        for item in prepared["items"]:
            image_task = self.service.repository.get_image_task("game_scene", item["text_id"])
            self.assertIsNotNone(image_task)
            self.assertIsNotNone(image_task.deps.prev_scene_image)
            self.assertIsInstance(image_task.deps.character_refs, list)
            self.assertIsNotNone(image_task.deps.scene_anchor)


if __name__ == "__main__":
    unittest.main()
