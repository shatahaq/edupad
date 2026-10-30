import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Dashboard EduPad versi kedua (tema neo-brutalism). Halaman, data, dan logikanya sama persis
// dengan dashboard/ versi pertama — yang ditambahkan hanya satu lapis tema (src/neo-theme.css)
// yang dimuat paling akhir. Versi pertama tidak diubah sama sekali.
//
// Dev: http://localhost:5184/dashboard-neo/
const office = "http://127.0.0.1:8001"; // python -m edupad office-api
const web = "http://127.0.0.1:8000"; // python -m edupad serve (login Google, /api/me)

export default defineConfig({
  plugins: [react()],
  base: "/dashboard-neo/",
  // publicDir sendiri: owl di dalamnya adalah owl neo-brutalism, dengan nama berkas yang sama
  // seperti versi pertama, sehingga semua halaman lama otomatis memakai gambar yang baru.
  publicDir: "public",
  // node_modules adalah symlink ke dashboard/node_modules; cache dibedakan agar tidak bentrok.
  cacheDir: "./.vite",
  resolve: { dedupe: ["react", "react-dom", "phaser"] },
  server: {
    host: "localhost",
    port: 5184,
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
