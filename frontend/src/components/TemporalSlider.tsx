"use client";

import React, { useEffect, useState } from "react";

export interface PlaybackSnapshot {
  step_index: number;
  timestamp: string;
  inundation_zones: any;
  sensors: any[];
  sos_count: number;
}

interface TemporalSliderProps {
  onSnapshotChange?: (snapshot: PlaybackSnapshot) => void;
}

export default function TemporalSlider({ onSnapshotChange }: TemporalSliderProps) {
  const [snapshots, setSnapshots] = useState<PlaybackSnapshot[]>([]);
  const [currentIndex, setCurrentIndex] = useState<number>(0);
  const [isPlaying, setIsPlaying] = useState<boolean>(false);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  // 1. Fetch Temporal Replay Snapshots from Backend
  useEffect(() => {
    async function fetchPlaybackData() {
      setIsLoading(true);
      try {
        const res = await fetch(
          `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/v1/spatial/temporal-playback?step_hours=1`
        );
        if (res.ok) {
          const data = await res.json();
          if (data.snapshots && data.snapshots.length > 0) {
            setSnapshots(data.snapshots);
            if (onSnapshotChange) onSnapshotChange(data.snapshots[0]);
          }
        }
      } catch (err) {
        console.warn("Temporal playback fetch fallback:", err);
      } finally {
        setIsLoading(false);
      }
    }
    fetchPlaybackData();
  }, []);

  // 2. Automated Replay Timer Worker
  useEffect(() => {
    let timer: NodeJS.Timeout | null = null;
    if (isPlaying && snapshots.length > 0) {
      timer = setInterval(() => {
        setCurrentIndex((prev) => {
          const nextIdx = (prev + 1) % snapshots.length;
          if (onSnapshotChange) onSnapshotChange(snapshots[nextIdx]);
          return nextIdx;
        });
      }, 1000); // 1-second step interval
    }
    return () => {
      if (timer) clearInterval(timer);
    };
  }, [isPlaying, snapshots, onSnapshotChange]);

  const handleSliderChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const idx = parseInt(e.target.value, 10);
    setCurrentIndex(idx);
    if (snapshots[idx] && onSnapshotChange) {
      onSnapshotChange(snapshots[idx]);
    }
  };

  const currentSnapshot = snapshots[currentIndex];
  const formattedTime = currentSnapshot?.timestamp
    ? new Date(currentSnapshot.timestamp).toLocaleString("en-US", {
        month: "short",
        day: "numeric",
        hour: "2-digit",
        minute: "2-digit",
      })
    : "Live Feed";

  return (
    <div className="w-full max-w-xl rounded-2xl border border-slate-800 bg-slate-900/90 p-3.5 backdrop-blur-xl shadow-2xl">
      <div className="flex items-center justify-between gap-3 mb-2.5">
        <div className="flex items-center gap-2.5">
          <button
            onClick={() => setIsPlaying(!isPlaying)}
            disabled={isLoading || snapshots.length === 0}
            className="flex h-9 w-9 items-center justify-center rounded-xl bg-cyan-500/20 text-cyan-400 hover:bg-cyan-500/30 border border-cyan-500/40 transition active:scale-95 disabled:opacity-40"
          >
            {isPlaying ? (
              <svg className="h-4 w-4" fill="currentColor" viewBox="0 0 24 24">
                <path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z" />
              </svg>
            ) : (
              <svg className="h-4 w-4 ml-0.5" fill="currentColor" viewBox="0 0 24 24">
                <path d="M8 5v14l11-7z" />
              </svg>
            )}
          </button>

          <div>
            <div className="flex items-center gap-2">
              <span className="font-mono text-[10px] uppercase font-bold tracking-widest text-cyan-400">TEMPORAL REPLAY</span>
              <span className="rounded bg-slate-800 px-1.5 py-0.5 text-[9px] font-mono text-slate-400 border border-slate-700">24H TIMELINE</span>
            </div>
            <div className="font-mono text-xs font-bold text-slate-100">{formattedTime}</div>
          </div>
        </div>

        <div className="flex items-center gap-3 text-[11px] font-mono text-slate-400">
          <div>
            <span className="text-slate-500">SOS: </span>
            <span className="text-amber-400 font-bold">{currentSnapshot?.sos_count || 0}</span>
          </div>
          <div>
            <span className="text-slate-500">Step: </span>
            <span className="text-emerald-400 font-bold">{currentIndex + 1}/{snapshots.length || 1}</span>
          </div>
        </div>
      </div>

      {/* Interactive Timeline Scrubber Slider */}
      <input
        type="range"
        min={0}
        max={Math.max(0, snapshots.length - 1)}
        value={currentIndex}
        onChange={handleSliderChange}
        disabled={isLoading || snapshots.length === 0}
        className="h-2 w-full cursor-pointer appearance-none rounded-lg bg-slate-800 accent-cyan-400 disabled:opacity-40"
      />
    </div>
  );
}
