/**
 * SurakshaGrid Real-Time WebSocket Client
 * Manages WebSocket feeds for water level sensors, live SOS emergency alerts, and rescue dispatch telemetry.
 */

class SurakshaWebSocketClient {
  constructor(options = {}) {
    this.baseUrl = options.baseUrl || this.getDefaultWsUrl();
    this.reconnectInterval = options.reconnectInterval || 3000;
    this.maxReconnectAttempts = options.maxReconnectAttempts || 10;
    this.reconnectAttempts = 0;
    this.sockets = new Map();
    this.listeners = new Map();
  }

  getDefaultWsUrl() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    return `${protocol}//${window.location.host}/ws`;
  }

  connect(channel = 'sensors') {
    if (this.sockets.has(channel)) {
      return this.sockets.get(channel);
    }

    const url = `${this.baseUrl}/${channel}`;
    const ws = new WebSocket(url);

    ws.onopen = () => {
      console.log(`[SurakshaWS] Connected to channel: ${channel}`);
      this.reconnectAttempts = 0;
      this.emit('connected', { channel });
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        this.emit('message', { channel, data });
        if (data.type) {
          this.emit(data.type, data.payload || data);
        }
      } catch (err) {
        console.warn(`[SurakshaWS] Error parsing message from ${channel}:`, err);
      }
    };

    ws.onerror = (error) => {
      console.error(`[SurakshaWS] Socket error on channel ${channel}:`, error);
      this.emit('error', { channel, error });
    };

    ws.onclose = () => {
      console.log(`[SurakshaWS] Closed connection on channel: ${channel}`);
      this.sockets.delete(channel);
      this.emit('disconnected', { channel });

      if (this.reconnectAttempts < this.maxReconnectAttempts) {
        this.reconnectAttempts += 1;
        setTimeout(() => this.connect(channel), this.reconnectInterval);
      }
    };

    this.sockets.set(channel, ws);
    return ws;
  }

  on(event, callback) {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, new Set());
    }
    this.listeners.get(event).add(callback);
    return () => this.off(event, callback);
  }

  off(event, callback) {
    if (this.listeners.has(event)) {
      this.listeners.get(event).delete(callback);
    }
  }

  emit(event, payload) {
    if (this.listeners.has(event)) {
      this.listeners.get(event).forEach((cb) => {
        try {
          cb(payload);
        } catch (err) {
          console.error(`[SurakshaWS] Listener error for event '${event}':`, err);
        }
      });
    }
  }

  send(channel, data) {
    const ws = this.sockets.get(channel);
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(typeof data === 'string' ? data : JSON.stringify(data));
      return true;
    }
    return false;
  }

  disconnectAll() {
    this.sockets.forEach((ws) => ws.close());
    this.sockets.clear();
  }
}

window.SurakshaWS = new SurakshaWebSocketClient();
