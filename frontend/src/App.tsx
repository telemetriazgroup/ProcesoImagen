import { useEffect, useState } from "react";

const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

export default function App() {
  const [health, setHealth] = useState<string>("comprobando…");

  useEffect(() => {
    fetch(`${API_URL}/api/health`)
      .then((r) => r.json())
      .then((data) => setHealth(`${data.status} · fase ${data.phase}`))
      .catch(() => setHealth("API no disponible"));
  }, []);

  return (
    <main className="page">
      <header className="brand">
        <p className="eyebrow">Telemetría · campo</p>
        <h1>ProcesoImagen</h1>
        <p className="lead">
          Reconocimiento de códigos de equipos (ZGRU / Serial No) mediante OCR.
        </p>
      </header>

      <section className="status">
        <h2>Fase 0 — Preparación</h2>
        <p>
          Scaffold listo. La captura, confirmación y listado llegan en la Fase 3.
        </p>
        <p className="pill">API: {health}</p>
      </section>
    </main>
  );
}
