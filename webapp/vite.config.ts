import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Determine backend URL based on environment
const backendUrl = process.env.VITE_API_BACKEND || 'http://app:8000'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    host: '0.0.0.0',
    allowedHosts: ['rona-isobathythermal-nondeficiently.ngrok-free.dev', 'localhost'],
    proxy: {
      '/web': {
        target: backendUrl,
        changeOrigin: true,
        rewrite: (path) => path
      },
      '/slack': {
        target: backendUrl,
        changeOrigin: true,
        rewrite: (path) => path
      }
    }
  },
  build: {
    outDir: 'dist',
    assetsDir: 'assets'
  }
})
