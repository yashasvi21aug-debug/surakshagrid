/**
 * SurakshaGrid API & WebSocket Communications Core Module
 */

const getBackendDomain = () => {
  const host = window.location.hostname;
  return (host === 'localhost' || host === '127.0.0.1')
    ? window.location.host
    : 'surakshagrid-app.onrender.com';
};

export const BACKEND_DOMAIN = getBackendDomain();
export const API_BASE = (window.location.protocol === 'https:' ? 'https://' : 'http://') + BACKEND_DOMAIN;
export const WS_BASE = (window.location.protocol === 'https:' ? 'wss://' : 'ws://') + BACKEND_DOMAIN;

/**
 * Perform JSON HTTP API requests
 */
export async function apiFetch(endpoint, options = {}) {
  const url = endpoint.startsWith('http') ? endpoint : `${API_BASE}${endpoint}`;
  const defaultHeaders = { 'Content-Type': 'application/json' };

  const config = {
    ...options,
    headers: { ...defaultHeaders, ...options.headers }
  };

  if (config.body && typeof config.body === 'object') {
    config.body = JSON.stringify(config.body);
  }

  const response = await fetch(url, config);
  if (!response.ok) {
    const errorBody = await response.text();
    throw new Error(`API ${response.status}: ${errorBody}`);
  }
  return response.json();
}

/**
 * Connect WebSocket stream with auto-reconnect capability
 */
export function connectWebSocket(path, onMessage, onStatusChange) {
  const wsUrl = `${WS_BASE}${path}`;
  let socket = null;
  let isReconnecting = false;

  function init() {
    socket = new WebSocket(wsUrl);

    socket.onopen = () => {
      isReconnecting = false;
      if (onStatusChange) onStatusChange(true);
    };

    socket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (onMessage) onMessage(data);
      } catch (err) {
        console.error("Failed to parse WebSocket message:", err);
      }
    };

    socket.onclose = () => {
      if (onStatusChange) onStatusChange(false);
      if (!isReconnecting) {
        isReconnecting = true;
        setTimeout(init, 3000);
      }
    };

    socket.onerror = (err) => {
      console.error("WebSocket error:", err);
    };
  }

  init();

  return {
    send: (data) => {
      if (socket && socket.readyState === WebSocket.OPEN) {
        socket.send(typeof data === 'string' ? data : JSON.stringify(data));
      }
    },
    close: () => {
      if (socket) socket.close();
    }
  };
}
