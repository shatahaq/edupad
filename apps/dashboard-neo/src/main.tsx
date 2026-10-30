import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import { App } from "./App";
// Urutan penting: tiga berkas pertama milik dashboard versi pertama (struktur & tata letak),
// neo-theme.css dimuat paling akhir dan hanya menimpa rupa (warna, tepi, bayangan, huruf).
import "../../dashboard/src/styles.css";
import "../../dashboard/src/readability.css";
import "../../dashboard/src/theme.css";
import "./neo-theme.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
