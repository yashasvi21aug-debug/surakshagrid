"use client";

import React, { useEffect, useState } from "react";
import dynamic from "next/dynamic";
import { useGeolocation } from "@/hooks/useGeolocation";
import { useOfflineNavigation } from "@/hooks/useOfflineNavigation";

const MapLibreMap = dynamic(() => import("@/components/MapLibreMap"), {
  ssr: false,
  loading: () => (
    <div className="flex h-full w-full items-center justify-center bg-slate-950 text-emerald-400">
      <span className="font-mono text-xs uppercase tracking-widest">Loading Tactical Navigation Engine...</span>
    </div>
  ),
});

export default function OperatorNavigationPage() {
  const { latitude, longitude } = useGeolocation();
  const { activeRoute, isOffRoute, deviationMeters, cacheRouteLocally, checkGPSDeviation } = useOfflineNavigation();
  const [activeStepIndex, setActiveStepIndex] = useState<number>(0);

  useEffect(() => {
    // Demo initial route caching
    const demoRoute = {
      id: "CORRIDOR-NDRF-01",
      distance_km: 4.2,
      estimated_travel_time_mins: 7.5,
      steps: [
        { instruction: "Head East on Riverbed Bypass Road", distance_m: 1200, duration_sec: 180, type: "straight" },
        { instruction: "Turn Left onto Elevated Flood Dike Ramp", distance_m: 1800, duration_sec: 240, type: "turn" },
        { instruction: "Arrive at Target Rooftop Emergency Point", distance_m: 1200, duration_sec: 120, type: "arrive" },
      ],
      geojson: {
        type: "LineString",
        coordinates: [
          [77.2490, 28.6590],
          [77.3110, 28.6450],
          [77.4446, 28.6321],
        ],
      },
      timestamp: new Date().toISOString(),
    };
    cacheRouteLocally(demoRoute);
  }, []);

  useEffect(() => {
    if (latitude && longitude) {
      checkGPSDeviation(latitude, longitude);
    }
  }, [latitude, longitude]);

  const steps = activeRoute?.steps || [];

  return (
    <div className="flex h-screen w-screen flex-col bg-slate-950 text-slate-100 font-sans select-none overflow-hidden">
      {/* Header Bar */}
      <header className="flex h-14 w-full items-center justify-between border-b border-slate-800 bg-slate-900 px-4 backdrop-blur-md z-30">
        <div className="flex items-center gap-2">
          <span className="font-mono text-xs font-bold text-emerald-400">NDRF TACTICAL NAV</span>
          {isOffRoute && (
            <span className="rounded bg-red-600 px-2 py-0.5 text-[10px] font-bold text-white animate-pulse">
              OFF ROUTE ({deviationMeters}m)
            </span>
          )}
        </div>
        <div className="font-mono text-xs text-slate-400">
          {latitude && longitude ? `${latitude.toFixed(4)}°, ${longitude.toFixed(4)}°` : "Acquiring GPS..."}
        </div>
      </header>

      {/* Map View & Turn Overlay */}
      <div className="relative flex-1 w-full overflow-hidden">
        <div className="absolute inset-0 z-0">
          <MapLibreMap
            center={latitude && longitude ? [longitude, latitude] : [77.2490, 28.6590]}
            routeGeometry={activeRoute?.geojson?.coordinates}
          />
        </div>

        {/* Turn-by-Turn Maneuver Overlay */}
        <div className="absolute top-4 left-4 right-4 z-10 max-w-md mx-auto rounded-2xl border border-slate-800/80 bg-slate-900/90 p-4 backdrop-blur-xl shadow-2xl">
          <div className="flex items-center justify-between text-xs font-mono text-emerald-400 mb-1">
            <span>STEP {activeStepIndex + 1} OF {steps.length || 1}</span>
            <span>{steps[activeStepIndex]?.distance_m || 1200}m</span>
          </div>
          <h2 className="text-base font-semibold text-slate-100">
            {steps[activeStepIndex]?.instruction || "Proceed along green safe corridor"}
          </h2>
        </div>
      </div>
    </div>
  );
}
