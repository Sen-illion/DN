from __future__ import annotations

import queue

from flask import Blueprint, Response, jsonify, request, stream_with_context

from server.events import subscribe, unsubscribe

from .orchestrator import WorkflowOrchestrator, get_workflow_service



def create_workflow_blueprint(service: WorkflowOrchestrator | None = None) -> Blueprint:
    blueprint = Blueprint("workflow", __name__)

    def workflow() -> WorkflowOrchestrator:
        return service or get_workflow_service()

    @blueprint.post("/games/<game_id>/start")
    def start_game(game_id: str):
        try:
            return jsonify(workflow().start_game(game_id))
        except Exception as exc:
            return jsonify({"error": str(exc)}), 400

    @blueprint.post("/games/<game_id>/next-text")
    def next_text(game_id: str):
        try:
            data = request.get_json(silent=True) or {}
            result = workflow().next_text(
                game_id=game_id,
                branch_id=str(data.get("branch_id") or ""),
                from_text_id=str(data.get("from_text_id") or ""),
            )
            return jsonify(result)
        except Exception as exc:
            return jsonify({"error": str(exc)}), 400

    @blueprint.post("/games/<game_id>/choice")
    def choice(game_id: str):
        try:
            data = request.get_json(silent=True) or {}
            result = workflow().on_user_choice(
                game_id=game_id,
                branch_id=str(data.get("branch_id") or ""),
                text_id=str(data.get("text_id") or ""),
                choice_index=int(data.get("choice_index", 0)),
            )
            return jsonify(result)
        except Exception as exc:
            return jsonify({"error": str(exc)}), 400

    @blueprint.get("/games/<game_id>/state")
    def state(game_id: str):
        try:
            return jsonify(workflow().get_state(game_id))
        except Exception as exc:
            return jsonify({"error": str(exc)}), 404

    @blueprint.get("/games/<game_id>/stream")
    def stream(game_id: str):
        event_queue = subscribe("", game_id=game_id)

        def gen():
            yield "event: hello\ndata: {}\n\n"
            try:
                while True:
                    try:
                        yield event_queue.get(timeout=15.0)
                    except queue.Empty:
                        yield "event: ping\ndata: {}\n\n"
            finally:
                unsubscribe("", event_queue, game_id=game_id)

        return Response(
            stream_with_context(gen()),
            mimetype="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
                "Connection": "keep-alive",
            },
        )

    return blueprint


workflow_blueprint = create_workflow_blueprint()
