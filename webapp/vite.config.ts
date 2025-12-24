import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    host: '0.0.0.0',
    allowedHosts: ['rona-isobathythermal-nondeficiently.ngrok-free.dev']
  },
  build: {
    outDir: 'dist',
    assetsDir: 'assets'
  }
})
