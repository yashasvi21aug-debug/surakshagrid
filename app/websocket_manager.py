from __future__ import annotations

import asyncio
import logging
from collections.abc import Iterable
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Thread-safe, room-based WebSocket connection manager with dropped connection cleanup."""

    def __init__(self) -> None:
        self.active_connections: set[WebSocket] = set()
        self.rooms: dict[str, set[WebSocket]] = {
            "dashboard": set(),
            "responders": set(),
            "citizens": set(),
            "global": set(),
        }
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, room: str = "global") -> None:
        """Accept connection and register websocket to designated room."""
        await websocket.accept()
        async with self._lock:
            self.active_connections.add(websocket)
            if room not in self.rooms:
                self.rooms[room] = set()
            self.rooms[room].add(websocket)
        logger.info("WebSocket connected to room '%s' (total active: %d)", room, len(self.active_connections))

    def disconnect(self, websocket: WebSocket, room: str | None = None) -> None:
        """Remove websocket from active connections and rooms."""
        self.active_connections.discard(websocket)
        if room and room in self.rooms:
            self.rooms[room].discard(websocket)
        else:
            for r_set in self.rooms.values():
                r_set.discard(websocket)

    async def broadcast(self, payload: dict[str, Any], room: str = "global") -> None:
        """Broadcast payload to all websockets in specified room or global."""
        await self.broadcast_to_rooms(payload, [room] if room != "global" else list(self.rooms.keys()))

    async def broadcast_to_rooms(self, payload: dict[str, Any], rooms: Iterable[str]) -> None:
        """Broadcast payload to specified rooms."""
        target_sockets: set[WebSocket] = set()
        async with self._lock:
            for r in rooms:
                if r in self.rooms:
                    target_sockets.update(self.rooms[r])
            if not rooms or "global" in rooms:
                target_sockets.update(self.active_connections)

        if not target_sockets:
            return

        dead_connections: list[WebSocket] = []
        for socket in list(target_sockets):
            try:
                await socket.send_json(payload)
            except (WebSocketDisconnect, RuntimeError, Exception):
                dead_connections.append(socket)

        if dead_connections:
            async with self._lock:
                for socket in dead_connections:
                    self.disconnect(socket)

    async def broadcast_many(self, payloads: Iterable[dict[str, Any]], room: str = "global") -> None:
        """Broadcast multiple payloads sequentially."""
        for payload in payloads:
            await self.broadcast(payload, room=room)


manager = ConnectionManager()
