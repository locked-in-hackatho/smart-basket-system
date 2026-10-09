import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import basicSsl from '@vitejs/plugin-basic-ssl'
import { defineConfig } from 'vite'

// HTTPS is opt-in (`npm run dev:https`). Browsers only grant camera access on
// localhost or over HTTPS, so a phone on the local network needs it.
const useHttps = process.env.HTTPS === '1'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss(), ...(useHttps ? [basicSsl()] : [])],
  server: {
    // Listen on all interfaces so a phone on the same Wi-Fi can connect.
    host: true,
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
})
