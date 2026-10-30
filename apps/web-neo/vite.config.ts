import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

// Web EduPad versi kedua (tema neo-brutalism). Versi pertama (pixel art) tetap di web/ dan
// tidak diubah; keduanya memakai isi teks yang sama dari web/src/landing/copy.ts.
//
// `npm run dev`: /api dan /auth diteruskan ke `python -m edupad serve`, sama seperti web/,
// sehingga login Google bisa diuji dari sini. Port dibedakan agar bisa jalan berdampingan.
const backend = "http://127.0.0.1:8000";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5180,
    strictPort: true,
    // Isi teks & klip suara dibaca dari folder web/ versi pertama.
    fs: { allow: [".."] },
    proxy: { "/api": backend, "/auth": backend },
  },
  build: {
    outDir: "dist",
    sourcemap: false,
    // Font tidak disisipkan sebagai data: URI; CSP web EduPad hanya mengizinkan font dari 'self'.
    assetsInlineLimit: (file) => (/\.woff2?$/.test(file) ? false : undefined),
  },
});
