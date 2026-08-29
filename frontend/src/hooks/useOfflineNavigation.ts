"use client";

import { useEffect, useState } from "react";
import { saveTileToCache, getTileFromCache } from "@/services/tileCache";

export interface RouteManeuver {
  instruction: string;
  distance_m: number;
  duration_sec: number;
  type: string;
}

export interface CachedCorridorRoute {
  id: string;
  distance_km: number;
  estimated_travel_time_mins: number;
  steps: RouteManeuver[];
  geojson: any;
  timestamp: string;
}

export function useOfflineNavigation() {
  const [activeRoute, setActiveRoute] = useState<CachedCorridorRoute | null>(null);
  const [isOffRoute, setIsOffRoute] = useState<boolean>(false);
  const [deviationMeters, setDeviationMeters] = useState<number>(0);

  const cacheRouteLocally = async (route: CachedCorridorRoute) => {
    setActiveRoute(route);
    try {
      const blob = new Blob([JSON.stringify(route)], { type: "application/json" });
      await saveTileToCache(`route-${route.id}`, blob);
    } catch (err) {
      console.warn("IndexedDB route cache fallback:", err);
    }
  };

  const checkGPSDeviation = (currentLat: number, currentLng: number) => {
    if (!activeRoute || !activeRoute.geojson || !activeRoute.geojson.coordinates) return;
    const coords = activeRoute.geojson.coordinates;
    let minDistance = 999999;

    coords.forEach(([lng, lat]: [number, number]) => {
      const dLat = (lat - currentLat) * 111000;
      const dLng = (lng - currentLng) * 111000 * Math.cos((currentLat * Math.PI) / 180);
      const dist = Math.sqrt(dLat * dLat + dLng * dLng);
      if (dist < minDistance) minDistance = dist;
    });

    setDeviationMeters(Math.round(minDistance));
    setIsOffRoute(minDistance > 30.0); // Alert operator if >30 meters off-route
  };

  return {
    activeRoute,
    isOffRoute,
    deviationMeters,
    cacheRouteLocally,
    checkGPSDeviation,
  };
}
