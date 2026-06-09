import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'node:path'

// Build output goes into the Frappe app's public assets so Frappe's web server
// can serve the SPA at /assets/diagnostic_management/frontend/ and the bench-
// generated route /diagnostic_management.
//
// During dev, run `npm run dev` and proxy /api to the Frappe site.

const FRAPPE_SITE = 'http://localhost:8008'

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, 'src'),
      // Re-route bare `frappe-ui` imports (left over in some ported pages) to
      // a local shim that re-exports our in-tree replacements.
      'frappe-ui': path.resolve(__dirname, 'src/shims/frappe-ui.ts'),
    },
  },
  server: {
    port: 5273,
    proxy: {
      '/api': { target: FRAPPE_SITE, changeOrigin: true },
      '/assets': { target: FRAPPE_SITE, changeOrigin: true },
      '/files': { target: FRAPPE_SITE, changeOrigin: true },
      '/private/files': { target: FRAPPE_SITE, changeOrigin: true },
    },
  },
  base: '/assets/diagnostic_management/frontend/',
  build: {
    outDir: path.resolve(__dirname, '..', 'diagnostic_management', 'public', 'frontend'),
    emptyOutDir: true,
    target: 'es2020',
    sourcemap: true,
    // Emit .vite/manifest.json so the Frappe SPA shell (www/diagnostic_management.py)
    // can resolve the hashed entry + css filenames at request time.
    manifest: true,
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ['vue', 'vue-router', 'pinia'],
        },
      },
    },
  },
})
