#!/usr/bin/env python3
from __future__ import annotations

import json
import queue
import threading
import time
from typing import Any, Dict, Optional, Set, Tuple

_subscribers: Dict[Tuple[str, str], Set["queue.Queue[str]"]] = {}
_lock = threading.Lock()



def subscribe(scene_id: Optional[str], game_id: Optional[str] = None) -> "queue.Queue[str]":
    sid = str(scene_id or "")
    gid = str(game_id or "")
    q: "queue.Queue[str]" = queue.Queue(maxsize=50)
    with _lock:
        _subscribers.setdefault((sid, gid), set()).add(q)
    return q



def unsubscribe(scene_id: Optional[str], q: "queue.Queue[str]", game_id: Optional[str] = None) -> None:
    sid = str(scene_id or "")
    gid = str(game_id or "")
    with _lock:
        key = (sid, gid)
        listeners = _subscribers.get(key)
        if not listeners:
            return
        listeners.discard(q)
        if not listeners:
            _subscribers.pop(key, None)



def publish(event: Dict[str, Any]) -> None:
    try:
        payload = dict(event or {})
        payload.setdefault("ts", time.time())
        sid = str(payload.get("sceneId") or payload.get("scene_id") or "")
        gid = str(payload.get("gameId") or payload.get("game_id") or "")
        line = f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"
    except Exception:
        return

    targets: Set["queue.Queue[str]"] = set()
    with _lock:
        for key in ((sid, gid), (sid, ""), ("", gid)):
            listeners = _subscribers.get(key)
            if listeners:
                targets |= set(listeners)

    for q in targets:
        try:
            q.put_nowait(line)
        except queue.Full:
            try:
                q.get_nowait()
            except Exception:
                pass
            try:
                q.put_nowait(line)
            except Exception:
                pass
