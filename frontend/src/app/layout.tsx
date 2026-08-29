import './globals.css';
import type { Metadata, Viewport } from 'next';

export const metadata: Metadata = {
  title: 'SurakshaGrid | Real-Time Disaster Response & Spatial Emergency Grid',
  description: 'AI-driven spatial hazard analysis, emergency corridor routing, and citizen SOS telemetry portal.',
  manifest: '/manifest.json',
};

export const viewport: Viewport = {
  themeColor: '#0f172a',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <head>
        <link rel="manifest" href="/manifest.json" />
        <link
          href="https://unpkg.com/maplibre-gl@4.1.0/dist/maplibre-gl.css"
          rel="stylesheet"
        />
      </head>
      <body className="bg-suraksha-bg text-slate-100 antialiased selection:bg-cyan-500 selection:text-white">
        {children}
        <script
          dangerouslySetInnerHTML={{
            __html: `
              if ('serviceWorker' in navigator) {
                window.addEventListener('load', function() {
                  navigator.serviceWorker.register('/sw.js').then(
                    function(reg) { console.log('[PWA] ServiceWorker registered with scope:', reg.scope); },
                    function(err) { console.log('[PWA] ServiceWorker registration failed:', err); }
                  );
                });
              }
            `,
          }}
        />
      </body>
    </html>
  );
}
