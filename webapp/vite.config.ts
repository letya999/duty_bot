import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

// https://vitejs.dev/config/
export default defineConfig(({ mode }) => {
  // Load env file based on `mode` in the current working directory.
  // Set the third parameter to '' to load all env instead of just those starting with `VITE_`.
  const env = loadEnv(mode, process.cwd(), '');

  const backendUrl = env.VITE_API_BACKEND || 'http://app:8000';
  const appHost = env.VITE_APP_HOST;
  const webPort = parseInt(env.VITE_PORT || '5173');
  const hmrPort = parseInt(env.VITE_HMR_PORT || '443');

  // Determine allowed hosts based on environment
  const allowedHosts = appHost
    ? [appHost, 'localhost', '.ngrok-free.dev']
    : ['localhost', '.ngrok-free.dev'];

  return {
    plugins: [react()],
    server: {
      port: webPort,
      host: '0.0.0.0',
      allowedHosts,
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
        },
        '/api': {
          target: backendUrl,
          changeOrigin: true,
          rewrite: (path) => path
        }
      },
      hmr: appHost ? {
        host: appHost,
        clientPort: hmrPort
      } : undefined
    },
    build: {
      outDir: 'dist',
      assetsDir: 'assets'
    }
  }
})
