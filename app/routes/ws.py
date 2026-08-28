import time
import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.websocket_manager import manager

router = APIRouter()


async def _receive_keepalive(websocket: WebSocket) -> None:
    while True:
        data = await websocket.receive_text()
        if data == "ping":
            await websocket.send_text("pong")

@router.websocket("/ws/vehicle-telemetry")
async def vehicle_telemetry_stream(websocket: WebSocket):
    """
    Real-time bidirectional WebSocket channel.
    Ingests live GPS coordinates from field driver devices
    and broadcasts them to all listening EOC command dashboards.
    """
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
                continue
            payload = json.loads(data)
            # Broadcast the live driver coordinate to all dashboards
            await manager.broadcast(payload)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        manager.disconnect(websocket)


@router.websocket("/ws/eoc-feed")
async def eoc_websocket_endpoint(websocket: WebSocket):
    """Persistent EOC feed for SOS incidents and telemetry broadcasts."""
    await manager.connect(websocket)
    try:
        await websocket.send_json(
            {
                "type": "HANDSHAKE_ACK",
                "status": "CONNECTED",
                "timestamp": time.time(),
            }
        )
        await _receive_keepalive(websocket)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception:
        manager.disconnect(websocket)