"use client";

import { useState } from "react";
import {
  AlertTriangle,
  CheckCircle2,
  HeartPulse,
  LifeBuoy,
  MapPin,
  Phone,
  Radio,
  RefreshCw,
  ShieldAlert,
  Wifi,
  WifiOff,
} from "lucide-react";
import { useGeolocation } from "../../hooks/useGeolocation";
import { useCitizenSOS, TriageCategory } from "../../hooks/useCitizenSOS";

export default function CitizenSOSPage() {
  const {
    latitude,
    longitude,
    accuracy,
    loading: locating,
    error: locError,
    acquireLocation,
    setManualCoords,
  } = useGeolocation();

  const {
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
  } = useCitizenSOS();

  const [showManualInput, setShowManualInput] = useState<boolean>(false);
  const [manualLat, setManualLat] = useState<string>("");
  const [manualLng, setManualLng] = useState<string>("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!latitude || !longitude) {
      alert("GPS location pending lock. Please retry or enter manual coordinates.");
      return;
    }
    transmitSOS(latitude, longitude, accuracy || 10);
  };

  const handleApplyManualCoords = () => {
    const parsedLat = parseFloat(manualLat);
    const parsedLng = parseFloat(manualLng);
    if (!isNaN(parsedLat) && !isNaN(parsedLng)) {
      setManualCoords(parsedLat, parsedLng);
      setShowManualInput(false);
    } else {
      alert("Please enter valid decimal coordinates (e.g. 28.6321, 77.4446)");
    }
  };

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col items-center justify-center p-4 selection:bg-red-500 selection:text-white">
      {/* Header Banner */}
      <header className="w-full max-w-lg mb-6 flex items-center justify-between border-b border-slate-800 pb-4">
        <div className="flex items-center gap-2">
          <ShieldAlert className="w-8 h-8 text-red-500 animate-pulse" />
          <div>
            <h1 className="text-xl font-bold tracking-tight text-white flex items-center gap-2">
              SURAKSHA<span className="text-red-500 font-mono">GRID</span>
            </h1>
            <p className="text-xs text-slate-400">Mobile Citizen Emergency SOS Portal (PRD v1.0.0)</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          {isOffline ? (
            <span className="flex items-center gap-1 text-xs bg-amber-950/80 text-amber-400 border border-amber-800/60 px-2.5 py-1 rounded-full font-mono">
              <WifiOff className="w-3.5 h-3.5" /> OFFLINE QUEUE
            </span>
          ) : (
            <span className="flex items-center gap-1 text-xs bg-emerald-950/80 text-emerald-400 border border-emerald-800/60 px-2.5 py-1 rounded-full font-mono">
              <Wifi className="w-3.5 h-3.5" /> LIVE CONNECTED
            </span>
          )}
        </div>
      </header>

      {/* Main Container */}
      <main className="w-full max-w-lg bg-slate-900 border border-slate-800 rounded-2xl p-5 shadow-2xl space-y-6">
        {submittedId ? (
          <div className="text-center py-8 space-y-4">
            <div className="w-16 h-16 bg-emerald-500/20 text-emerald-400 border border-emerald-500/40 rounded-full flex items-center justify-center mx-auto shadow-lg shadow-emerald-500/20">
              <CheckCircle2 className="w-10 h-10" />
            </div>
            <h2 className="text-2xl font-bold text-white">Distress Telemetry Transmitted</h2>
            <p className="text-sm text-slate-300">
              NDRF Emergency Command Center & local evacuation teams have logged your location payload.
            </p>

            <div className="bg-slate-950 border border-slate-800 rounded-xl p-4 text-left font-mono text-xs space-y-2">
              <div className="flex justify-between text-slate-400">
                <span>INCIDENT ACK ID:</span>
                <span className="text-emerald-400 font-bold">{submittedId}</span>
              </div>
              <div className="flex justify-between text-slate-400">
                <span>GPS POSITION:</span>
                <span className="text-slate-200">{latitude?.toFixed(5)}, {longitude?.toFixed(5)}</span>
              </div>
              <div className="flex justify-between text-slate-400">
                <span>TRIAGE SEVERITY:</span>
                <span className="text-red-400 font-bold">{category}</span>
              </div>
            </div>

            <button
              onClick={resetForm}
              className="w-full py-3 bg-slate-800 hover:bg-slate-700 text-white rounded-xl font-medium transition"
            >
              Submit Additional SOS Signal
            </button>
          </div>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-6">
            {/* Triage Selection Buttons */}
            <div>
              <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">
                1. Select Emergency Triage Level
              </label>
              <div className="grid grid-cols-3 gap-2.5">
                <button
                  type="button"
                  onClick={() => setCategory("CRITICAL_TRAPPED")}
                  className={`p-3.5 rounded-xl border flex flex-col items-center justify-center gap-2 text-center transition ${
                    category === "CRITICAL_TRAPPED"
                      ? "bg-red-950/80 border-red-500 text-red-200 ring-2 ring-red-500/50 shadow-lg shadow-red-900/30"
                      : "bg-slate-950/60 border-slate-800 text-slate-400 hover:border-slate-700"
                  }`}
                >
                  <LifeBuoy className="w-7 h-7 text-red-400 animate-bounce" />
                  <span className="text-xs font-bold leading-tight">Trapped in Flood</span>
                </button>

                <button
                  type="button"
                  onClick={() => setCategory("MEDICAL_EVAC")}
                  className={`p-3.5 rounded-xl border flex flex-col items-center justify-center gap-2 text-center transition ${
                    category === "MEDICAL_EVAC"
                      ? "bg-orange-950/80 border-orange-500 text-orange-200 ring-2 ring-orange-500/50 shadow-lg shadow-orange-900/30"
                      : "bg-slate-950/60 border-slate-800 text-slate-400 hover:border-slate-700"
                  }`}
                >
                  <HeartPulse className="w-7 h-7 text-orange-400" />
                  <span className="text-xs font-bold leading-tight">Medical Evac</span>
                </button>

                <button
                  type="button"
                  onClick={() => setCategory("FOOD_WATER")}
                  className={`p-3.5 rounded-xl border flex flex-col items-center justify-center gap-2 text-center transition ${
                    category === "FOOD_WATER"
                      ? "bg-sky-950/80 border-sky-500 text-sky-200 ring-2 ring-sky-500/50 shadow-lg shadow-sky-900/30"
                      : "bg-slate-950/60 border-slate-800 text-slate-400 hover:border-slate-700"
                  }`}
                >
                  <Radio className="w-7 h-7 text-sky-400" />
                  <span className="text-xs font-bold leading-tight">Food & Water</span>
                </button>
              </div>
            </div>

            {/* GPS Telemetry Bar */}
            <div className="bg-slate-950 border border-slate-800 rounded-xl p-3.5 space-y-2 text-xs font-mono">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <MapPin className={`w-4 h-4 ${latitude ? "text-emerald-400" : "text-amber-400 animate-spin"}`} />
                  <span className="text-slate-400">HIGH-ACCURACY GPS POSITION:</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <button
                    type="button"
                    onClick={acquireLocation}
                    className="p-1.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-lg transition"
                    title="Refresh GPS Satellite Lock"
                  >
                    <RefreshCw className="w-3.5 h-3.5" />
                  </button>
                  <button
                    type="button"
                    onClick={() => setShowManualInput(!showManualInput)}
                    className="text-[11px] underline text-slate-400 hover:text-white"
                  >
                    {showManualInput ? "Hide Pin" : "Manual Coords"}
                  </button>
                </div>
              </div>

              <div className="text-slate-200 font-bold">
                {locating
                  ? "Acquiring satellite GPS lock (enable high accuracy)..."
                  : `${latitude?.toFixed(5)}°N, ${longitude?.toFixed(5)}°E (±${accuracy ? Math.round(accuracy) : 10}m)`}
              </div>

              {showManualInput && (
                <div className="pt-2 border-t border-slate-800 flex items-center gap-2">
                  <input
                    type="text"
                    placeholder="Lat (e.g. 28.6321)"
                    value={manualLat}
                    onChange={(e) => setManualLat(e.target.value)}
                    className="w-1/2 bg-slate-900 border border-slate-700 px-2 py-1 text-white rounded"
                  />
                  <input
                    type="text"
                    placeholder="Lng (e.g. 77.4446)"
                    value={manualLng}
                    onChange={(e) => setManualLng(e.target.value)}
                    className="w-1/2 bg-slate-900 border border-slate-700 px-2 py-1 text-white rounded"
                  />
                  <button
                    type="button"
                    onClick={handleApplyManualCoords}
                    className="bg-emerald-700 hover:bg-emerald-600 px-2.5 py-1 text-white rounded font-sans text-xs font-bold"
                  >
                    Set
                  </button>
                </div>
              )}
            </div>
            {locError && <p className="text-[11px] text-amber-400 font-mono italic">{locError}</p>}

            {/* Contact Phone & Notes */}
            <div className="space-y-3">
              <div>
                <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1.5">
                  Mobile Contact Number
                </label>
                <div className="relative">
                  <Phone className="w-4 h-4 absolute left-3.5 top-3 text-slate-500" />
                  <input
                    type="tel"
                    placeholder="+91 98765 43210"
                    value={phone}
                    onChange={(e) => setPhone(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 rounded-xl pl-10 pr-3 py-2.5 text-sm text-white focus:outline-none focus:border-red-500 font-mono"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1.5">
                  Situational Notes (e.g., 3 people on terrace, water rising)
                </label>
                <textarea
                  rows={2}
                  placeholder="Describe your current status..."
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  className="w-full bg-slate-950 border border-slate-800 rounded-xl p-3 text-sm text-white focus:outline-none focus:border-red-500"
                />
              </div>
            </div>

            {/* Submit Emergency Button */}
            <button
              type="submit"
              disabled={submitting}
              className="w-full py-4 bg-gradient-to-r from-red-600 to-red-700 hover:from-red-500 hover:to-red-600 text-white rounded-xl font-bold text-base shadow-lg shadow-red-900/40 flex items-center justify-center gap-2 transition disabled:opacity-50"
            >
              {submitting ? (
                <>
                  <RefreshCw className="w-5 h-5 animate-spin" /> TRANSMITTING SOS TELEMETRY...
                </>
              ) : (
                <>
                  <AlertTriangle className="w-5 h-5" /> TRANSMIT SOS EMERGENCY SIGNAL
                </>
              )}
            </button>

            {queuedCount > 0 && (
              <div className="bg-amber-950/40 border border-amber-800/50 rounded-xl p-3 text-center text-xs text-amber-300 font-mono">
                📦 {queuedCount} offline SOS payload(s) stored in localStorage queue. Will auto-sync upon reconnection.
              </div>
            )}
          </form>
        )}
      </main>
    </div>
  );
}
