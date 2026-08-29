import Link from 'next/link';
import { AlertTriangle, ShieldAlert, Navigation, Activity } from 'lucide-react';

export default function Home() {
  return (
    <main className="min-h-screen flex flex-col justify-center items-center px-4 py-12 bg-gradient-to-b from-slate-950 via-suraksha-bg to-slate-950 relative overflow-hidden">
      {/* Subtle background glow */}
      <div className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-cyan-600/10 rounded-full blur-[140px] pointer-events-none" />

      <div className="max-w-4xl w-full text-center z-10 space-y-8">
        <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full glass-panel border-cyan-500/30 text-cyan-400 text-sm font-medium tracking-wide uppercase">
          <Activity className="w-4 h-4 animate-pulse" />
          <span>SurakshaGrid PRD v1.0.0 Active</span>
        </div>

        <h1 className="text-4xl md:text-6xl font-extrabold text-transparent bg-clip-text bg-gradient-to-r from-white via-slate-200 to-cyan-400 tracking-tight">
          Spatial Emergency & Digital Twin Command Grid
        </h1>

        <p className="text-lg md:text-xl text-slate-400 max-w-2xl mx-auto font-light leading-relaxed">
          Dynamic SAR flood polygon analysis, low-latency mobile SOS telemetry, and OSRM evasive green corridor routing.
        </p>

        <div className="grid md:grid-cols-2 gap-6 max-w-2xl mx-auto pt-6">
          <Link
            href="/citizen"
            className="group glass-panel p-8 rounded-2xl border-emerald-500/20 hover:border-emerald-500/50 transition-all duration-300 hover:shadow-2xl hover:shadow-emerald-500/10 text-left relative overflow-hidden"
          >
            <div className="w-12 h-12 rounded-xl bg-emerald-500/10 border border-emerald-500/30 flex items-center justify-center text-emerald-400 mb-6 group-hover:scale-110 transition-transform">
              <ShieldAlert className="w-6 h-6" />
            </div>
            <h2 className="text-2xl font-bold text-white mb-2 group-hover:text-emerald-400 transition-colors">
              Citizen Emergency SOS
            </h2>
            <p className="text-slate-400 text-sm leading-relaxed">
              Zero-login mobile portal capturing HTML5 GPS coordinates, triage urgency selection, and offline caching.
            </p>
            <div className="mt-6 flex items-center text-emerald-400 text-sm font-semibold gap-1">
              Launch Portal &rarr;
            </div>
          </Link>

          <Link
            href="/dashboard"
            className="group glass-panel p-8 rounded-2xl border-cyan-500/20 hover:border-cyan-500/50 transition-all duration-300 hover:shadow-2xl hover:shadow-cyan-500/10 text-left relative overflow-hidden"
          >
            <div className="w-12 h-12 rounded-xl bg-cyan-500/10 border border-cyan-500/30 flex items-center justify-center text-cyan-400 mb-6 group-hover:scale-110 transition-transform">
              <Navigation className="w-6 h-6" />
            </div>
            <h2 className="text-2xl font-bold text-white mb-2 group-hover:text-cyan-400 transition-colors">
              EOC Command Dashboard
            </h2>
            <p className="text-slate-400 text-sm leading-relaxed">
              MapLibre GL vector map displaying live flood polygons, river gauge telemetry, and OSRM safe corridor routing.
            </p>
            <div className="mt-6 flex items-center text-cyan-400 text-sm font-semibold gap-1">
              Enter Command Grid &rarr;
            </div>
          </Link>
        </div>
      </div>
    </main>
  );
}
