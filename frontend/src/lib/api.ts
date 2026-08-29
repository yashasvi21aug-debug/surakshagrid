export interface SOSPayload {
  phone: string;
  emergencyType: "CRITICAL_TRAPPED" | "MEDICAL_EVAC" | "FOOD_WATER" | "INFRASTRUCTURE_DAMAGE";
  lat: number;
  lng: number;
  rainRate?: number;
}

export interface SOSResponse {
  id: string;
  phone_number: string;
  emergency_type: string;
  lat: number;
  lng: number;
  rain_rate?: number;
  risk_status?: string;
  status: string;
  timestamp: string;
}

export interface EvasiveRouteRequest {
  origin: [number, number];
  destination: [number, number];
  active_flood_zones?: any[];
}

export interface EvasiveRouteResponse {
  status: string;
  passability?: string;
  safety_flags?: string[];
  safe_bypass_geojson: {
    type: "LineString";
    coordinates: [number, number][];
  };
  distance_km: number;
  estimated_travel_time_mins: number;
  flood_zones_considered?: number;
  intersections_avoided?: number;
  steps?: {
    instruction: string;
    distance_m: number;
    duration_sec: number;
    type: string;
  }[];
}

const API_BASE = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:8000/api/v1';

export async function submitSOS(payload: SOSPayload): Promise<SOSResponse> {
  const res = await fetch(`${API_BASE}/sos/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    throw new Error(`SOS submission failed: ${res.statusText}`);
  }
  return res.json();
}

export async function fetchInundationPolygons() {
  const res = await fetch(`${API_BASE}/spatial/inundation`);
  if (!res.ok) return { type: 'FeatureCollection', features: [] };
  return res.json();
}

export async function fetchSensors() {
  const res = await fetch(`${API_BASE}/spatial/sensors`);
  if (!res.ok) return { items: [] };
  return res.json();
}

export async function fetchActiveSOSFeed(): Promise<SOSResponse[]> {
  const res = await fetch(`${API_BASE}/sos/`);
  if (!res.ok) return [];
  const data = await res.json();
  return data.items || [];
}

export async function requestSafeCorridor(req: EvasiveRouteRequest): Promise<EvasiveRouteResponse> {
  const res = await fetch(`${API_BASE}/routes/safe-corridor`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(req),
  });
  if (!res.ok) {
    throw new Error(`Route calculation failed: ${res.statusText}`);
  }
  return res.json();
}

export function createWebSocket(room: string = 'dashboard'): WebSocket {
  const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const host = process.env.NEXT_PUBLIC_WS_HOST || 'localhost:8000';
  return new WebSocket(`${wsProtocol}//${host}/ws/${room}`);
}
