# Workflow API

## Endpoints

### POST /games/{game_id}/start
Starts a workflow game, creates `101`, and triggers the first image task.

### POST /games/{game_id}/next-text
Body:
```json
{
  "branch_id": "b0.1",
  "from_text_id": "101"
}
```

### POST /games/{game_id}/choice
Body:
```json
{
  "branch_id": "b0",
  "text_id": "101",
  "choice_index": 0
}
```

### GET /games/{game_id}/state
Returns the latest workflow snapshot.

### GET /games/{game_id}/stream
SSE stream for `text.generated`, `image.generated`, `scene.switch.prepared`, and `branch.abandoned`.

## Event payload highlights
- `text.generated`: `game_id`, `branch_id`, `text_id`, `scene_id`, `content`
- `image.generated`: `game_id`, `branch_id`, `anchor_text_id`, `result_url`
- `scene.switch.prepared`: `from_scene_id`, `to_scene_id`, `prepared_branch_ids`
- `branch.abandoned`: `branch_id`, `abandoned_text_ids`, `abandoned_image_task_ids`
