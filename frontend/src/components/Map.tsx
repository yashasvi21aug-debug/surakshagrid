'use client';

import React, { useEffect, useRef } from 'react';
import maplibregl from 'maplibre-gl';
import { SOSResponse } from '@/lib/api';

interface MapProps {
  inundationData?: any;
  sensors?: any[];
  sosRecords?: SOSResponse[];
  corridorGeoJSON?: any;
  onSelectSOS?: (sos: SOSResponse) => void;
}

export default function MapComponent({
  inundationData,
  sensors = [],
  sosRecords = [],
  corridorGeoJSON,
  onSelectSOS,
}: MapProps) {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<maplibregl.Map | null>(null);
  const markersRef = useRef<maplibregl.Marker[]>([]);

  useEffect(() => {
    if (!mapContainerRef.current) return;

    // Initialize MapLibre GL map centered over Hindon Basin / NCR region
    const map = new maplibregl.Map({
      container: mapContainerRef.current,
      style: {
        version: 8,
        sources: {
          'osm-tiles': {
            type: 'raster',
            tiles: ['https://tile.openstreetmap.org/{z}/{x}/{y}.png'],
            tileSize: 256,
            attribution: '&copy; OpenStreetMap contributors',
          },
        },
        layers: [
          {
            id: 'osm-tiles-layer',
            type: 'raster',
            source: 'osm-tiles',
            minzoom: 0,
            maxzoom: 19,
          },
        ],
      },
      center: [77.37, 28.65],
      zoom: 11,
    });

    map.addControl(new maplibregl.NavigationControl(), 'top-right');
    mapRef.current = map;

    map.on('load', () => {
      // Add source & layers for Flood Inundation Polygons
      map.addSource('flood-polygons-source', {
        type: 'geojson',
        data: inundationData || { type: 'FeatureCollection', features: [] },
      });

      map.addLayer({
        id: 'flood-polygons-fill',
        type: 'fill',
        source: 'flood-polygons-source',
        paint: {
          'fill-color': '#EF4444',
          'fill-opacity': 0.35,
        },
      });

      map.addLayer({
        id: 'flood-polygons-outline',
        type: 'line',
        source: 'flood-polygons-source',
        paint: {
          'line-color': '#DC2626',
          'line-width': 2,
        },
      });

      // Add source & layer for Safe Evasive Route Line
      map.addSource('route-source', {
        type: 'geojson',
        data: corridorGeoJSON || { type: 'FeatureCollection', features: [] },
      });

      map.addLayer({
        id: 'route-layer',
        type: 'line',
        source: 'route-source',
        paint: {
          'line-color': '#10B981',
          'line-width': 5,
        },
      });
    });

    return () => {
      map.remove();
    };
  }, []);

  // Update Inundation Polygons
  useEffect(() => {
    if (!mapRef.current) return;
    const source = mapRef.current.getSource('flood-polygons-source') as maplibregl.GeoJSONSource;
    if (source && inundationData) {
      source.setData(inundationData);
    }
  }, [inundationData]);

  // Update Evasive Route Line
  useEffect(() => {
    if (!mapRef.current) return;
    const source = mapRef.current.getSource('route-source') as maplibregl.GeoJSONSource;
    if (source) {
      source.setData(
        corridorGeoJSON
          ? {
              type: 'FeatureCollection',
              features: [
                {
                  type: 'Feature',
                  geometry: corridorGeoJSON,
                  properties: {},
                },
              ],
            }
          : { type: 'FeatureCollection', features: [] }
      );
    }
  }, [corridorGeoJSON]);

  // Render Markers for SOS Incidents and River Sensors
  useEffect(() => {
    if (!mapRef.current) return;

    // Clear old markers
    markersRef.current.forEach((m: maplibregl.Marker) => m.remove());
    markersRef.current = [];

    // Render SOS Markers
    sosRecords.forEach((sos) => {
      if (!sos.lat || !sos.lng) return;

      const el = document.createElement('div');
      el.className = 'w-6 h-6 rounded-full bg-red-600 border-2 border-white flex items-center justify-center cursor-pointer shadow-lg pulse-red';
      el.title = `${sos.emergency_type} - ${sos.phone_number}`;

      el.addEventListener('click', () => {
        if (onSelectSOS) onSelectSOS(sos);
      });

      const popup = new maplibregl.Popup({ offset: 25 }).setHTML(`
        <div class="p-2 text-slate-900 text-xs font-sans">
          <strong class="text-red-600 block text-sm font-bold">${sos.emergency_type}</strong>
          <div>Phone: ${sos.phone_number}</div>
          <div>Status: <span class="font-bold">${sos.status}</span></div>
          <div>Risk: ${sos.risk_status || 'MEDIUM'}</div>
        </div>
      `);

      const marker = new maplibregl.Marker({ element: el })
        .setLngLat([sos.lng, sos.lat])
        .setPopup(popup)
        .addTo(mapRef.current!);

      markersRef.current.push(marker);
    });

    // Render River Telemetry Sensors Markers
    sensors.forEach((sensor) => {
      if (!sensor.lat || !sensor.lng) return;

      const el = document.createElement('div');
      const isCritical = sensor.status === 'CRITICAL' || sensor.status === 'WARNING';
      el.className = `w-5 h-5 rounded-full ${isCritical ? 'bg-amber-500' : 'bg-cyan-500'} border-2 border-white flex items-center justify-center cursor-pointer shadow-md`;
      el.title = `Sensor: ${sensor.sensor_name}`;

      const popup = new maplibregl.Popup({ offset: 25 }).setHTML(`
        <div class="p-2 text-slate-900 text-xs font-sans">
          <strong class="text-cyan-700 block text-sm font-bold">${sensor.sensor_name}</strong>
          <div>Water Level: <span class="font-bold">${sensor.current_water_level_m}m</span></div>
          <div>Warning Threshold: ${sensor.warning_threshold_m}m</div>
          <div>Status: <span class="font-bold ${isCritical ? 'text-amber-600' : 'text-emerald-600'}">${sensor.status}</span></div>
        </div>
      `);

      const marker = new maplibregl.Marker({ element: el })
        .setLngLat([sensor.lng, sensor.lat])
        .setPopup(popup)
        .addTo(mapRef.current!);

      markersRef.current.push(marker);
    });
  }, [sosRecords, sensors]);

  return (
    <div className="w-full h-full relative">
      <div ref={mapContainerRef} className="w-full h-full rounded-2xl overflow-hidden shadow-2xl border border-slate-800" />
    </div>
  );
}
