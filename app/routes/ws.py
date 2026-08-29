from __future__ import annotations

import json
import time
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.websocket_manager import manager

router = APIRouter(tags=["ws"])


async def _handle_room_websocket(websocket: WebSocket, room_name: str) -> None:
    """Helper to handle connection, ping-pong heartbeat, and disconnects for room websockets."""
    await manager.connect(websocket, room=room_name)
    try:
        await websocket.send_json(
            {
                "type": "HANDSHAKE_ACK",
                "room": room_name,
                "status": "CONNECTED",
                "timestamp": time.time(),
            }
        )
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
                continue
            try:
                payload = json.loads(data)
                await manager.broadcast_to_rooms(payload, [room_name])
            except Exception:
                pass
    except WebSocketDisconnect:
        manager.disconnect(websocket, room=room_name)
    except Exception:
        manager.disconnect(websocket, room=room_name)


@router.websocket("/ws/dashboard")
async def dashboard_websocket_endpoint(websocket: WebSocket) -> None:
    """Command center dashboard WebSocket room."""
    await _handle_room_websocket(websocket, "dashboard")


@router.websocket("/ws/responders")
async def responders_websocket_endpoint(websocket: WebSocket) -> None:
    """Rescue field teams & driver responders WebSocket room."""
    await _handle_room_websocket(websocket, "responders")


@router.websocket("/ws/citizens")
async def citizens_websocket_endpoint(websocket: WebSocket) -> None:
    """Public citizen portal WebSocket room."""
    await _handle_room_websocket(websocket, "citizens")


@router.websocket("/ws/vehicle-telemetry")
async def vehicle_telemetry_stream(websocket: WebSocket) -> None:
    """Ingests live driver telemetry and broadcasts to dashboard & responder rooms."""
    await manager.connect(websocket, room="responders")
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
                continue
            payload = json.loads(data)
            await manager.broadcast_to_rooms(payload, ["dashboard", "responders"])
    except (WebSocketDisconnect, Exception):
        manager.disconnect(websocket, room="responders")


@router.websocket("/ws/eoc-feed")
async def eoc_websocket_endpoint(websocket: WebSocket) -> None:
    """Persistent EOC command center feed."""
    await _handle_room_websocket(websocket, "dashboard")