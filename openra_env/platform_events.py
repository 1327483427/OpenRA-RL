"""In-memory event stream used by external MCP agents and the web console."""

from __future__ import annotations

import asyncio
import time
import uuid
from collections import deque
from typing import Any


SENSITIVE_PARTS = ("api_key", "apikey", "authorization", "password", "secret", "token")


def compact_payload(value: Any, depth: int = 0) -> Any:
    """Bound event payload size and remove credentials before browser display."""
    if depth >= 4:
        return "<truncated>"
    if isinstance(value, dict):
        result = {}
        for index, (key, item) in enumerate(value.items()):
            if index >= 30:
                result["..."] = f"{len(value) - index} more fields"
                break
            if any(part in str(key).lower() for part in SENSITIVE_PARTS):
                result[str(key)] = "<redacted>"
            elif str(key) in {"spatial_map", "heightMap", "terrain", "visible", "explored"}:
                result[str(key)] = "<large field omitted>"
            else:
                result[str(key)] = compact_payload(item, depth + 1)
        return result
    if isinstance(value, (list, tuple)):
        items = [compact_payload(item, depth + 1) for item in value[:30]]
        if len(value) > 30:
            items.append(f"<{len(value) - 30} more items>")
        return items
    if isinstance(value, str) and len(value) > 1000:
        return value[:1000] + "..."
    return value


class AgentEventHub:
    """Fan out a bounded event history to Server-Sent Event subscribers."""

    def __init__(self, max_events: int = 1000):
        self._events: deque[dict[str, Any]] = deque(maxlen=max_events)
        self._subscribers: set[asyncio.Queue] = set()

    def publish(self, event: dict[str, Any]) -> dict[str, Any]:
        normalized = compact_payload(event)
        normalized.setdefault("id", str(uuid.uuid4()))
        normalized.setdefault("timestamp", time.time())
        self._events.append(normalized)
        for queue in list(self._subscribers):
            try:
                queue.put_nowait(normalized)
            except asyncio.QueueFull:
                try:
                    queue.get_nowait()
                    queue.put_nowait(normalized)
                except (asyncio.QueueEmpty, asyncio.QueueFull):
                    pass
        return normalized

    def recent(self, limit: int = 200) -> list[dict[str, Any]]:
        return list(self._events)[-max(0, min(limit, len(self._events))):]

    def subscribe(self) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue(maxsize=500)
        self._subscribers.add(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue) -> None:
        self._subscribers.discard(queue)

    def clear(self) -> None:
        self._events.clear()
