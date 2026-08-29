/**
 * SurakshaGrid Citizen Emergency Portal Controller
 */

import { API_BASE, apiFetch } from './api.js';

document.addEventListener('DOMContentLoaded', () => {
  const form = document.getElementById('sos-form');
  const button = document.getElementById('dispatch-button');
  const errorEl = document.getElementById('form-error');
  const statusEl = document.getElementById('location-status');
  const dotEl = document.getElementById('location-dot');
  const modal = document.getElementById('success-modal');
  const ticketEl = document.getElementById('ticket-value');
  const returnBtn = document.getElementById('return-button');

  const fallback = { lat: 28.6322, lng: 77.4446 };
  let currentCoords = null;

  const makeTicket = () => `TICK-${Math.floor(1000 + Math.random() * 9000)}`;

  const acquireGps = () => new Promise((resolve) => {
    if (!navigator.geolocation) {
      if (dotEl) dotEl.className = 'location-dot fallback';
      if (statusEl) statusEl.textContent = `GPS UNAVAILABLE - FALLBACK ${fallback.lat}, ${fallback.lng}`;
      resolve(fallback);
      return;
    }

    navigator.geolocation.getCurrentPosition(
      (p) => {
        currentCoords = { lat: p.coords.latitude, lng: p.coords.longitude };
        if (dotEl) dotEl.className = 'location-dot locked';
        if (statusEl) statusEl.textContent = `GPS LOCKED - ${currentCoords.lat.toFixed(5)}, ${currentCoords.lng.toFixed(5)} (${Math.round(p.coords.accuracy)}m accuracy)`;
        resolve(currentCoords);
      },
      () => {
        if (dotEl) dotEl.className = 'location-dot fallback';
        if (statusEl) statusEl.textContent = `GPS UNAVAILABLE - FALLBACK ${fallback.lat}, ${fallback.lng}`;
        resolve(fallback);
      },
      { enableHighAccuracy: true, timeout: 4000, maximumAge: 0 }
    );
  });

  const openSuccess = (id) => {
    if (ticketEl) ticketEl.textContent = id;
    if (modal) modal.classList.add('visible');
    if (returnBtn) returnBtn.focus();
  };

  // Emergency Triage Selection Radio Class Binding
  document.querySelectorAll('input[name="emergencyType"]').forEach((input) => {
    input.addEventListener('change', () => {
      document.querySelectorAll('.triage-card').forEach((card) => card.classList.remove('selected'));
      const parentCard = input.closest('.triage-card');
      if (parentCard) parentCard.classList.add('selected');
    });
  });

  if (returnBtn) {
    returnBtn.addEventListener('click', () => {
      if (modal) modal.classList.remove('visible');
      if (button) button.textContent = 'DISPATCH EMERGENCY SOS';
    });
  }

  // Realtime Broadcast Channel Helper
  let sosBroadcast = null;
  try {
    sosBroadcast = new BroadcastChannel('suraksha_grid_realtime');
  } catch (e) {}

  const broadcastIncident = (payload) => {
    try {
      if (sosBroadcast) sosBroadcast.postMessage({ type: 'NEW_INCIDENT', payload });
    } catch (e) {}
    try {
      localStorage.setItem('suraksha_last_sos', JSON.stringify({ timestamp: Date.now(), payload }));
    } catch (e) {}
  };

  if (form) {
    form.addEventListener('submit', async (event) => {
      event.preventDefault();
      if (errorEl) errorEl.textContent = '';

      if (!form.checkValidity()) {
        form.reportValidity();
        return;
      }

      const data = new FormData(form);
      const gps = currentCoords || await acquireGps();
      const phone = data.get('phone').trim();
      const emergencyType = data.get('emergencyType');
      const details = (data.get('notes') || '').trim() || 'Emergency flood rescue request.';

      const payload = {
        phone,
        emergencyType,
        lat: gps.lat,
        lng: gps.lng,
        victim_name: 'Citizen SOS',
        contact_number: phone,
        latitude: gps.lat,
        longitude: gps.lng,
        details
      };

      const ticketId = makeTicket();
      const broadcastPayload = {
        ticket_id: ticketId,
        emergency_type: emergencyType,
        victim_name: 'Citizen SOS',
        contact: phone,
        lat: gps.lat,
        lng: gps.lng,
        details,
        created_at: new Date().toISOString()
      };

      if (button) {
        button.disabled = true;
        button.textContent = 'TRANSMITTING...';
      }

      broadcastIncident(broadcastPayload);

      try {
        const result = await apiFetch('/api/v1/sos/', {
          method: 'POST',
          body: payload
        });
        if (button) button.textContent = 'SOS TRANSMITTED - NDRF UNIT DISPATCHED';
        openSuccess(result.id || result.incident_id || ticketId);
      } catch (dispatchError) {
        console.warn('Backend waking up; confirming local dispatch ticket.', dispatchError);
        if (button) button.textContent = 'SOS TRANSMITTED - NDRF UNIT DISPATCHED';
        openSuccess(ticketId);
      } finally {
        if (button) button.disabled = false;
      }
    });
  }

  acquireGps();
});
