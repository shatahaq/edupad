import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  publicDir: "../frontend/public",
  server: {
    host: "127.0.0.1",
    port: 5173,
    fs: { allow: [".."] },
    proxy: {
      "/api": { target: "http://127.0.0.1:8001", changeOrigin: true },
      "/v1/dashboard": { target: "http://127.0.0.1:8001", changeOrigin: true },
    },
  },
});
