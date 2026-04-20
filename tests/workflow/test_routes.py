import unittest
from pathlib import Path

from flask import Flask

from server.workflow.config import WorkflowSettings
from server.workflow.orchestrator import WorkflowOrchestrator
from server.workflow.redis_store import InMemoryLeaseStore
from server.workflow.routes import create_workflow_blueprint
from server.workflow.sql_store import SqliteWorkflowRepository



def build_app(tmp_dir: Path):
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
    service = WorkflowOrchestrator(
        settings=settings,
        repository=SqliteWorkflowRepository(settings.database_path),
        lease_store=InMemoryLeaseStore(),
    )
    app = Flask(__name__)
    app.config["TESTING"] = True
    app.register_blueprint(create_workflow_blueprint(service))
    return app, service


class TestRoutes(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = Path("data") / "test_routes"
        self.tmp_dir.mkdir(parents=True, exist_ok=True)
        db_path = self.tmp_dir / "workflow.db"
        if db_path.exists():
            db_path.unlink()
        self.app, self.service = build_app(self.tmp_dir)

    def test_start_route_returns_first_text_and_image_task(self):
        client = self.app.test_client()
        response = client.post("/games/game_routes/start")
        payload = response.get_json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["active_branch_id"], "b0")
        self.assertEqual(payload["text_node"]["text_id"], "101")
        self.assertEqual(payload["image_task"]["anchor_text_id"], "101")

    def test_choice_route_returns_selected_and_abandoned_branches(self):
        client = self.app.test_client()
        client.post("/games/game_choice/start")
        response = client.post(
            "/games/game_choice/choice",
            json={"branch_id": "b0", "text_id": "101", "choice_index": 0},
        )
        payload = response.get_json()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(payload["selected_branch_id"], "b0.1")
        self.assertEqual(payload["abandoned_branch_ids"], ["b0.2"])

    def test_stream_route_receives_image_generated_event(self):
        stream_client = self.app.test_client()
        event_client = self.app.test_client()

        response = stream_client.get("/games/game_stream/stream", buffered=False)
        first_chunk = next(response.response).decode("utf-8")
        self.assertIn("event: hello", first_chunk)

        event_client.post("/games/game_stream/start")

        chunks = []
        for _ in range(6):
            chunks.append(next(response.response).decode("utf-8"))
            if any("image.generated" in chunk for chunk in chunks):
                break

        joined = "".join(chunks)
        self.assertIn("image.generated", joined)
        self.assertIn("game_stream", joined)


if __name__ == "__main__":
    unittest.main()
