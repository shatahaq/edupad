import { useEffect } from "react";

import { navigate, usePathname } from "./lib/router";
import Dashboard from "./pages/Dashboard";
import Landing from "./pages/Landing";

export default function App() {
  const pathname = usePathname();

  useEffect(() => {
    // Alamat yang tidak dikenal kembali ke halaman depan.
    if (pathname !== "/" && pathname !== "/dashboard") navigate("/", { replace: true });
  }, [pathname]);

  return pathname === "/dashboard" ? <Dashboard /> : <Landing />;
}
