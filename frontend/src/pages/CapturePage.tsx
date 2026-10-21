import { useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { uploadImagen } from "../api/client";
import { COLA_INDEX_KEY, COLA_KEY, ImagenPropuesta } from "../types";

export function CapturePage() {
  const navigate = useNavigate();
  const cameraRef = useRef<HTMLInputElement>(null);
  const galleryRef = useRef<HTMLInputElement>(null);
  const multiRef = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
  const [progress, setProgress] = useState<{ done: number; total: number } | null>(
    null,
  );
  const [error, setError] = useState<string | null>(null);

  async function processFiles(files: FileList | File[] | null) {
    const list = files ? Array.from(files) : [];
    if (!list.length) return;
    setBusy(true);
    setError(null);
    setProgress({ done: 0, total: list.length });
    const cola: ImagenPropuesta[] = [];
    const fallos: string[] = [];
    try {
      for (let i = 0; i < list.length; i++) {
        const file = list[i];
        setProgress({ done: i, total: list.length });
        try {
          const propuesta = await uploadImagen(file);
          cola.push(propuesta);
        } catch (err) {
          fallos.push(
            `${file.name}: ${err instanceof Error ? err.message : "error"}`,
          );
        }
        setProgress({ done: i + 1, total: list.length });
      }
      if (!cola.length) {
        setError(fallos.join(" · ") || "No se pudo procesar ninguna imagen.");
        return;
      }
      sessionStorage.setItem(COLA_KEY, JSON.stringify(cola));
      sessionStorage.setItem(COLA_INDEX_KEY, "0");
      if (fallos.length) {
        sessionStorage.setItem("procesoimagen_fallos", fallos.join("\n"));
      } else {
        sessionStorage.removeItem("procesoimagen_fallos");
      }
      navigate("/confirmar");
    } finally {
      setBusy(false);
      setProgress(null);
      if (cameraRef.current) cameraRef.current.value = "";
      if (galleryRef.current) galleryRef.current.value = "";
      if (multiRef.current) multiRef.current.value = "";
    }
  }

  return (
    <section className="page-capture">
      <header className="brand">
        <p className="eyebrow">Campo · registrar equipo</p>
        <h1>ProcesoImagen</h1>
        <p className="lead">
          Una o varias fotos. Verás imagen, tiempo y pasos del OCR en
          observaciones antes de confirmar.
        </p>
      </header>

      {busy ? (
        <div className="processing" role="status" aria-live="polite">
          <div className="spinner" />
          <p>
            Procesando{" "}
            {progress
              ? `${progress.done}/${progress.total}`
              : "imagen…"}
          </p>
          <p className="hint">Puede tardar varios segundos por foto.</p>
        </div>
      ) : (
        <div className="capture-actions">
          <button
            type="button"
            className="btn-hero"
            onClick={() => cameraRef.current?.click()}
          >
            Tomar foto
          </button>
          <button
            type="button"
            className="btn-secondary"
            onClick={() => galleryRef.current?.click()}
          >
            Elegir de galería
          </button>
          <button
            type="button"
            className="btn-secondary"
            onClick={() => multiRef.current?.click()}
          >
            Varias imágenes
          </button>
        </div>
      )}

      <input
        ref={cameraRef}
        type="file"
        accept="image/*"
        capture="environment"
        className="sr-only"
        onChange={(e) => processFiles(e.target.files)}
      />
      <input
        ref={galleryRef}
        type="file"
        accept="image/jpeg,image/png,image/webp,image/heic,image/*"
        className="sr-only"
        onChange={(e) => processFiles(e.target.files)}
      />
      <input
        ref={multiRef}
        type="file"
        accept="image/jpeg,image/png,image/webp,image/heic,image/*"
        multiple
        className="sr-only"
        onChange={(e) => processFiles(e.target.files)}
      />

      {error && <p className="error">{error}</p>}
    </section>
  );
}
