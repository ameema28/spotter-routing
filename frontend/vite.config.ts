import react from '@vitejs/plugin-react'
import { defineConfig } from 'vitest/config'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  build: {
    // maplibre-gl alone is ~1.1 MB and already loads as its own chunk after the page, so the 500 kB
    // default warning can't be fixed by splitting further.
    chunkSizeWarningLimit: 1200,
  },
  test: {
    environment: 'node',
  },
})
