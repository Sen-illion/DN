import json
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from pathlib import Path
from typing import Any


def _url(base_url: str, path: str) -> str:
    return base_url.rstrip("/") + path


def _read_json(request: urllib.request.Request, timeout: float) -> dict[str, Any]:
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"ComfyUI HTTP {exc.code}: {body}") from exc


def get_system_stats(base_url: str, timeout: float = 10.0) -> dict[str, Any]:
    request = urllib.request.Request(_url(base_url, "/system_stats"), method="GET")
    return _read_json(request, timeout)


def queue_prompt(base_url: str, prompt: dict[str, Any], client_id: str | None = None, timeout: float = 30.0) -> str:
    payload = json.dumps(
        {
            "prompt": prompt,
            "client_id": client_id or str(uuid.uuid4()),
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        _url(base_url, "/prompt"),
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    response = _read_json(request, timeout)
    prompt_id = response.get("prompt_id")
    if not prompt_id:
        raise RuntimeError(f"ComfyUI did not return a prompt_id: {response}")
    return str(prompt_id)


def get_history(base_url: str, prompt_id: str, timeout: float = 10.0) -> dict[str, Any]:
    quoted_id = urllib.parse.quote(prompt_id, safe="")
    request = urllib.request.Request(_url(base_url, f"/history/{quoted_id}"), method="GET")
    return _read_json(request, timeout)


def wait_for_history(base_url: str, prompt_id: str, timeout_seconds: float, poll_seconds: float = 1.0) -> dict[str, Any]:
    deadline = time.monotonic() + timeout_seconds
    last_response: dict[str, Any] = {}
    while time.monotonic() < deadline:
        last_response = get_history(base_url, prompt_id)
        if prompt_id in last_response:
            return last_response[prompt_id]
        time.sleep(poll_seconds)
    raise TimeoutError(f"Timed out after {timeout_seconds:.0f}s waiting for ComfyUI prompt {prompt_id}: {last_response}")


def image_refs_from_history(prompt_history: dict[str, Any]) -> list[dict[str, Any]]:
    refs: list[dict[str, Any]] = []
    for node_output in prompt_history.get("outputs", {}).values():
        for image in node_output.get("images", []):
            if image.get("filename"):
                refs.append(image)
    return refs


def download_image(base_url: str, image_ref: dict[str, Any], output_path: str | Path, timeout: float = 60.0) -> Path:
    query = urllib.parse.urlencode(
        {
            "filename": image_ref["filename"],
            "subfolder": image_ref.get("subfolder", ""),
            "type": image_ref.get("type", "output"),
        }
    )
    request = urllib.request.Request(_url(base_url, f"/view?{query}"), method="GET")
    out_path = Path(output_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            data = response.read()
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Could not download ComfyUI image ({exc.code}): {body}") from exc
    if not data:
        raise RuntimeError(f"Downloaded empty image for {image_ref}")
    out_path.write_bytes(data)
    return out_path
