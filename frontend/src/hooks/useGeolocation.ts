"use client";

import { useCallback, useEffect, useState } from "react";

export interface GeolocationState {
  latitude: number | null;
  longitude: number | null;
  altitude: number | null;
  accuracy: number | null;
  error: string | null;
  loading: boolean;
  isManualFallback: boolean;
}

export function useGeolocation() {
  const [state, setState] = useState<GeolocationState>({
    latitude: null,
    longitude: null,
    altitude: null,
    accuracy: null,
    error: null,
    loading: true,
    isManualFallback: false,
  });

  const acquireLocation = useCallback(() => {
    setState((prev) => ({ ...prev, loading: true, error: null }));

    if (typeof window === "undefined" || !navigator.geolocation) {
      setState({
        latitude: 28.6321,
        longitude: 77.4446,
        altitude: null,
        accuracy: 25,
        error: "Geolocation unsupported by browser. Using default sector position.",
        loading: false,
        isManualFallback: true,
      });
      return;
    }

    navigator.geolocation.getCurrentPosition(
      (position) => {
        setState({
          latitude: position.coords.latitude,
          longitude: position.coords.longitude,
          altitude: position.coords.altitude,
          accuracy: position.coords.accuracy,
          error: null,
          loading: false,
          isManualFallback: false,
        });
      },
      (err) => {
        console.warn("HTML5 Geolocation acquisition error:", err.message);
        // Fallback default coordinates (Hindon River Basin, Ghaziabad)
        setState({
          latitude: 28.6321,
          longitude: 77.4446,
          altitude: null,
          accuracy: 50,
          error: `GPS Error (${err.message}). Defaulting to Hindon River Basin.`,
          loading: false,
          isManualFallback: true,
        });
      },
      {
        enableHighAccuracy: true,
        timeout: 10000,
        maximumAge: 0,
      }
    );
  }, []);

  const setManualCoords = useCallback((lat: number, lng: number) => {
    setState({
      latitude: lat,
      longitude: lng,
      altitude: null,
      accuracy: 5,
      error: null,
      loading: false,
      isManualFallback: true,
    });
  }, []);

  useEffect(() => {
    acquireLocation();
  }, [acquireLocation]);

  return { ...state, acquireLocation, setManualCoords };
}
