export const WS_BASE_URL =
  typeof window !== "undefined"
    ? process.env.NEXT_PUBLIC_WS_URL || "ws://localhost:8000"
    : "ws://localhost:8000";

export type WSEventCallback = (event: { type: string; event?: string; data: any }) => void;

export class SurakshaWebSocketClient {
  private socket: WebSocket | null = null;
  private listeners: Set<WSEventCallback> = new Set();
  private isConnecting: boolean = false;
  private reconnectTimer: any = null;
  private heartbeatTimer: any = null;
  private reconnectAttempts: number = 0;
  private maxReconnectDelayMs: number = 30000;
  private endpoint: string;

  constructor(endpoint: string = "/ws/dashboard") {
    this.endpoint = endpoint;
  }

  public connect(): void {
    if (this.socket && (this.socket.readyState === WebSocket.OPEN || this.socket.readyState === WebSocket.CONNECTING)) {
      return;
    }
    this.isConnecting = true;
    
    // Support relative WebSocket URL resolution
    let baseUrl = WS_BASE_URL;
    if (baseUrl.startsWith("http://")) baseUrl = baseUrl.replace("http://", "ws://");
    if (baseUrl.startsWith("https://")) baseUrl = baseUrl.replace("https://", "wss://");

    const url = `${baseUrl}${this.endpoint}`;
    try {
      this.socket = new WebSocket(url);

      this.socket.onopen = () => {
        this.isConnecting = false;
        this.reconnectAttempts = 0;
        console.log(`WebSocket connected to ${url}`);
        this.startHeartbeat();
      };

      this.socket.onmessage = (messageEvent) => {
        try {
          const payload = JSON.parse(messageEvent.data);
          if (payload.type === "pong") return;
          this.listeners.forEach((callback) => callback(payload));
        } catch (error) {
          console.error("Failed to parse WebSocket JSON payload:", error);
        }
      };

      this.socket.onclose = () => {
        this.isConnecting = false;
        this.stopHeartbeat();
        this.scheduleReconnect();
      };

      this.socket.onerror = (err) => {
        console.warn("WebSocket connection error:", err);
        this.socket?.close();
      };
    } catch (err) {
      this.isConnecting = false;
      this.stopHeartbeat();
      this.scheduleReconnect();
    }
  }

  private startHeartbeat(): void {
    this.stopHeartbeat();
    this.heartbeatTimer = setInterval(() => {
      if (this.socket && this.socket.readyState === WebSocket.OPEN) {
        this.socket.send(JSON.stringify({ type: "ping" }));
      }
    }, 25000); // 25-second interval keeps Render / HTTP proxy sockets active
  }

  private stopHeartbeat(): void {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer);
      this.heartbeatTimer = null;
    }
  }

  private scheduleReconnect(): void {
    if (this.reconnectTimer) return;
    this.reconnectAttempts += 1;

    // Exponential backoff with jitter: 1s, 2s, 4s, 8s, 16s... up to 30s cap
    const delay = Math.min(
      this.maxReconnectDelayMs,
      1000 * Math.pow(2, this.reconnectAttempts - 1) + Math.random() * 500
    );

    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null;
      this.connect();
    }, delay);
  }

  public subscribe(callback: WSEventCallback): () => void {
    this.listeners.add(callback);
    if (!this.socket || this.socket.readyState !== WebSocket.OPEN) {
      this.connect();
    }
    return () => {
      this.listeners.delete(callback);
    };
  }

  public disconnect(): void {
    this.stopHeartbeat();
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    if (this.socket) {
      this.socket.close();
      this.socket = null;
    }
  }
}

export const wsClient = new SurakshaWebSocketClient("/ws");
