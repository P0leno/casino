import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  base: './',
  server: {
    host: true, // This enables listening on all addresses
    port: 5173,
    strictPort: true,
    allowedHosts: ['93963a64d69e.ngrok-free.app']
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks(id) {
          // Разбиваем большие JSON анимации на отдельные чанки
          if (id.includes('/assets/') && id.endsWith('.json')) {
            const fileName = id.split('/').pop().replace('.json', '')
            return `animations/${fileName}`
          }
          // Vendor чанк для node_modules
          if (id.includes('node_modules')) {
            return 'vendor'
          }
        }
      }
    },
    chunkSizeWarningLimit: 1000
  }
})
