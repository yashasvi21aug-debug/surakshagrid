"use client";

import React, { useState } from "react";

interface DroneTelemetry {
  drone_id: string;
  callsign: string;
  lat: number;
  lng: number;
  altitude_m: number;
  heading_deg: number;
  stream_url: string;
  status: string;
}

interface DroneOverlayProps {
  drones?: DroneTelemetry[];
}

export default function DroneOverlay({ drones = [] }: DroneOverlayProps) {
  const [selectedDrone, setSelectedDrone] = useState<DroneTelemetry | null>(null);

  const demoDrones: DroneTelemetry[] = drones.length > 0 ? drones : [
    {
      drone_id: "UAV-NDRF-01",
      callsign: "SkySentinel Alpha",
      lat: 28.6380,
      lng: 77.4420,
      altitude_m: 120.0,
      heading_deg: 145,
      stream_url: "https://surakshagrid-demo-stream.local/hls/uav-01.m3u8",
      status: "LIVE_PATROL",
    },
  ];

  return (
    <div className="relative">
      {/* Clickable Drone List / Controls */}
      <div className="flex gap-2">
        {demoDrones.map((drone) => (
          <button
            key={drone.drone_id}
            onClick={() => setSelectedDrone(drone)}
            className="flex items-center gap-2 rounded-xl bg-slate-900/90 border border-slate-800 px-3 py-1.5 text-xs text-cyan-400 backdrop-blur-md hover:bg-slate-800"
          >
            <span className="h-2 w-2 rounded-full bg-cyan-400 animate-ping" />
            <span className="font-mono font-bold">{drone.callsign}</span>
          </button>
        ))}
      </div>

      {/* Picture-in-Picture Drone Video Feed Modal */}
      {selectedDrone && (
        <div className="fixed bottom-6 right-6 z-50 w-80 rounded-2xl border border-slate-700 bg-slate-950/95 p-3 text-slate-100 shadow-2xl backdrop-blur-xl">
          <div className="flex items-center justify-between border-b border-slate-800 pb-2 mb-2">
            <div className="flex items-center gap-2">
              <span className="h-2 w-2 rounded-full bg-red-500 animate-pulse" />
              <span className="font-mono text-xs font-bold text-slate-100">{selectedDrone.callsign} (LIVE)</span>
            </div>
            <button
              onClick={() => setSelectedDrone(null)}
              className="text-slate-400 hover:text-slate-200 text-sm"
            >
              ✕
            </button>
          </div>

          <div className="relative h-44 w-full rounded-xl bg-slate-900 overflow-hidden flex items-center justify-center border border-slate-800">
            <div className="text-center font-mono text-xs text-cyan-400 animate-pulse">
              🎥 [LIVE HLS STREAM]
              <br />
              <span className="text-[10px] text-slate-400">Heading: {selectedDrone.heading_deg}° | Alt: {selectedDrone.altitude_m}m</span>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
