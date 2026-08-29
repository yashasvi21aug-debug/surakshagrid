import { create } from "zustand";

export interface IncidentItem {
  id: string;
  phone_number: string;
  category: "CRITICAL_TRAPPED" | "MEDICAL_EVAC" | "FOOD_WATER" | "INFRASTRUCTURE_DAMAGE" | string;
  lat: number;
  lng: number;
  notes?: string;
  status: "PENDING" | "ACKNOWLEDGED" | "DISPATCHED" | "ON_SCENE" | "RESOLVED" | string;
  timestamp: string;
  rain_rate?: number;
  risk_status?: string;
}

export interface SensorTelemetryItem {
  sensor_id: string;
  name: string;
  water_level_m: number;
  threshold_m: number;
  status: string;
  is_alert: boolean;
  timestamp: string;
}

export interface CommandStoreState {
  // Real-Time Reactive Collections
  incidents: IncidentItem[];
  sensors: SensorTelemetryItem[];
  inundationZones: any;
  selectedIncidentId: string | null;
  activeCorridorRoute: any;
  filterCategory: string | null;
  filterStatus: string | null;
  unreadCriticalCount: number;

  // Actions
  setIncidents: (incidents: IncidentItem[]) => void;
  addOrUpdateIncident: (incident: IncidentItem) => void;
  setSensors: (sensors: SensorTelemetryItem[]) => void;
  updateSensor: (sensor: SensorTelemetryItem) => void;
  setInundationZones: (zones: any) => void;
  setSelectedIncidentId: (id: string | null) => void;
  setActiveCorridorRoute: (route: any) => void;
  setFilterCategory: (category: string | null) => void;
  setFilterStatus: (status: string | null) => void;
  resetUnreadCount: () => void;

  // WebSocket Real-Time Event Reducer
  processWSEvent: (eventPayload: { type: string; event?: string; data: any }) => void;
}

export const useCommandStore = create<CommandStoreState>((set, get) => ({
  incidents: [],
  sensors: [],
  inundationZones: null,
  selectedIncidentId: null,
  activeCorridorRoute: null,
  filterCategory: null,
  filterStatus: null,
  unreadCriticalCount: 0,

  setIncidents: (incidents) => set({ incidents }),

  addOrUpdateIncident: (incident) =>
    set((state) => {
      const existingIdx = state.incidents.findIndex((item) => item.id === incident.id);
      let updatedList = [...state.incidents];
      let isCriticalNew = false;

      if (existingIdx >= 0) {
        updatedList[existingIdx] = { ...updatedList[existingIdx], ...incident };
      } else {
        updatedList = [incident, ...updatedList];
        if (incident.category === "CRITICAL_TRAPPED") {
          isCriticalNew = true;
        }
      }

      // Trigger visual/audio alert notice for critical events
      if (isCriticalNew && typeof window !== "undefined") {
        try {
          const audio = new Audio("/alert.mp3");
          audio.play().catch(() => {});
        } catch {}
      }

      return {
        incidents: updatedList,
        unreadCriticalCount: isCriticalNew
          ? state.unreadCriticalCount + 1
          : state.unreadCriticalCount,
      };
    }),

  setSensors: (sensors) => set({ sensors }),

  updateSensor: (sensor) =>
    set((state) => {
      const existingIdx = state.sensors.findIndex((item) => item.sensor_id === sensor.sensor_id);
      let updatedList = [...state.sensors];
      if (existingIdx >= 0) {
        updatedList[existingIdx] = { ...updatedList[existingIdx], ...sensor };
      } else {
        updatedList.push(sensor);
      }
      return { sensors: updatedList };
    }),

  setInundationZones: (inundationZones) => set({ inundationZones }),

  setSelectedIncidentId: (selectedIncidentId) => set({ selectedIncidentId }),

  setActiveCorridorRoute: (activeCorridorRoute) => set({ activeCorridorRoute }),

  setFilterCategory: (filterCategory) => set({ filterCategory }),

  setFilterStatus: (filterStatus) => set({ filterStatus }),

  resetUnreadCount: () => set({ unreadCriticalCount: 0 }),

  processWSEvent: (payload) => {
    const eventType = payload.type || payload.event;
    const data = payload.data;
    if (!data) return;

    switch (eventType) {
      case "NEW_INCIDENT":
      case "NEW_SOS":
        get().addOrUpdateIncident({
          id: data.id,
          phone_number: data.phone_number || data.phone || "+91-9876543210",
          category: data.category || data.emergency_type || "CRITICAL_TRAPPED",
          lat: data.lat || data.latitude,
          lng: data.lng || data.longitude,
          notes: data.notes,
          status: data.status || "PENDING",
          timestamp: data.timestamp || new Date().toISOString(),
          rain_rate: data.rain_rate,
          risk_status: data.risk_status,
        });
        break;

      case "INCIDENT_STATUS_CHANGED":
      case "SOS_STATUS_UPDATE":
      case "DISPATCH_STATUS_CHANGED":
      case "SOS_ACKNOWLEDGED":
      case "SOS_RESOLVED":
        if (data.id || data.sos_id) {
          get().addOrUpdateIncident({
            id: data.id || data.sos_id,
            phone_number: data.phone_number || "",
            category: data.emergency_type || data.category || "CRITICAL_TRAPPED",
            lat: data.lat || 28.6321,
            lng: data.lng || 77.4446,
            status: data.status,
            notes: data.notes,
            timestamp: data.timestamp || new Date().toISOString(),
          });
        }
        break;

      case "UNIT_DISPATCHED":
        if (data.sos_id) {
          get().addOrUpdateIncident({
            id: data.sos_id,
            phone_number: "",
            category: "CRITICAL_TRAPPED",
            lat: data.destination?.[1] || 28.6321,
            lng: data.destination?.[0] || 77.4446,
            status: "DISPATCHED",
            timestamp: data.timestamp || new Date().toISOString(),
          });
          if (data.safe_corridor) {
            get().setActiveCorridorRoute(data.safe_corridor);
          }
        }
        break;

      case "HAZARD_LAYER_UPDATE":
        get().setInundationZones(data);
        break;

      case "SENSOR_ALERT":
        get().updateSensor({
          sensor_id: data.sensor_id,
          name: data.name,
          water_level_m: data.water_level_m,
          threshold_m: data.threshold_m,
          status: data.status,
          is_alert: data.is_alert,
          timestamp: data.timestamp,
        });
        break;

      default:
        break;
    }
  },
}));
