from __future__ import annotations

import asyncio
import logging
from collections.abc import Iterable
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Thread-safe, room- and channel-based WebSocket manager for low-latency (<200 ms) event broadcasting."""

    def __init__(self) -> None:
        self.active_connections: set[WebSocket] = set()
        self.rooms: dict[str, set[WebSocket]] = {
            "dashboard": set(),
            "responders": set(),
            "citizens": set(),
            "incidents": set(),
            "sensors": set(),
            "evacuation_corridors": set(),
            "global": set(),
        }
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, room: str = "global") -> None:
        """Accept connection and register websocket to designated room/channel."""
        await websocket.accept()
        async with self._lock:
            self.active_connections.add(websocket)
            if room not in self.rooms:
                self.rooms[room] = set()
            self.rooms[room].add(websocket)
        logger.info("WebSocket client connected to room '%s' (active: %d)", room, len(self.active_connections))

    def disconnect(self, websocket: WebSocket, room: str | None = None) -> None:
        """Remove websocket from active connections and rooms."""
        self.active_connections.discard(websocket)
        if room and room in self.rooms:
            self.rooms[room].discard(websocket)
        else:
            for r_set in self.rooms.values():
                r_set.discard(websocket)

    async def broadcast(self, payload: dict[str, Any], room: str = "global") -> None:
        """Broadcast payload to specified room or global connections."""
        await self.broadcast_to_rooms(payload, [room] if room != "global" else list(self.rooms.keys()))

    async def broadcast_to_rooms(self, payload: dict[str, Any], rooms: Iterable[str]) -> None:
        """Broadcast payload to specified rooms/channels with <200 ms latency."""
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

    async def broadcast_sos(self, event_data: dict[str, Any]) -> None:
        """Broadcast NEW_INCIDENT / NEW_SOS_ALERT to dashboard & responder channels in <200 ms."""
        payload = {
            "type": "NEW_INCIDENT",
            "event": "new_sos",
            "data": event_data,
        }
        await self.broadcast_to_rooms(payload, ["dashboard", "responders", "incidents"])

    async def broadcast_sensor_alert(self, alert_data: dict[str, Any]) -> None:
        """Broadcast SENSOR_ALERT to dashboard & sensor telemetry channels."""
        payload = {
            "type": "SENSOR_ALERT",
            "event": "sensor_alert",
            "data": alert_data,
        }
        await self.broadcast_to_rooms(payload, ["dashboard", "responders", "sensors"])

    async def broadcast_hazard_update(self, geojson_data: dict[str, Any]) -> None:
        """Broadcast HAZARD_LAYER_UPDATE when flood polygons expand from SAR or ML forecasts."""
        payload = {
            "type": "HAZARD_LAYER_UPDATE",
            "event": "inundation_zones_update",
            "data": geojson_data,
        }
        await self.broadcast_to_rooms(payload, ["dashboard", "responders", "citizens"])

    async def broadcast_many(self, payloads: Iterable[dict[str, Any]], room: str = "global") -> None:
        """Broadcast multiple payloads sequentially."""
        for payload in payloads:
            await self.broadcast(payload, room=room)


manager = ConnectionManager()
