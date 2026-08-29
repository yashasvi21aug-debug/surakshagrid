from __future__ import annotations

import json
import logging
import time
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.websocket_manager import manager

logger = logging.getLogger(__name__)

router = APIRouter(tags=["ws"])


async def _handle_room_websocket(websocket: WebSocket, room_name: str) -> None:
    """Handle connection lifecycle, channels, ping-pong keep-alive, and disconnects for WebSocket clients."""
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
                if payload.get("type") == "ping":
                    await websocket.send_json({"type": "pong", "timestamp": time.time()})
                    continue

                if payload.get("type") == "subscribe":
                    channel = payload.get("channel", room_name)
                    async with manager._lock:
                        if channel not in manager.rooms:
                            manager.rooms[channel] = set()
                        manager.rooms[channel].add(websocket)
                    await websocket.send_json({"type": "SUBSCRIBE_ACK", "channel": channel})
                    continue

                await manager.broadcast_to_rooms(payload, [room_name])
            except Exception:
                pass
    except WebSocketDisconnect:
        manager.disconnect(websocket, room=room_name)
    except Exception as error:
        logger.debug("WebSocket exception in room %s: %s", room_name, error)
        manager.disconnect(websocket, room=room_name)


@router.websocket("/ws")
async def gateway_websocket_endpoint(websocket: WebSocket) -> None:
    """General WebSocket gateway for live incident and river telemetry streams."""
    await _handle_room_websocket(websocket, "dashboard")


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