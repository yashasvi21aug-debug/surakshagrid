export const API_BASE_URL =
  typeof window !== "undefined"
    ? process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"
    : "http://localhost:8000";

export interface SOSPayload {
  category: "CRITICAL_TRAPPED" | "MEDICAL_EVAC" | "FOOD_WATER" | "INFRASTRUCTURE_DAMAGE";
  latitude: number;
  longitude: number;
  accuracy?: number;
  notes?: string;
  phone?: string;
  emergencyType?: string;
  lat?: number;
  lng?: number;
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

export interface GeoJSONFeatureCollection {
  type: "FeatureCollection";
  features: Array<{
    type: "Feature";
    geometry: {
      type: string;
      coordinates: any;
    };
    properties: Record<string, any>;
  }>;
}

export interface SafeCorridorRequest {
  start_lat: number;
  start_lng: number;
  end_lat: number;
  end_lng: number;
  vehicle_type?: string;
}

export interface SafeCorridorResponse {
  status: string;
  passability: string;
  safety_flags: string[];
  safe_bypass_geojson: {
    type: "LineString";
    coordinates: Array<[number, number]>;
  };
  distance_km: number;
  estimated_travel_time_mins: number;
  flood_zones_considered: number;
  intersections_avoided: number;
  steps: Array<{
    instruction: string;
    distance_m: number;
    duration_sec: number;
    type: string;
  }>;
}

export async function submitSOS(payload: SOSPayload): Promise<SOSResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/sos/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    throw new Error(`SOS ingestion failed: ${response.statusText}`);
  }
  return response.json();
}

export async function fetchInundationZones(): Promise<GeoJSONFeatureCollection> {
  const response = await fetch(`${API_BASE_URL}/api/v1/spatial/inundation`);
  if (!response.ok) {
    throw new Error(`Failed to fetch inundation zones: ${response.statusText}`);
  }
  return response.json();
}

export async function fetchRiverSensors(): Promise<GeoJSONFeatureCollection> {
  const response = await fetch(`${API_BASE_URL}/api/v1/spatial/sensors`);
  if (!response.ok) {
    throw new Error(`Failed to fetch river sensors: ${response.statusText}`);
  }
  return response.json();
}

export async function fetchNearbySOS(lat: number, lng: number, radiusKm: number = 5): Promise<any> {
  const response = await fetch(
    `${API_BASE_URL}/api/v1/spatial/nearby-sos?lat=${lat}&lng=${lng}&radius_km=${radiusKm}`
  );
  if (!response.ok) {
    throw new Error(`Failed to fetch nearby SOS items: ${response.statusText}`);
  }
  return response.json();
}

export async function requestSafeCorridor(req: SafeCorridorRequest): Promise<SafeCorridorResponse> {
  const response = await fetch(`${API_BASE_URL}/api/v1/routes/safe-corridor`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  });
  if (!response.ok) {
    throw new Error(`Failed to calculate safe corridor: ${response.statusText}`);
  }
  return response.json();
}

export async function getDemoToken(): Promise<{ access_token: string; token_type: string; role: string }> {
  const response = await fetch(`${API_BASE_URL}/api/v1/auth/demo-token`, {
    method: "POST",
  });
  if (!response.ok) {
    throw new Error(`Demo authentication failed: ${response.statusText}`);
  }
  return response.json();
}
