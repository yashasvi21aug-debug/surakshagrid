/**
 * SurakshaGrid NDRF Field Unit Driver Telemetry Broadcaster Controller
 */

import { connectWebSocket } from './api.js';

document.addEventListener('DOMContentLoaded', () => {
  let wsClient = null;
  let watchId = null;
  let packetCount = 0;

  const statusIndicator = document.getElementById('status-indicator');
  const startBtn = document.getElementById('start-btn');
  const latVal = document.getElementById('lat-val');
  const lngVal = document.getElementById('lng-val');
  const speedVal = document.getElementById('speed-val');
  const packetVal = document.getElementById('packet-val');

  wsClient = connectWebSocket('/ws/vehicle-telemetry', null, (isOnline) => {
    if (statusIndicator) {
      statusIndicator.className = isOnline
        ? 'w-3 h-3 rounded-full bg-emerald-500 animate-pulse'
        : 'w-3 h-3 rounded-full bg-red-500';
    }
  });

  function startGPSTracking() {
    if (!("geolocation" in navigator)) {
      alert("Geolocation hardware not supported on this device.");
      return;
    }

    if (startBtn) {
      startBtn.className = "broadcast-btn active";
      startBtn.innerHTML = `<i class="fa-solid fa-tower-broadcast animate-pulse"></i> BROADCASTING HARDWARE GPS LIVE`;
    }

    watchId = navigator.geolocation.watchPosition(
      (position) => {
        const lat = position.coords.latitude;
        const lng = position.coords.longitude;
        const speed = (position.coords.speed || 0) * 3.6;
        const heading = position.coords.heading || 0;

        if (latVal) latVal.innerText = lat.toFixed(5);
        if (lngVal) lngVal.innerText = lng.toFixed(5);
        if (speedVal) speedVal.innerText = `${Math.round(speed)} km/h`;

        const payload = {
          type: "DRIVER_LOCATION_UPDATE",
          unit_id: "NDRF-RESCUE-UNIT-4",
          latitude: lat,
          longitude: lng,
          speed_kmh: speed,
          heading: heading,
          timestamp: Date.now()
        };

        if (wsClient) {
          wsClient.send(payload);
          packetCount++;
          if (packetVal) packetVal.innerText = packetCount;
        }
      },
      (error) => {
        console.error("GPS Hardware Error:", error);
      },
      {
        enableHighAccuracy: true,
        maximumAge: 1000,
        timeout: 5000
      }
    );
  }

  if (startBtn) {
    startBtn.addEventListener('click', startGPSTracking);
  }
});
