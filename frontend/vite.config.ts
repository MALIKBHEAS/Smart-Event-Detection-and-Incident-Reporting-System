import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import { VitePWA } from 'vite-plugin-pwa'

// The backend does not enable CORS, so in local dev we proxy `/api/*` to the
// FastAPI server and strip the prefix -- e.g. `/api/health` -> `/health` on
// http://localhost:8000. This means the frontend code never has to special
// case dev vs. prod: it always calls `${VITE_API_BASE_URL}/health` etc, and
// VITE_API_BASE_URL defaults to `/api` (see src/api/client.ts). In
// production, put a reverse proxy in front that does the same thing (see
// README / docker-compose).
const BACKEND_ORIGIN = process.env.VITE_BACKEND_ORIGIN ?? 'http://localhost:8000'

export default defineConfig({
  plugins: [
    react(),
    VitePWA({
      registerType: 'autoUpdate',
      includeAssets: ['favicon.ico', 'apple-touch-icon.png', 'mask-icon.svg'],
      manifest: {
        name: 'Sentinel SOC',
        short_name: 'Sentinel',
        description: 'Smart Event Detection and Security Operations Center',
        theme_color: '#121212',
        background_color: '#121212',
        display: 'standalone',
        start_url: '/',
        icons: [
          {
            src: 'pwa-192x192.png',
            sizes: '192x192',
            type: 'image/png'
          },
          {
            src: 'pwa-512x512.png',
            sizes: '512x512',
            type: 'image/png'
          },
          {
            src: 'pwa-512x512.png',
            sizes: '512x512',
            type: 'image/png',
            purpose: 'any maskable'
          }
        ]
      },
      workbox: {
        // Exclude API requests, WS, MJPEG streams from being cached by the service worker
        navigateFallbackDenylist: [/^\/api/],
        runtimeCaching: [
          {
            urlPattern: /^\/api\//,
            handler: 'NetworkOnly'
          }
        ]
      }
    })
  ],
  build: {
    rollupOptions: {
      output: {
        manualChunks(id: string) {
          if (id.includes("@mui/x-data-grid")) return "vendor-datagrid";
          if (id.includes("recharts")) return "vendor-charts";
          if (id.includes("framer-motion")) return "vendor-motion";
          if (id.includes("@tanstack/react-query")) return "vendor-query";
          if (id.includes("@mui/material") || id.includes("@mui/icons-material") || id.includes("@emotion")) return "vendor-mui";
        },
      },
    },
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: BACKEND_ORIGIN,
        changeOrigin: true,
        ws: true,
        rewrite: (path) => path.replace(/^\/api/, ''),
      },
    },
  },
})
