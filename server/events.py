#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SSE (Server-Sent Events) event hub.

用途：当后台线程生成剧情图完成后，主动推送给前端，避免前端“等下一次请求才看到图片”。
"""

from __future__ import annotations

import json
import queue
import threading
import time
from typing import Any, Dict, Optional, Set, Tuple

# key: (scene_id or "", game_id or "")
_subscribers: Dict[Tuple[str, str], Set["queue.Queue[str]"]] = {}
_lock = threading.Lock()


def subscribe(scene_id: Optional[str], game_id: Optional[str] = None) -> "queue.Queue[str]":
    """
    返回一个 Queue，内部存放已编码好的 SSE data 行（不包含 event:，只发 data:）。
    scene_id/game_id 为空时也允许订阅（作为兜底/调试），但建议至少传 scene_id。
    """
    sid = str(scene_id or "")
    gid = str(game_id or "")
    q: "queue.Queue[str]" = queue.Queue(maxsize=50)
    with _lock:
        key = (sid, gid)
        if key not in _subscribers:
            _subscribers[key] = set()
        _subscribers[key].add(q)
    return q


def unsubscribe(scene_id: Optional[str], q: "queue.Queue[str]", game_id: Optional[str] = None) -> None:
    sid = str(scene_id or "")
    gid = str(game_id or "")
    with _lock:
        key = (sid, gid)
        if key in _subscribers and q in _subscribers[key]:
            _subscribers[key].remove(q)
            if not _subscribers[key]:
                _subscribers.pop(key, None)


def publish(event: Dict[str, Any]) -> None:
    """
    广播事件。
    推荐 event 字段：
    - type: "scene_image_ready"
    - sceneId: str
    - optionIndex: int
    - image: { url, prompt?, ... } 或 url
    - ts: float
    """
    try:
        payload = dict(event or {})
        if "ts" not in payload:
            payload["ts"] = time.time()
        sid = str(payload.get("sceneId") or payload.get("scene_id") or "")
        gid = str(payload.get("gameId") or payload.get("game_id") or "")
        data = json.dumps(payload, ensure_ascii=False)
        line = f"data: {data}\n\n"
    except Exception:
        return

    # 仅推送给 (scene_id, game_id) 精确匹配的订阅者；
    # 同时也推送给 scene_id 匹配但 game_id 为空的订阅者（兼容旧前端/未传 gameId）。
    targets: Set["queue.Queue[str]"] = set()
    with _lock:
        exact = _subscribers.get((sid, gid))
        if exact:
            targets |= set(exact)
        fallback = _subscribers.get((sid, ""))
        if fallback:
            targets |= set(fallback)

    for q in targets:
        try:
            q.put_nowait(line)
        except queue.Full:
            # 丢弃最旧的一条，尽量保证最新图能进队列
            try:
                _ = q.get_nowait()
            except Exception:
                pass
            try:
                q.put_nowait(line)
            except Exception:
                pass

