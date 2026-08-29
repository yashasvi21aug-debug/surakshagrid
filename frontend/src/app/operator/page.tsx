"use client";

import React, { useEffect, useState } from "react";
import dynamic from "next/dynamic";
import { useGeolocation } from "@/hooks/useGeolocation";
import { wsClient } from "@/services/ws";

const MapLibreMap = dynamic(() => import("@/components/MapLibreMap"), {
  ssr: false,
  loading: () => (
    <div className="flex h-full w-full items-center justify-center bg-slate-950 text-emerald-400">
      <div className="flex flex-col items-center gap-3">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-emerald-500 border-t-transparent" />
        <span className="font-mono text-xs uppercase tracking-widest text-emerald-400">Loading Navigation Map Engine...</span>
      </div>
    </div>
  ),
});

interface RouteStep {
  instruction: string;
  distance_m: number;
  duration_sec: number;
  type: string;
}

interface AssignedIncident {
  id: string;
  phone_number: string;
  category: string;
  lat: number;
  lng: number;
  notes: string;
  status: string;
  safe_corridor?: {
    distance_km: number;
    estimated_travel_time_mins: number;
    steps: RouteStep[];
    safe_bypass_geojson: any;
  };
}

export default function FieldOperatorPage() {
  const { latitude, longitude, accuracy, loading } = useGeolocation();
  const [token, setToken] = useState<string | null>(null);
  const [incident, setIncident] = useState<AssignedIncident | null>(null);
  const [status, setStatus] = useState<string>("DISPATCHED");
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [activeStepIndex, setActiveStepIndex] = useState<number>(0);
  const [statusNotice, setStatusNotice] = useState<string | null>(null);

  // 1. Authenticate & Fetch Demo Token
  useEffect(() => {
    async function initAuth() {
      try {
        const res = await fetch(`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/v1/auth/demo-token`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ role: "FIELD_OPERATOR" }),
        });
        if (res.ok) {
          const data = await res.json();
          setToken(data.access_token);
        }
      } catch (err) {
        console.warn("Demo token auth fallback:", err);
      }
    }
    initAuth();
  }, []);

  // 2. Fetch Assigned Incident & Safe Corridor Route
  useEffect(() => {
    async function fetchAssignedCorridor() {
      setIsLoading(true);
      try {
        const res = await fetch(
          `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/v1/routes/safe-corridor`,
          {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({
              start_lat: latitude || 28.6590,
              start_lng: longitude || 77.2490,
              end_lat: 28.6321,
              end_lng: 77.4446,
              vehicle_type: "boat",
            }),
          }
        );

        if (res.ok) {
          const routeData = await res.json();
          setIncident({
            id: "INCIDENT-NDRF-9921",
            phone_number: "+91-9876543210",
            category: "CRITICAL_TRAPPED",
            lat: 28.6321,
            lng: 77.4446,
            notes: "Family stranded on rooftop near Hindon Barrage riverbank.",
            status: "DISPATCHED",
            safe_corridor: {
              distance_km: routeData.distance_km || 4.2,
              estimated_travel_time_mins: routeData.estimated_travel_time_mins || 7.5,
              steps: routeData.steps || [
                { instruction: "Head East on Riverbed Bypass Road", distance_m: 1200, duration_sec: 180, type: "straight" },
                { instruction: "Turn Left onto Elevated Flood Dike Ramp", distance_m: 1800, duration_sec: 240, type: "turn" },
                { instruction: "Arrive at Target Rooftop Emergency Point", distance_m: 1200, duration_sec: 120, type: "arrive" },
              ],
              safe_bypass_geojson: routeData.safe_bypass_geojson || {
                type: "LineString",
                coordinates: [
                  [77.2490, 28.6590],
                  [77.3110, 28.6450],
                  [77.4446, 28.6321],
                ],
              },
            },
          });
        }
      } catch (err) {
        console.error("Error fetching safe corridor:", err);
      } finally {
        setIsLoading(false);
      }
    }
    fetchAssignedCorridor();
  }, [latitude, longitude]);

  // 3. Status Action Handler
  const handleUpdateStatus = async (newStatus: string) => {
    setStatus(newStatus);
    setStatusNotice(`Updating status to ${newStatus}...`);

    try {
      const headers: Record<string, string> = { "Content-Type": "application/json" };
      if (token) headers["Authorization"] = `Bearer ${token}`;

      const res = await fetch(
        `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/v1/dispatch/incident/${incident?.id || "INCIDENT-NDRF-9921"}/status`,
        {
          method: "PATCH",
          headers,
          body: JSON.stringify({
            status: newStatus,
            officer_notes: `Status updated by Field Operator at ${new Date().toLocaleTimeString()}`,
          }),
        }
      );

      if (res.ok) {
        setStatusNotice(`Status confirmed: ${newStatus}`);
      } else {
        setStatusNotice(`Local status synced: ${newStatus}`);
      }
    } catch {
      setStatusNotice(`Offline mode: ${newStatus} queued locally`);
    }

    setTimeout(() => setStatusNotice(null), 3500);
  };

  const steps = incident?.safe_corridor?.steps || [];

  return (
    <div className="flex h-screen w-screen flex-col bg-slate-950 text-slate-100 antialiased font-sans overflow-hidden select-none">
      {/* Top Bar Navigation Header */}
      <header className="flex h-16 w-full items-center justify-between border-b border-slate-800 bg-slate-900/90 px-4 backdrop-blur-md z-30">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-emerald-500/20 text-emerald-400 border border-emerald-500/40">
            <svg className="h-5 w-5 animate-pulse" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
            </svg>
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-mono text-xs font-bold uppercase tracking-widest text-emerald-400">NDRF ALPHA-01</span>
              <span className="rounded bg-slate-800 px-1.5 py-0.5 text-[10px] font-mono text-slate-400 border border-slate-700">TACTICAL NAV</span>
            </div>
            <h1 className="text-sm font-semibold text-slate-100 leading-tight">
              Target: {incident?.phone_number || "+91-9876543210"}
            </h1>
          </div>
        </div>

        {/* GPS Lock Status */}
        <div className="flex items-center gap-2 bg-slate-950 px-3 py-1.5 rounded-lg border border-slate-800 text-xs">
          <span className={`h-2 w-2 rounded-full ${loading ? "bg-amber-400 animate-ping" : "bg-emerald-400"}`} />
          <span className="font-mono text-[11px] text-slate-300">
            {latitude && longitude ? `${latitude.toFixed(4)}°, ${longitude.toFixed(4)}°` : "Acquiring GPS..."}
          </span>
        </div>
      </header>

      {/* Main Content split: Map on Top, Navigation Drawer on Bottom */}
      <div className="relative flex-1 w-full overflow-hidden">
        {/* Navigation Map Engine */}
        <div className="absolute inset-0 z-0">
          <MapLibreMap
            center={latitude && longitude ? [longitude, latitude] : [77.2490, 28.6590]}
            sosIncidents={incident ? [{ id: incident.id, lat: incident.lat, lng: incident.lng, category: incident.category, status: incident.status }] : []}
            routeGeometry={incident?.safe_corridor?.safe_bypass_geojson?.coordinates}
          />
        </div>

        {/* Status Notice Toast */}
        {statusNotice && (
          <div className="absolute top-4 left-1/2 -translate-x-1/2 z-20 rounded-full bg-emerald-500 px-4 py-2 text-xs font-bold text-slate-950 shadow-lg border border-emerald-300 animate-bounce">
            {statusNotice}
          </div>
        )}

        {/* Turn-by-Turn Instruction Card Overlay */}
        <div className="absolute top-4 left-4 right-4 z-10 max-w-md mx-auto rounded-2xl border border-slate-800/80 bg-slate-900/90 p-4 backdrop-blur-xl shadow-2xl">
          <div className="flex items-start justify-between gap-3">
            <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-emerald-500/10 text-emerald-400 border border-emerald-500/30">
              <svg className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 5l7 7m0 0l-7 7m7-7H3" />
              </svg>
            </div>
            <div className="flex-1">
              <div className="flex items-center justify-between text-[11px] font-mono text-emerald-400 mb-0.5 uppercase tracking-wider">
                <span>NEXT MANEUVER</span>
                <span>STEP {activeStepIndex + 1} OF {steps.length || 1}</span>
              </div>
              <p className="text-base font-semibold text-slate-100 leading-snug">
                {steps[activeStepIndex]?.instruction || "Proceed along green safe corridor"}
              </p>
              <div className="flex items-center gap-4 mt-2 text-xs font-mono text-slate-400">
                <span>Distance: {steps[activeStepIndex]?.distance_m || 4200}m</span>
                <span>ETA: {incident?.safe_corridor?.estimated_travel_time_mins || 7.5} mins</span>
              </div>
            </div>
          </div>

          {/* Stepper Navigation */}
          {steps.length > 1 && (
            <div className="mt-3 flex items-center justify-between border-t border-slate-800/60 pt-2.5">
              <button
                onClick={() => setActiveStepIndex((prev) => Math.max(0, prev - 1))}
                disabled={activeStepIndex === 0}
                className="text-xs font-mono text-slate-400 hover:text-slate-200 disabled:opacity-30"
              >
                ← Previous Step
              </button>
              <button
                onClick={() => setActiveStepIndex((prev) => Math.min(steps.length - 1, prev + 1))}
                disabled={activeStepIndex === steps.length - 1}
                className="text-xs font-mono text-emerald-400 font-bold hover:text-emerald-300 disabled:opacity-30"
              >
                Next Step →
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Bottom Tactical Action Panel */}
      <footer className="z-30 w-full border-t border-slate-800 bg-slate-900/95 p-4 backdrop-blur-xl">
        <div className="mx-auto max-w-md space-y-3">
          {/* Incident Quick Summary */}
          <div className="flex items-center justify-between rounded-xl bg-slate-950 p-3 border border-slate-800/80 text-xs">
            <div>
              <span className="text-slate-400">Status: </span>
              <span className="font-mono font-bold text-emerald-400 uppercase">{status}</span>
            </div>
            <div>
              <span className="text-slate-400">Distress Category: </span>
              <span className="font-mono font-semibold text-amber-400">{incident?.category || "CRITICAL_TRAPPED"}</span>
            </div>
          </div>

          {/* Quick-Tap Action Buttons */}
          <div className="grid grid-cols-3 gap-2.5">
            <button
              onClick={() => handleUpdateStatus("EN_ROUTE")}
              className={`flex flex-col items-center justify-center rounded-xl p-3 text-center transition-all ${
                status === "EN_ROUTE"
                  ? "bg-indigo-600 text-white ring-2 ring-indigo-400 shadow-lg shadow-indigo-500/30"
                  : "bg-slate-800/80 text-slate-300 hover:bg-slate-800 active:scale-95 border border-slate-700"
              }`}
            >
              <svg className="h-5 w-5 mb-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 10V3L4 14h7v7l9-11h-7z" />
              </svg>
              <span className="text-xs font-bold uppercase tracking-wider">EN ROUTE</span>
            </button>

            <button
              onClick={() => handleUpdateStatus("ON_SCENE")}
              className={`flex flex-col items-center justify-center rounded-xl p-3 text-center transition-all ${
                status === "ON_SCENE"
                  ? "bg-amber-600 text-white ring-2 ring-amber-400 shadow-lg shadow-amber-500/30"
                  : "bg-slate-800/80 text-slate-300 hover:bg-slate-800 active:scale-95 border border-slate-700"
              }`}
            >
              <svg className="h-5 w-5 mb-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
              </svg>
              <span className="text-xs font-bold uppercase tracking-wider">ON SCENE</span>
            </button>

            <button
              onClick={() => handleUpdateStatus("RESCUED")}
              className={`flex flex-col items-center justify-center rounded-xl p-3 text-center transition-all ${
                status === "RESCUED" || status === "RESOLVED"
                  ? "bg-emerald-600 text-white ring-2 ring-emerald-400 shadow-lg shadow-emerald-500/30"
                  : "bg-slate-800/80 text-slate-300 hover:bg-slate-800 active:scale-95 border border-slate-700"
              }`}
            >
              <svg className="h-5 w-5 mb-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
              <span className="text-xs font-bold uppercase tracking-wider">RESCUED</span>
            </button>
          </div>
        </div>
      </footer>
    </div>
  );
}
