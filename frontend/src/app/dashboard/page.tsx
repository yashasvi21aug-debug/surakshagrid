"use client";

import { useEffect, useState } from "react";
import {
  AlertTriangle,
  Activity,
  Compass,
  Layers,
  LifeBuoy,
  MapPin,
  Navigation,
  Radio,
  RefreshCw,
  ShieldCheck,
  Zap,
} from "lucide-react";
import MapLibreMap from "../../components/MapLibreMap";
import {
  fetchInundationZones,
  fetchRiverSensors,
  requestSafeCorridor,
  SafeCorridorResponse,
} from "../../services/api";
import { SurakshaWebSocketClient } from "../../services/ws";

interface SOSIncident {
  id: string;
  category: string;
  emergency_type?: string;
  phone_number?: string;
  phone?: string;
  status: string;
  lat: number;
  lng: number;
  latitude?: number;
  longitude?: number;
  timestamp: string;
  notes?: string;
}

export default function OfficerDashboard() {
  const [incidents, setIncidents] = useState<SOSIncident[]>([
    {
      id: "SOS-2026-8801",
      category: "CRITICAL_TRAPPED",
      phone_number: "+91-9811223344",
      status: "PENDING",
      lat: 28.6350,
      lng: 77.4480,
      timestamp: "Just now",
      notes: "Family of 4 on roof near Hindon Bridge",
    },
    {
      id: "SOS-2026-8802",
      category: "MEDICAL_EVAC",
      phone_number: "+91-9877665544",
      status: "DISPATCHED",
      lat: 28.6290,
      lng: 77.4390,
      timestamp: "5 mins ago",
      notes: "Elderly patient needing oxygen cylinder",
    },
  ]);

  const [inundationZones, setInundationZones] = useState<any>(null);
  const [sensors, setSensors] = useState<any>(null);
  const [routeGeometry, setRouteGeometry] = useState<[number, number][] | undefined>(undefined);
  const [routeInfo, setRouteInfo] = useState<SafeCorridorResponse | null>(null);
  const [selectedIncident, setSelectedIncident] = useState<SOSIncident | null>(null);
  const [calculatingRoute, setCalculatingRoute] = useState<boolean>(false);
  const [connectionStatus, setConnectionStatus] = useState<"CONNECTED" | "CONNECTING" | "OFFLINE">("CONNECTING");

  // Fetch GIS layers on mount & set up WebSocket listener
  useEffect(() => {
    async function loadGISData() {
      try {
        const [inundationData, sensorData] = await Promise.all([
          fetchInundationZones().catch(() => null),
          fetchRiverSensors().catch(() => null),
        ]);
        if (inundationData) setInundationZones(inundationData);
        if (sensorData) setSensors(sensorData);
      } catch (err) {
        console.warn("Error fetching initial GIS data:", err);
      }
    }

    loadGISData();

    // Connect WebSocket
    const ws = new SurakshaWebSocketClient("/ws/dashboard");
    const unsubscribe = ws.subscribe((event) => {
      setConnectionStatus("CONNECTED");
      if (event.type === "new_sos" || event.event === "new_sos") {
        const data = event.data || event;
        setIncidents((prev) => [
          {
            id: data.id || `SOS-${Date.now().toString().slice(-4)}`,
            category: data.category || data.emergency_type || "CRITICAL_TRAPPED",
            phone_number: data.phone_number || data.phone || "N/A",
            status: data.status || "PENDING",
            lat: data.lat || data.latitude || 28.6321,
            lng: data.lng || data.longitude || 77.4446,
            timestamp: new Date().toLocaleTimeString(),
            notes: data.notes || "Live distress broadcast",
          },
          ...prev,
        ]);
      }
    });

    return () => {
      unsubscribe();
      ws.disconnect();
    };
  }, []);

  // Compute Tactical Safe Corridor
  const handleCalculateCorridor = async (incident: SOSIncident) => {
    setSelectedIncident(incident);
    setCalculatingRoute(true);

    const originBase: [number, number] = [77.4300, 28.6200]; // NDRF Base Depot
    const destTarget: [number, number] = [incident.lng, incident.lat];

    try {
      const result = await requestSafeCorridor({
        start_lat: originBase[1],
        start_lng: originBase[0],
        end_lat: destTarget[1],
        end_lng: destTarget[0],
        vehicle_type: "driving",
      });

      setRouteInfo(result);
      if (result.safe_bypass_geojson && result.safe_bypass_geojson.coordinates) {
        setRouteGeometry(result.safe_bypass_geojson.coordinates);
      }
    } catch (err) {
      console.error("Failed to compute safe corridor:", err);
      // Fallback synthetic green corridor geometry for presentation
      setRouteGeometry([
        originBase,
        [77.4350, 28.6250],
        [77.4410, 28.6310],
        destTarget,
      ]);
    }
    setCalculatingRoute(false);
  };

  const criticalCount = incidents.filter((i) => i.category === "CRITICAL_TRAPPED").length;
  const pendingCount = incidents.filter((i) => i.status === "PENDING").length;

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col font-sans selection:bg-cyan-500 selection:text-black">
      {/* Top Navbar */}
      <header className="h-16 border-b border-slate-800 bg-slate-900/90 backdrop-blur px-6 flex items-center justify-between sticky top-0 z-50">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-cyan-500/20 border border-cyan-500/40 rounded-xl flex items-center justify-center text-cyan-400 font-bold shadow-lg shadow-cyan-500/10">
            <Zap className="w-5 h-5" />
          </div>
          <div>
            <h1 className="text-lg font-extrabold tracking-tight text-white flex items-center gap-2">
              SURAKSHA<span className="text-cyan-400 font-mono">GRID</span>
              <span className="text-[10px] bg-cyan-950 text-cyan-400 border border-cyan-800/80 px-2 py-0.5 rounded font-mono uppercase">
                EOC Command Suite v1.0
              </span>
            </h1>
            <p className="text-xs text-slate-400">National Disaster Response Force (NDRF) Tactical Portal</p>
          </div>
        </div>

        <div className="flex items-center gap-4 text-xs font-mono">
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg border border-slate-800 bg-slate-950">
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
            <span className="text-slate-300">WEBSOCKET:</span>
            <span className="text-emerald-400 font-bold">{connectionStatus}</span>
          </div>

          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg border border-slate-800 bg-slate-950">
            <Activity className="w-3.5 h-3.5 text-cyan-400" />
            <span className="text-slate-300">ACTIVE SENSORS:</span>
            <span className="text-cyan-400 font-bold">{sensors?.features?.length || 4} GAGES</span>
          </div>
        </div>
      </header>

      {/* Main Grid Workspace */}
      <div className="flex-1 p-6 grid grid-cols-1 lg:grid-cols-4 gap-6 max-w-[1920px] mx-auto w-full">
        {/* Left Sidebar: Live Incident Feed & Triage Queue */}
        <div className="lg:col-span-1 space-y-4 flex flex-col">
          {/* Key Metrics Header Cards */}
          <div className="grid grid-cols-2 gap-3">
            <div className="bg-slate-900 border border-red-900/40 rounded-xl p-3.5">
              <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">CRITICAL TRAPPED</div>
              <div className="text-2xl font-black text-red-500 font-mono mt-1">{criticalCount}</div>
            </div>
            <div className="bg-slate-900 border border-amber-900/40 rounded-xl p-3.5">
              <div className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider">PENDING DISPATCH</div>
              <div className="text-2xl font-black text-amber-500 font-mono mt-1">{pendingCount}</div>
            </div>
          </div>

          {/* Distress Feed List */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 flex-1 flex flex-col min-h-[500px]">
            <div className="flex items-center justify-between pb-3 border-b border-slate-800">
              <h2 className="text-sm font-bold uppercase tracking-wider text-slate-200 flex items-center gap-2">
                <Radio className="w-4 h-4 text-red-400 animate-pulse" /> Live Distress Stream
              </h2>
              <span className="text-xs font-mono text-slate-400">{incidents.length} TOTAL</span>
            </div>

            <div className="space-y-3 mt-3 overflow-y-auto flex-1 pr-1">
              {incidents.map((incident) => {
                const isSelected = selectedIncident?.id === incident.id;
                return (
                  <div
                    key={incident.id}
                    onClick={() => setSelectedIncident(incident)}
                    className={`p-3.5 rounded-xl border transition cursor-pointer ${
                      isSelected
                        ? "bg-slate-800 border-cyan-500 shadow-lg shadow-cyan-500/10"
                        : "bg-slate-950/60 border-slate-800/80 hover:border-slate-700"
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-mono font-bold text-slate-300">{incident.id}</span>
                      <span
                        className={`text-[10px] font-mono font-bold px-2 py-0.5 rounded ${
                          incident.category === "CRITICAL_TRAPPED"
                            ? "bg-red-950 text-red-400 border border-red-800"
                            : "bg-amber-950 text-amber-400 border border-amber-800"
                        }`}
                      >
                        {incident.category}
                      </span>
                    </div>

                    <p className="text-xs text-slate-300 font-medium mt-2 line-clamp-2">{incident.notes}</p>

                    <div className="flex items-center justify-between mt-3 text-[11px] text-slate-400 font-mono">
                      <span>{incident.phone_number || incident.phone || "N/A"}</span>
                      <span>{incident.timestamp}</span>
                    </div>

                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        handleCalculateCorridor(incident);
                      }}
                      className="w-full mt-3 py-2 bg-gradient-to-r from-emerald-600 to-teal-600 hover:from-emerald-500 hover:to-teal-500 text-white rounded-lg font-bold text-xs flex items-center justify-center gap-1.5 transition shadow"
                    >
                      <Navigation className="w-3.5 h-3.5" /> COMPUTE SAFE CORRIDOR
                    </button>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* Center / Right: MapLibre GIS Map & Routing Panel */}
        <div className="lg:col-span-3 space-y-4 flex flex-col">
          {/* Top GIS Map Layer Control Bar */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-3 flex items-center justify-between text-xs font-mono">
            <div className="flex items-center gap-4">
              <span className="flex items-center gap-1.5 text-slate-300 font-bold">
                <Layers className="w-4 h-4 text-cyan-400" /> GIS OVERLAYS:
              </span>
              <span className="flex items-center gap-1.5 text-blue-400">
                <span className="w-2.5 h-2.5 rounded bg-blue-500"></span> Flood Polygons
              </span>
              <span className="flex items-center gap-1.5 text-cyan-400">
                <span className="w-2.5 h-2.5 rounded bg-cyan-400"></span> Sensor Gauges
              </span>
              <span className="flex items-center gap-1.5 text-emerald-400">
                <span className="w-2.5 h-2.5 rounded bg-emerald-500"></span> Green Corridor
              </span>
            </div>
            <div className="text-slate-400">Hindon River Basin • Ghaziabad Sector 4</div>
          </div>

          {/* GIS Vector Map */}
          <div className="flex-1 min-h-[500px] relative">
            <MapLibreMap
              center={[77.4446, 28.6321]}
              zoom={12.5}
              inundationZones={inundationZones}
              sensors={sensors}
              sosIncidents={incidents}
              routeGeometry={routeGeometry}
              onMarkerClick={(id) => {
                const found = incidents.find((i) => i.id === id);
                if (found) setSelectedIncident(found);
              }}
            />
          </div>

          {/* Bottom Tactical Safe Corridor Status Panel */}
          {routeInfo && (
            <div className="bg-slate-900 border border-emerald-800/60 rounded-xl p-4 space-y-3 font-mono">
              <div className="flex items-center justify-between border-b border-slate-800 pb-2">
                <div className="flex items-center gap-2 text-emerald-400 font-bold text-sm">
                  <ShieldCheck className="w-5 h-5" /> TACTICAL FLOOD-EVASIVE CORRIDOR COMPUTED
                </div>
                <span className="text-xs bg-emerald-950 text-emerald-300 border border-emerald-800 px-2.5 py-0.5 rounded uppercase">
                  {routeInfo.passability}
                </span>
              </div>

              <div className="grid grid-cols-4 gap-4 text-xs">
                <div>
                  <span className="text-slate-400">DISTANCE:</span>
                  <div className="text-white font-bold text-sm">{routeInfo.distance_km} km</div>
                </div>
                <div>
                  <span className="text-slate-400">EST. TRAVEL TIME:</span>
                  <div className="text-white font-bold text-sm">{routeInfo.estimated_travel_time_mins} mins</div>
                </div>
                <div>
                  <span className="text-slate-400">HAZARD POLYGONS AVOIDED:</span>
                  <div className="text-emerald-400 font-bold text-sm">{routeInfo.intersections_avoided} Zones</div>
                </div>
                <div>
                  <span className="text-slate-400">SAFETY STATUS:</span>
                  <div className="text-emerald-400 font-bold text-sm">{routeInfo.status.toUpperCase()}</div>
                </div>
              </div>

              {routeInfo.steps && routeInfo.steps.length > 0 && (
                <div className="text-xs text-slate-300 pt-2 border-t border-slate-800">
                  <span className="text-slate-400 font-bold">TURN-BY-TURN NAVIGATION WAYPOINTS:</span>
                  <ul className="list-disc list-inside mt-1 space-y-1 text-[11px] text-slate-300">
                    {routeInfo.steps.slice(0, 3).map((step, idx) => (
                      <li key={idx}>
                        {step.instruction} ({step.distance_m}m, {step.duration_sec}s)
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
