import { useEffect, useState } from "react";
import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { checkHealth } from "./api/client";
import { NavBar } from "./components/NavBar";
import { CapturePage } from "./pages/CapturePage";
import { ConfirmPage } from "./pages/ConfirmPage";
import { DetailPage } from "./pages/DetailPage";
import { ListPage } from "./pages/ListPage";

export default function App() {
  const [health, setHealth] = useState("…");

  useEffect(() => {
    checkHealth()
      .then(setHealth)
      .catch(() => setHealth("API no disponible"));
  }, []);

  return (
    <BrowserRouter>
      <div className="app-shell">
        <p className="api-pill">API: {health}</p>
        <Routes>
          <Route path="/" element={<CapturePage />} />
          <Route path="/confirmar" element={<ConfirmPage />} />
          <Route path="/registros" element={<ListPage />} />
          <Route path="/registros/:id" element={<DetailPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
        <NavBar />
      </div>
    </BrowserRouter>
  );
}
