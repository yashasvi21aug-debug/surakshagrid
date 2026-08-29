"use client";

import { useCallback, useEffect, useState } from "react";
import { submitSOS, SOSPayload } from "../services/api";

export type TriageCategory = "CRITICAL_TRAPPED" | "MEDICAL_EVAC" | "FOOD_WATER";

export interface PendingSOSPayload extends SOSPayload {
  timestamp_queued: number;
}

const QUEUE_STORAGE_KEY = "pending_sos_queue";

export function useCitizenSOS() {
  const [category, setCategory] = useState<TriageCategory>("CRITICAL_TRAPPED");
  const [phone, setPhone] = useState<string>("");
  const [notes, setNotes] = useState<string>("");
  const [submitting, setSubmitting] = useState<boolean>(false);
  const [submittedId, setSubmittedId] = useState<string | null>(null);
  const [isOffline, setIsOffline] = useState<boolean>(false);
  const [queuedCount, setQueuedCount] = useState<number>(0);

  const updateQueuedCount = useCallback(() => {
    try {
      const stored = localStorage.getItem(QUEUE_STORAGE_KEY);
      const list = stored ? JSON.parse(stored) : [];
      setQueuedCount(list.length);
    } catch {
      setQueuedCount(0);
    }
  }, []);

  const saveToOfflineQueue = useCallback((payload: SOSPayload) => {
    try {
      const stored = localStorage.getItem(QUEUE_STORAGE_KEY);
      const list: PendingSOSPayload[] = stored ? JSON.parse(stored) : [];
      list.push({ ...payload, timestamp_queued: Date.now() });
      localStorage.setItem(QUEUE_STORAGE_KEY, JSON.stringify(list));
      updateQueuedCount();
    } catch (e) {
      console.error("Failed to write pending SOS to localStorage:", e);
    }
  }, [updateQueuedCount]);

  const flushOfflineQueue = useCallback(async () => {
    try {
      const stored = localStorage.getItem(QUEUE_STORAGE_KEY);
      if (!stored) return;
      const list: PendingSOSPayload[] = JSON.parse(stored);
      if (list.length === 0) return;

      const remaining: PendingSOSPayload[] = [];
      for (const item of list) {
        try {
          await submitSOS(item);
        } catch {
          remaining.push(item);
        }
      }
      localStorage.setItem(QUEUE_STORAGE_KEY, JSON.stringify(remaining));
      setQueuedCount(remaining.length);
    } catch (e) {
      console.error("Failed to replay offline SOS queue:", e);
    }
  }, []);

  useEffect(() => {
    if (typeof window === "undefined") return;
    setIsOffline(!navigator.onLine);

    const handleOnline = () => {
      setIsOffline(false);
      flushOfflineQueue();
    };

    const handleOffline = () => setIsOffline(true);

    window.addEventListener("online", handleOnline);
    window.addEventListener("offline", handleOffline);
    updateQueuedCount();

    return () => {
      window.removeEventListener("online", handleOnline);
      window.removeEventListener("offline", handleOffline);
    };
  }, [flushOfflineQueue, updateQueuedCount]);

  const transmitSOS = useCallback(
    async (lat: number, lng: number, accuracy: number) => {
      setSubmitting(true);
      const payload: SOSPayload = {
        category,
        latitude: lat,
        longitude: lng,
        accuracy,
        phone: phone || "+91-9876543210",
        notes: notes || "Immediate citizen disaster assistance requested",
        emergencyType: category,
        lat,
        lng,
      };

      if (navigator.onLine) {
        try {
          const res = await submitSOS(payload);
          setSubmittedId(res.id || "SOS-ACK-LOCAL");
        } catch (err) {
          console.warn("Online transmission failed. Queueing offline...", err);
          saveToOfflineQueue(payload);
          setSubmittedId("OFFLINE-QUEUED-" + Date.now().toString().slice(-4));
        }
      } else {
        saveToOfflineQueue(payload);
        setSubmittedId("OFFLINE-QUEUED-" + Date.now().toString().slice(-4));
      }

      setSubmitting(false);
    },
    [category, phone, notes, saveToOfflineQueue]
  );

  const resetForm = useCallback(() => {
    setSubmittedId(null);
    setNotes("");
  }, []);

  return {
    category,
    setCategory,
    phone,
    setPhone,
    notes,
    setNotes,
    submitting,
    submittedId,
    isOffline,
    queuedCount,
    transmitSOS,
    resetForm,
    flushOfflineQueue,
  };
}
