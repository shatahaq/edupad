/** @type {import('tailwindcss').Config} */
// Warna & huruf sama dengan dashboard (dashboard/src/theme.css): lantai krem, dinding slate,
// lampu teal, owl berwarna. Pixelify Sans hanya untuk judul.
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        floor: { DEFAULT: "#f4efe6", line: "#ebe2d3" },
        paper: { DEFAULT: "#fffdf8", 2: "#faf5ec" },
        edge: { DEFAULT: "#ddd1bd", soft: "#eee6d8" },
        slate: { DEFAULT: "#2f3a46", 2: "#3d4a58", 3: "#4b5968", text: "#efe7da", muted: "#aab5c1" },
        ink: { DEFAULT: "#1e2731", 2: "#44505d", 3: "#5f6b78" },
        teal: { DEFAULT: "#2bb3ad", ink: "#1d727a" },
        owl: {
          nova: "#30b8e8",
          pixel: "#3f97ea",
          sora: "#efb81a",
          tempo: "#a77ef0",
          metric: "#2fd3a3",
          koin: "#3db368",
          nexus: "#ef5f6f",
        },
      },
      fontFamily: {
        sans: ['"Plus Jakarta Sans Variable"', "ui-sans-serif", "system-ui", "sans-serif"],
        display: ['"Pixelify Sans"', '"Plus Jakarta Sans Variable"', "ui-sans-serif", "sans-serif"],
      },
      boxShadow: {
        hard: "0 3px 0 #ddd1bd",
        "hard-dark": "0 3px 0 #1d252e",
      },
      keyframes: {
        bob: { "0%, 100%": { transform: "translateY(0)" }, "50%": { transform: "translateY(-6px)" } },
      },
      animation: { bob: "bob 3.2s ease-in-out infinite" },
    },
  },
  plugins: [],
};
