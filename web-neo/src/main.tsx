// Huruf disimpan di situs sendiri: CSP web EduPad (webapp.py) hanya mengizinkan font dari 'self'.
import "@fontsource-variable/space-grotesk";
import "@fontsource/archivo-black";
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
