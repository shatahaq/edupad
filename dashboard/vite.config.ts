import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Disajikan di https://shata.id/dashboard/ oleh Office API (port 8001), di belakang Caddy.
// Dev: http://localhost:5174/dashboard/ (login dulu di web EduPad http://localhost:5173 agar
// cookie sesi Google ikut terkirim; cookie tidak dibedakan per port).
const office = "http://127.0.0.1:8001"; // python -m edupad office-api
const web = "http://127.0.0.1:8000"; // python -m edupad serve (login Google, /api/me)

export default defineConfig({
  plugins: [react()],
  base: "/dashboard/",
  publicDir: "../frontend/public",
  // Kode game di ../frontend/src memakai React/Phaser yang sama dengan dashboard (satu salinan).
  resolve: { dedupe: ["react", "react-dom", "phaser"] },
  server: {
    host: "localhost",
    port: 5174,
    strictPort: true,
    fs: { allow: [".."] },
    proxy: {
      "/api/office": { target: office, changeOrigin: true },
      "/v1/dashboard": { target: office, changeOrigin: true },
      "/api/me": { target: web },
      "/auth": { target: web },
    },
  },
});
