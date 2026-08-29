"use client";

import { useEffect, useRef } from "react";
import maplibregl from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";
import { wsClient } from "../services/ws";

interface MapLibreMapProps {
  center?: [number, number]; // [lng, lat]
  zoom?: number;
  inundationZones?: any;
  sensors?: any;
  sosIncidents?: any[];
  routeGeometry?: [number, number][];
  inundationOpacity?: number;
  onMarkerClick?: (incidentId: string) => void;
  onRequestRoute?: (destLat: number, destLng: number) => void;
}

export default function MapLibreMap({
  center = [77.4446, 28.6321], // Hindon River Basin, Ghaziabad/NCR
  zoom = 12.5,
  inundationZones,
  sensors,
  sosIncidents = [],
  routeGeometry,
  inundationOpacity = 0.5,
  onMarkerClick,
  onRequestRoute,
}: MapLibreMapProps) {
  const mapContainer = useRef<HTMLDivElement>(null);
  const map = useRef<maplibregl.Map | null>(null);
  const markersRef = useRef<maplibregl.Marker[]>([]);

  useEffect(() => {
    if (!mapContainer.current || map.current) return;

    map.current = new maplibregl.Map({
      container: mapContainer.current,
      style: {
        version: 8,
        sources: {
          "carto-dark": {
            type: "raster",
            tiles: [
              "https://a.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}@2x.png",
              "https://b.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}@2x.png",
              "https://c.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}@2x.png",
            ],
            tileSize: 256,
            attribution: "&copy; OpenStreetMap contributors &copy; CARTO",
          },
        },
        layers: [
          {
            id: "carto-dark-layer",
            type: "raster",
            source: "carto-dark",
            minzoom: 0,
            maxzoom: 19,
          },
        ],
      },
      center: center,
      zoom: zoom,
    });

    map.current.addControl(new maplibregl.NavigationControl(), "top-right");

    map.current.on("load", () => {
      if (!map.current) return;

      // 1. Add Inundation Zones GeoJSON Layer
      map.current.addSource("inundation-source", {
        type: "geojson",
        data: inundationZones || { type: "FeatureCollection", features: [] },
      });

      map.current.addLayer({
        id: "inundation-fill",
        type: "fill",
        source: "inundation-source",
        paint: {
          "fill-color": [
            "interpolate",
            ["linear"],
            ["get", "depth_m"],
            0.0,
            "#3B82F6",
            0.5,
            "#F59E0B",
            1.2,
            "#EF4444",
            2.5,
            "#7F1D1D",
          ],
          "fill-opacity": inundationOpacity,
        },
      });

      map.current.addLayer({
        id: "inundation-line",
        type: "line",
        source: "inundation-source",
        paint: {
          "line-color": "#EF4444",
          "line-width": 2,
          "line-dasharray": [2, 2],
        },
      });

      // 2. Add Tactical Green Safe Corridor Route LineString Layer
      map.current.addSource("safe-corridor-source", {
        type: "geojson",
        data: {
          type: "Feature",
          properties: {},
          geometry: {
            type: "LineString",
            coordinates: routeGeometry || [],
          },
        },
      });

      map.current.addLayer({
        id: "safe-corridor-line-glow",
        type: "line",
        source: "safe-corridor-source",
        layout: {
          "line-join": "round",
          "line-cap": "round",
        },
        paint: {
          "line-color": "#059669",
          "line-width": 8,
          "line-opacity": 0.35,
        },
      });

      map.current.addLayer({
        id: "safe-corridor-line",
        type: "line",
        source: "safe-corridor-source",
        layout: {
          "line-join": "round",
          "line-cap": "round",
        },
        paint: {
          "line-color": "#10B981",
          "line-width": 4,
        },
      });
    });

    // Real-Time WebSocket Binding for In-Place GeoJSON Updates (<200ms, 60fps)
    const unsubscribe = wsClient.subscribe((payload) => {
      if (!map.current || !map.current.isStyleLoaded()) return;

      if (payload.type === "HAZARD_LAYER_UPDATE" && payload.data) {
        const source = map.current.getSource("inundation-source") as maplibregl.GeoJSONSource;
        if (source) {
          source.setData(payload.data);
        }
      }
    });

    return () => {
      unsubscribe();
      markersRef.current.forEach((m: maplibregl.Marker) => m.remove());
      markersRef.current = [];
      if (map.current) {
        map.current.remove();
        map.current = null;
      }
    };
  }, []);

  // Update Inundation Zones opacity dynamically
  useEffect(() => {
    if (!map.current || !map.current.isStyleLoaded()) return;
    if (map.current.getLayer("inundation-fill")) {
      map.current.setPaintProperty("inundation-fill", "fill-opacity", inundationOpacity);
    }
  }, [inundationOpacity]);

  // Update Inundation Zones layer data
  useEffect(() => {
    if (!map.current || !map.current.isStyleLoaded()) return;
    const source = map.current.getSource("inundation-source") as maplibregl.GeoJSONSource;
    if (source && inundationZones) {
      source.setData(inundationZones);
    }
  }, [inundationZones]);

  // Update Safe Corridor Route layer
  useEffect(() => {
    if (!map.current || !map.current.isStyleLoaded()) return;
    const source = map.current.getSource("safe-corridor-source") as maplibregl.GeoJSONSource;
    if (source) {
      source.setData({
        type: "Feature",
        properties: {},
        geometry: {
          type: "LineString",
          coordinates: routeGeometry || [],
        },
      });
    }
  }, [routeGeometry]);

  // Render HTML Markers for SOS Incidents and River Sensor Telemetry
  useEffect(() => {
    if (!map.current) return;

    // Clear existing markers
    markersRef.current.forEach((m: maplibregl.Marker) => m.remove());
    markersRef.current = [];

    // 1. Render River Sensor Gauge Markers
    if (sensors && sensors.features) {
      sensors.features.forEach((feature: any) => {
        const coords = feature.geometry?.coordinates;
        if (!coords || coords.length < 2) return;
        const props = feature.properties || {};
        const isAlert = props.is_alert || props.water_level_m >= props.threshold_m;

        const el = document.createElement("div");
        el.className = "group relative flex items-center justify-center cursor-pointer";
        el.innerHTML = `
          <div class="w-6 h-6 rounded-full flex items-center justify-center border-2 border-slate-900 ${
            isAlert ? "bg-red-600 animate-ping" : "bg-cyan-500"
          } shadow-lg shadow-cyan-500/50">
            <span class="w-2.5 h-2.5 bg-white rounded-full"></span>
          </div>
          <div class="absolute bottom-7 hidden group-hover:block z-50 bg-slate-900/95 text-white text-xs p-2.5 rounded-xl border border-slate-700 whitespace-nowrap shadow-xl font-mono">
            <div class="font-bold text-cyan-400">${props.name || props.sensor_id}</div>
            <div>Water Level: <span class="font-bold ${isAlert ? "text-red-400" : "text-emerald-400"}">${props.water_level_m}m</span> / Safe Limit: ${props.threshold_m}m</div>
            <div class="text-[10px] text-slate-400">${props.status || "NORMAL"}</div>
          </div>
        `;

        const marker = new maplibregl.Marker({ element: el })
          .setLngLat([coords[0], coords[1]])
          .addTo(map.current!);
        markersRef.current.push(marker);
      });
    }

    // 2. Render Citizen SOS Distress Markers
    sosIncidents.forEach((sos) => {
      const lat = sos.lat || sos.latitude;
      const lng = sos.lng || sos.longitude;
      if (!lat || !lng) return;

      const category = sos.category || sos.emergency_type || "CRITICAL_TRAPPED";
      const isPending = sos.status === "PENDING";
      const badgeColor =
        category === "CRITICAL_TRAPPED"
          ? "bg-red-600"
          : category === "MEDICAL_EVAC"
          ? "bg-orange-500"
          : "bg-sky-500";

      const el = document.createElement("div");
      el.className = "group relative flex items-center justify-center cursor-pointer";
      el.innerHTML = `
        <div class="relative flex items-center justify-center">
          ${
            isPending
              ? `<span class="animate-ping absolute inline-flex h-8 w-8 rounded-full ${badgeColor} opacity-75"></span>`
              : ""
          }
          <div class="relative inline-flex rounded-full h-8 w-8 ${badgeColor} border-2 border-slate-950 items-center justify-center text-white font-bold text-xs shadow-lg">
            🚨
          </div>
        </div>
      `;

      // Create Interactive MapLibre Popup Modal
      const popupHtml = `
        <div class="p-3 bg-slate-900 text-white rounded-xl border border-slate-700 font-sans text-xs space-y-2 max-w-xs shadow-2xl">
          <div class="font-bold text-sm text-red-400 flex items-center justify-between">
            <span>${category.replace("_", " ")}</span>
            <span class="text-[10px] uppercase font-mono px-2 py-0.5 rounded bg-slate-800 border border-slate-700 text-slate-300">${sos.status}</span>
          </div>
          <div class="text-slate-300 font-mono text-[11px]">
            <div>Phone: <span class="text-white font-bold">${sos.phone_number || sos.phone || "+91-9876543210"}</span></div>
            <div>Coords: ${lat.toFixed(4)}, ${lng.toFixed(4)}</div>
            ${sos.notes ? `<div class="mt-1 text-slate-400 italic">"${sos.notes}"</div>` : ""}
          </div>
          <button id="dispatch-btn-${sos.id || Math.random()}" class="w-full mt-2 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white font-bold rounded-lg text-xs transition">
            🚑 Dispatch Safe Route
          </button>
        </div>
      `;

      const popup = new maplibregl.Popup({ offset: 25, closeButton: false }).setHTML(popupHtml);

      const marker = new maplibregl.Marker({ element: el })
        .setLngLat([lng, lat])
        .setPopup(popup)
        .addTo(map.current!);

      popup.on("open", () => {
        const btnId = `dispatch-btn-${sos.id || Math.random()}`;
        const btn = document.getElementById(btnId);
        if (btn) {
          btn.onclick = () => {
            if (onRequestRoute) onRequestRoute(lat, lng);
            if (onMarkerClick && sos.id) onMarkerClick(sos.id);
          };
        }
      });

      markersRef.current.push(marker);
    });
  }, [sensors, sosIncidents, onMarkerClick, onRequestRoute]);

  return (
    <div className="relative w-full h-full min-h-[480px] rounded-xl overflow-hidden border border-slate-800 shadow-2xl">
      <div ref={mapContainer} className="w-full h-full" />
    </div>
  );
}
