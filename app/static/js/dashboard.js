/**
 * SurakshaGrid EOC Incident Command Console Controller
 */

import { connectWebSocket, API_BASE } from './api.js';
import { SurakshaMap } from './map.js';
import { showToast, setBadgeStatus } from './ui.js';

document.addEventListener('DOMContentLoaded', () => {
  const mapEngine = new SurakshaMap('map', [28.6350, 77.4350], 13);
  let incidentCount = 0;

  // Live UTC & IST Clock Ticker
  const updateClocks = () => {
    const now = new Date();
    const utcS = now.toISOString().substring(11, 19) + ' UTC';
    const istS = now.toLocaleTimeString('en-IN', { timeZone: 'Asia/Kolkata', hour12: false }) + ' IST';
    const utcEl = document.getElementById('utc-clock');
    const istEl = document.getElementById('ist-clock');
    if (utcEl) utcEl.innerText = utcS;
    if (istEl) istEl.innerText = istS;
  };
  setInterval(updateClocks, 1000);
  updateClocks();

  // Invalidate map size on window resize
  window.addEventListener('resize', () => {
    if (mapEngine && mapEngine.map) {
      mapEngine.map.invalidateSize();
    }
  });

  // Toggle SAR Inundation Vector Overlay
  const toggleBtn = document.getElementById('toggle-inundation');
  if (toggleBtn) {
    toggleBtn.addEventListener('click', () => {
      const active = mapEngine.toggleInundationLayer();
      showToast('SAR Vector', active ? 'SAR Inundation vector layer enabled' : 'SAR Inundation vector layer hidden', active ? 'info' : 'warning');
    });
  }

  // Connect WebSocket Feed
  const streamBadge = document.getElementById('stream-badge');
  const ws = connectWebSocket('/ws/eoc-feed', (data) => {
    if (data.type === 'NEW_INCIDENT') {
      addIncidentToQueue(data);
    }
  }, (isOnline) => {
    if (streamBadge) {
      const textEl = document.getElementById('stream-status-text');
      if (textEl) textEl.innerText = isOnline ? 'LIVE STREAM' : 'OFFLINE';
    }
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
    const timeStr = new Date().toLocaleTimeString('en-IN', { hour12: false });
    const priority = data.emergency_type || data.emergencyType || 'CRITICAL_TRAPPED';

    const card = document.createElement('div');
    card.className = "incident-card-tactical";
    card.innerHTML = `
      <div class="incident-card-header">
        <span class="incident-ticket">${ticketId}</span>
        <span class="incident-badge-priority">${priority}</span>
      </div>
      <div class="incident-notes">${data.notes || data.details || 'Distress signal received'}</div>
      <div class="incident-meta">
        <span><i class="fa-solid fa-phone text-[9px] mr-1"></i>${data.contact || data.phone || '+91-EMERGENCY'}</span>
        <span><i class="fa-clock text-[9px] mr-1"></i>${timeStr}</span>
      </div>
    `;
    queue.prepend(card);

    const lat = data.lat || data.latitude || 28.6322;
    const lng = data.lng || data.longitude || 77.4446;

    const popupHtml = `
      <div style="padding: 2px;">
        <b style="color: #f85149;">${ticketId}</b> (${priority})<br/>
        <span style="color: #8b949e; font-size: 11px;">Contact: ${data.contact || data.phone || 'N/A'}</span><br/>
        <button id="dispatch-btn-${incidentCount}" class="tactical-btn tactical-btn-primary" style="margin-top: 6px; width: 100%;">
          <i class="fa-solid fa-truck-medical text-[10px]"></i> Dispatch NDRF Unit #4
        </button>
      </div>
    `;

    mapEngine.addIncidentMarker(ticketId, lat, lng, popupHtml);

    setTimeout(() => {
      const btn = document.getElementById(`dispatch-btn-${incidentCount}`);
      if (btn) {
        btn.addEventListener('click', () => {
          mapEngine.renderSafeCorridor([28.6410, 77.4280], [lat, lng]);
          showToast('Unit Dispatch', `NDRF Unit #4 dispatched to ticket ${ticketId}`, 'success');
        });
      }
    }, 400);

    showToast('Emergency SOS', `Distress signal received: ${ticketId}`, 'error');
  }
});
