from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import List
import json

router = APIRouter()

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_text(json.dumps(message))
            except Exception:
                pass

manager = ConnectionManager()

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
            payload = json.loads(data)
            # Broadcast the live driver coordinate to all dashboards
            await manager.broadcast(payload)
    except WebSocketDisconnect:
        manager.disconnect(websocket)