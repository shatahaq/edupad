/** @type {import('tailwindcss').Config} */
// Sistem desain "EduPad NEO" (neo-brutalism): bidang warna datar, garis tepi hitam tebal,
// bayangan blok keras, huruf tebal besar. Sengaja berbeda dari tema pixel art di web/.
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // Dasar
        paper: "#FFFDF5",
        bone: "#F3EADA",
        ink: { DEFAULT: "#111111", 2: "#3A3A3A", 3: "#5E5E5E" },
        night: "#141414",
        // Warna pop: satu warna per bagian, dipakai sebagai bidang penuh
        pop: {
          yellow: "#FFD400",
          cyan: "#35C8F3",
          purple: "#B98CFF",
          green: "#36D399",
          red: "#FF5A5F",
          blue: "#4B7BEC",
          lime: "#C8F135",
        },
        // Warna khas tiap owl (sama dengan versi pertama agar identitasnya tetap)
        owl: {
          nova: "#30B8E8",
          pixel: "#3F97EA",
          sora: "#EFB81A",
          tempo: "#A77EF0",
          metric: "#2FD3A3",
          koin: "#3DB368",
          nexus: "#EF5F6F",
        },
      },
      fontFamily: {
        sans: ['"Space Grotesk Variable"', "ui-sans-serif", "system-ui", "sans-serif"],
        display: ['"Archivo Black"', '"Space Grotesk Variable"', "ui-sans-serif", "sans-serif"],
      },
      borderWidth: { 3: "3px", 5: "5px" },
      boxShadow: {
        neo: "6px 6px 0 #111111",
        "neo-sm": "4px 4px 0 #111111",
        "neo-lg": "10px 10px 0 #111111",
        "neo-press": "2px 2px 0 #111111",
        "neo-light": "6px 6px 0 #FFFDF5",
        "neo-light-sm": "4px 4px 0 #FFFDF5",
      },
      keyframes: {
        marquee: { from: { transform: "translateX(0)" }, to: { transform: "translateX(-50%)" } },
      },
      animation: { marquee: "marquee 28s linear infinite" },
    },
  },
  plugins: [],
};
