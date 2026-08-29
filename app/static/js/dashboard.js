/**
 * SurakshaGrid EOC Incident Command & Digital Twin Dashboard Controller
 */

import { connectWebSocket, API_BASE } from './api.js';
import { SurakshaMap } from './map.js';
import { showToast, setBadgeStatus } from './ui.js';

document.addEventListener('DOMContentLoaded', () => {
  const mapEngine = new SurakshaMap('map', [28.6350, 77.4350], 13);
  let incidentCount = 0;

  // Toggle SAR Inundation Overlay
  const toggleBtn = document.getElementById('toggle-inundation');
  if (toggleBtn) {
    toggleBtn.addEventListener('click', () => {
      const active = mapEngine.toggleInundationLayer();
      showToast('SAR Processing', active ? 'Flood vector mask enabled' : 'Flood vector mask hidden', active ? 'info' : 'warning');
    });
  }

  // Connect WebSocket Feed
  const streamBadge = document.getElementById('stream-badge');
  const ws = connectWebSocket('/ws/eoc-feed', (data) => {
    if (data.type === 'NEW_INCIDENT') {
      addIncidentToQueue(data);
    }
  }, (isOnline) => {
    setBadgeStatus(streamBadge, isOnline, isOnline ? 'TELEMETRY STREAM ONLINE' : 'DISCONNECTED');
  });

  // Listen for Cross-Tab BroadcastChannel Events
  try {
    const channel = new BroadcastChannel('suraksha_grid_realtime');
    channel.onmessage = (event) => {
      if (event.data && event.data.type === 'NEW_INCIDENT') {
        addIncidentToQueue(event.data.payload || event.data);
      }
    };
  } catch (err) {
    console.warn("BroadcastChannel not supported", err);
  }

  // Storage Fallback
  window.addEventListener('storage', (e) => {
    if (e.key === 'suraksha_last_sos' && e.newValue) {
      try {
        const item = JSON.parse(e.newValue);
        addIncidentToQueue(item.payload || item);
      } catch (err) {}
    }
  });

  function addIncidentToQueue(data) {
    const emptyNotice = document.getElementById('queue-empty');
    if (emptyNotice) emptyNotice.remove();

    incidentCount++;
    const activeCountEl = document.getElementById('active-count');
    if (activeCountEl) activeCountEl.innerText = `${incidentCount} Active Tickets`;

    const queue = document.getElementById('incident-queue');
    if (!queue) return;

    const ticketId = data.ticket_id || `TICK-${Math.floor(1000 + Math.random() * 9000)}`;
    const card = document.createElement('div');
    card.className = "p-2.5 rounded bg-slate-900 border border-red-500/60 font-mono text-[11px] cursor-pointer hover:bg-slate-800 transition-all";
    card.innerHTML = `
      <div class="flex justify-between font-bold text-red-400">
        <span>${ticketId}</span>
        <span class="text-[9px] bg-red-950 px-1 py-0.5 rounded border border-red-700">PRIORITY 1</span>
      </div>
      <div class="text-slate-300 mt-1">${data.notes || data.details || 'Distress signal received'}</div>
      <div class="text-slate-500 text-[10px] mt-1">${data.contact || data.phone || '+91-EMERGENCY'}</div>
    `;
    queue.prepend(card);

    const lat = data.lat || data.latitude || 28.6322;
    const lng = data.lng || data.longitude || 77.4446;

    const popupHtml = `
      <div class="p-1 text-slate-900 font-sans text-xs">
        <b>${ticketId}</b><br/>
        <span>${data.contact || data.phone || ''}</span><br/>
        <button id="dispatch-btn-${incidentCount}" class="mt-2 w-full px-2 py-1 bg-blue-600 hover:bg-blue-700 text-white rounded font-bold">
          Dispatch Unit (Road Track)
        </button>
      </div>
    `;

    mapEngine.addIncidentMarker(ticketId, lat, lng, popupHtml);

    setTimeout(() => {
      const btn = document.getElementById(`dispatch-btn-${incidentCount}`);
      if (btn) {
        btn.addEventListener('click', () => {
          mapEngine.renderSafeCorridor([28.6410, 77.4280], [lat, lng]);
          document.getElementById('unit-eta').innerText = "6 MIN";
          document.getElementById('unit-dist').innerText = "3.4 KM";
          document.getElementById('unit-speed').innerText = "38 KM/H";
          showToast('Unit Dispatch', `NDRF Unit #4 dispatched to ticket ${ticketId}`, 'success');
        });
      }
    }, 400);

    showToast('Emergency SOS', `Distress signal received: ${ticketId}`, 'error');
  }
});
