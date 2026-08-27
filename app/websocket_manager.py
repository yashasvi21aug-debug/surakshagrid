from __future__ import annotations

from collections.abc import Iterable

from fastapi import WebSocket


class ConnectionManager:
    def __init__(self) -> None:
        self.active_connections: set[WebSocket] = set()

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections.add(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        self.active_connections.discard(websocket)

    async def broadcast(self, payload: dict) -> None:
        await self._send_to_all([payload])

    async def broadcast_many(self, payloads: Iterable[dict]) -> None:
        await self._send_to_all(list(payloads))

    async def _send_to_all(self, payloads: list[dict]) -> None:
        dead_connections: list[WebSocket] = []
        for socket in list(self.active_connections):
            try:
                for payload in payloads:
                    await socket.send_json(payload)
            except Exception:
                dead_connections.append(socket)
        for socket in dead_connections:
            self.disconnect(socket)


manager = ConnectionManager()
