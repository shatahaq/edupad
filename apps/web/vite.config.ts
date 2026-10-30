import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// `npm run dev`: /api dan /auth diteruskan ke `python -m edupad serve`, sehingga halaman,
// login Google, dan cookie sesi memakai satu origin (http://localhost:5173).
const backend = "http://127.0.0.1:8000";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    strictPort: true, // redirect URI Google didaftarkan untuk port ini
    // /dashboard: dashboard EduPad (`cd dashboard && npm run dev`, port 5174)
    proxy: { "/api": backend, "/auth": backend, "/dashboard": "http://localhost:5174" },
  },
  build: {
    outDir: "dist",
    sourcemap: false,
    // Jangan sisipkan font kecil sebagai data: URI; CSP web EduPad (webapp.py) hanya
    // mengizinkan font dari 'self', jadi font data: diblokir browser.
    assetsInlineLimit: (file) => (/\.woff2?$/.test(file) ? false : undefined),
  },
});
