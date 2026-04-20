TEXT_NODE_SCHEMA = {
    "type": "object",
    "required": [
        "game_id", "text_id", "scene_id", "image_index_in_scene", "branch_id",
        "parent_text_id", "content", "options", "status", "created_at", "updated_at"
    ],
    "properties": {
        "game_id": {"type": "string"},
        "text_id": {"type": "string", "pattern": "^[1-9][0-9]{2}$"},
        "scene_id": {"type": "integer"},
        "image_index_in_scene": {"type": "integer"},
        "branch_id": {"type": "string"},
        "parent_text_id": {"type": ["string", "null"]},
        "content": {"type": "string"},
        "options": {"type": "array"},
        "status": {"type": "string"},
        "choice_index": {"type": ["integer", "null"]},
        "is_scene_entry": {"type": "boolean"},
        "anchor_image_task_id": {"type": ["string", "null"]},
        "created_at": {"type": "string"},
        "updated_at": {"type": "string"}
    }
}

IMAGE_TASK_SCHEMA = {
    "type": "object",
    "required": [
        "game_id", "anchor_text_id", "scene_id", "branch_id", "deps", "status",
        "retry_count", "error", "created_at", "updated_at"
    ],
    "properties": {
        "game_id": {"type": "string"},
        "anchor_text_id": {"type": "string"},
        "scene_id": {"type": "integer"},
        "branch_id": {"type": "string"},
        "deps": {"type": "object"},
        "status": {"type": "string"},
        "retry_count": {"type": "integer"},
        "error": {"type": ["string", "null"]},
        "result_url": {"type": ["string", "null"]},
        "created_at": {"type": "string"},
        "updated_at": {"type": "string"}
    }
}

BRANCH_STATE_SCHEMA = {
    "type": "object",
    "required": [
        "game_id", "branch_id", "scene_id", "status", "current_text_id",
        "last_anchor_text_id", "last_scene_image_id", "depth", "created_at", "updated_at"
    ],
    "properties": {
        "game_id": {"type": "string"},
        "branch_id": {"type": "string"},
        "scene_id": {"type": "integer"},
        "status": {"type": "string"},
        "current_text_id": {"type": ["string", "null"]},
        "last_anchor_text_id": {"type": ["string", "null"]},
        "last_scene_image_id": {"type": ["string", "null"]},
        "depth": {"type": "integer"},
        "created_at": {"type": "string"},
        "updated_at": {"type": "string"}
    }
}
