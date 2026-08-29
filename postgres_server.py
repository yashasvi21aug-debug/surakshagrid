import asyncio
import json
import os
import asyncpg
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="SurakshaGrid Native PostgreSQL Engine")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DATABASE_URL = "postgresql://postgres:nexyash$21@localhost:5432/postgres"
ws_clients = []
db_pool = None

class SOSRequest(BaseModel):
    ticket_id: str
    contact: str
    triage_type: str
    notes: str = ""
    lat: float
    lng: float

@app.on_event("startup")
async def on_startup():
    global db_pool
    try:
        db_pool = await asyncpg.create_pool(DATABASE_URL)
        asyncio.create_task(listen_pg_notifications())
        print(" Connected to PostgreSQL & PostGIS")
    except Exception as e:
        print("DB Pool Init Error:", e)

async def listen_pg_notifications():
    try:
        conn = await asyncpg.connect(DATABASE_URL)
        await conn.add_listener('eoc_incident_stream', on_notification)
        while True:
            await asyncio.sleep(1)
    except Exception as e:
        print("Notification listener error:", e)

def on_notification(connection, pid, channel, payload):
    data = json.loads(payload)
    for ws in ws_clients:
        asyncio.create_task(ws.send_json(data))

# --- HTML Page Routes ---

@app.get("/")
async def serve_index():
    if os.path.exists("index.html"):
        return FileResponse("index.html")
    return {"status": "SurakshaGrid Backend Running", "docs": "/docs"}

@app.get("/citizen")
async def serve_citizen():
    if os.path.exists("citizen.html"):
        return FileResponse("citizen.html")
    raise HTTPException(status_code=404, detail="citizen.html not found")

@app.get("/driver")
async def serve_driver():
    if os.path.exists("driver.html"):
        return FileResponse("driver.html")
    raise HTTPException(status_code=404, detail="driver.html not found")

@app.get("/dashboard")
async def serve_dashboard():
    if os.path.exists("dashboard.html"):
        return FileResponse("dashboard.html")
    raise HTTPException(status_code=404, detail="dashboard.html not found")

# --- Real-Time WebSocket Endpoint ---

@app.websocket("/ws/eoc-feed")
async def websocket_hub(ws: WebSocket):
    await ws.accept()
    ws_clients.append(ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        ws_clients.remove(ws)

# --- REST Endpoints ---

@app.post("/api/v1/sos/")
async def ingest_sos(sos: SOSRequest):
    try:
        async with db_pool.acquire() as conn:
            query = """
                INSERT INTO incidents (ticket_id, contact, triage_type, notes, lat, lng)
                VALUES ($1, $2, $3, $4, $5, $6)
                ON CONFLICT (ticket_id) DO UPDATE 
                SET contact = EXCLUDED.contact,
                    triage_type = EXCLUDED.triage_type,
                    notes = EXCLUDED.notes,
                    lat = EXCLUDED.lat,
                    lng = EXCLUDED.lng
                RETURNING ticket_id;
            """
            await conn.fetchval(
                query, 
                str(sos.ticket_id), 
                str(sos.contact), 
                str(sos.triage_type), 
                str(sos.notes), 
                float(sos.lat), 
                float(sos.lng)
            )
        return {"status": "dispatched", "ticket_id": sos.ticket_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/incidents/spatial-check/{ticket_id}")
async def check_hazard(ticket_id: str):
    try:
        async with db_pool.acquire() as conn:
            query = """
                SELECT EXISTS (
                    SELECT 1 FROM incidents i, flood_zones f
                    WHERE i.ticket_id = $1 
                      AND i.lat BETWEEN f.min_lat AND f.max_lat
                      AND i.lng BETWEEN f.min_lng AND f.max_lng
                );
            """
            is_trapped = await conn.fetchval(query, ticket_id)
        return {"ticket_id": ticket_id, "inside_flood_zone": bool(is_trapped)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))