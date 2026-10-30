import "@fontsource-variable/plus-jakarta-sans";
// Huruf disimpan di situs sendiri: CSP web EduPad (webapp.py) hanya mengizinkan font dari 'self'.
import "@fontsource/pixelify-sans/400.css";
import "@fontsource/pixelify-sans/600.css";
import "./index.css";

import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import App from "./App";

const root = document.getElementById("root");
if (!root) throw new Error("elemen #root tidak ada di index.html");

createRoot(root).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
