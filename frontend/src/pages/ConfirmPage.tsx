import { FormEvent, useCallback, useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { apiUrl, crearRegistro } from "../api/client";
import { BBoxImage } from "../components/BBoxImage";
import {
  COLA_INDEX_KEY,
  COLA_KEY,
  CONF_THRESHOLD,
  ImagenPropuesta,
} from "../types";

function loadCola(): ImagenPropuesta[] {
  try {
    const raw = sessionStorage.getItem(COLA_KEY);
    if (!raw) return [];
    return JSON.parse(raw) as ImagenPropuesta[];
  } catch {
    return [];
  }
}

function initialCodigo(p: ImagenPropuesta): string {
  if (p.sin_deteccion) return "";
  if (p.confianza != null && p.confianza < CONF_THRESHOLD) return "";
  return p.codigo_propuesto ?? "";
}

export function ConfirmPage() {
  const navigate = useNavigate();
  const [cola, setCola] = useState<ImagenPropuesta[]>(() => loadCola());
  const [idx, setIdx] = useState(() => {
    const n = Number(sessionStorage.getItem(COLA_INDEX_KEY) || "0");
    return Number.isFinite(n) ? n : 0;
  });
  const propuesta = cola[idx] ?? null;
  const [codigo, setCodigo] = useState(() =>
    propuesta ? initialCodigo(propuesta) : "",
  );
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fallosBatch] = useState(
    () => sessionStorage.getItem("procesoimagen_fallos") || "",
  );

  useEffect(() => {
    if (!propuesta) return;
    setCodigo(initialCodigo(propuesta));
    setError(null);
    sessionStorage.setItem(COLA_INDEX_KEY, String(idx));
  }, [idx, propuesta]);

  const go = useCallback(
    (next: number) => {
      if (next < 0 || next >= cola.length) return;
      setIdx(next);
    },
    [cola.length],
  );

  if (!propuesta || !cola.length) {
    return (
      <section className="page-confirm empty">
        <p className="lead">No hay imágenes pendientes de confirmar.</p>
        <Link className="btn-hero" to="/">
          Ir a captura
        </Link>
      </section>
    );
  }

  const lowConf =
    propuesta.sin_deteccion ||
    propuesta.confianza == null ||
    propuesta.confianza < CONF_THRESHOLD;

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    const value = codigo.trim().toUpperCase();
    if (!value) {
      setError("Escribe el código del equipo.");
      return;
    }
    setSaving(true);
    setError(null);
    try {
      await crearRegistro({
        imagen_id: propuesta.imagen_id,
        codigo: value,
        tipo: propuesta.sin_deteccion ? "MANUAL" : undefined,
      });
      const rest = cola.filter((_, i) => i !== idx);
      if (!rest.length) {
        sessionStorage.removeItem(COLA_KEY);
        sessionStorage.removeItem(COLA_INDEX_KEY);
        navigate("/registros", { replace: true, state: { justSaved: value } });
        return;
      }
      const nextIdx = Math.min(idx, rest.length - 1);
      setCola(rest);
      sessionStorage.setItem(COLA_KEY, JSON.stringify(rest));
      setIdx(nextIdx);
      sessionStorage.setItem(COLA_INDEX_KEY, String(nextIdx));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al guardar");
    } finally {
      setSaving(false);
    }
  }

  function skip() {
    const rest = cola.filter((_, i) => i !== idx);
    if (!rest.length) {
      sessionStorage.removeItem(COLA_KEY);
      sessionStorage.removeItem(COLA_INDEX_KEY);
      navigate("/registros");
      return;
    }
    const nextIdx = Math.min(idx, rest.length - 1);
    setCola(rest);
    sessionStorage.setItem(COLA_KEY, JSON.stringify(rest));
    setIdx(nextIdx);
  }

  return (
    <section className="page-confirm">
      <header className="confirm-head">
        <p className="eyebrow">
          Resultado {idx + 1} / {cola.length}
          {propuesta.nombre_archivo ? ` · ${propuesta.nombre_archivo}` : ""}
        </p>
        <h1>¿Es correcto?</h1>
      </header>

      {cola.length > 1 && (
        <div className="result-nav">
          <button
            type="button"
            className="btn-secondary"
            disabled={idx <= 0}
            onClick={() => go(idx - 1)}
          >
            ← Anterior
          </button>
          <span className="hint">
            {idx + 1} de {cola.length}
          </span>
          <button
            type="button"
            className="btn-secondary"
            disabled={idx >= cola.length - 1}
            onClick={() => go(idx + 1)}
          >
            Siguiente →
          </button>
        </div>
      )}

      {fallosBatch && (
        <p className="error hint-block">Algunas fallaron: {fallosBatch}</p>
      )}

      <BBoxImage
        src={apiUrl(propuesta.url_imagen)}
        bbox={propuesta.bbox}
        alt="Placa del equipo"
      />

      <div className="meta-chips">
        <span className="chip">{propuesta.tipo || "MANUAL"}</span>
        <span className={`chip ${lowConf ? "warn" : "ok"}`}>
          {propuesta.sin_deteccion
            ? "Sin detección"
            : `Confianza ${((propuesta.confianza ?? 0) * 100).toFixed(0)}%`}
        </span>
        {propuesta.tiempo_proceso_s != null && (
          <span className="chip muted">
            {propuesta.tiempo_proceso_s.toFixed(2)} s
          </span>
        )}
        {propuesta.orientacion && (
          <span className="chip muted">{propuesta.orientacion}</span>
        )}
      </div>

      <label className="obs-label">
        Observaciones (pasos del OCR)
        <textarea
          className="obs-field"
          readOnly
          rows={8}
          value={propuesta.observaciones || (propuesta.pasos || []).join("\n")}
        />
      </label>

      <p className="hint">{propuesta.mensaje}</p>

      <form className="confirm-form" onSubmit={onSubmit}>
        <label>
          Código del equipo
          <input
            value={codigo}
            onChange={(e) => setCodigo(e.target.value.toUpperCase())}
            placeholder={lowConf ? "Escribe el código" : "Confirma o corrige"}
            autoCapitalize="characters"
            autoCorrect="off"
            spellCheck={false}
            inputMode="text"
            autoFocus={lowConf}
          />
        </label>

        {error && <p className="error">{error}</p>}

        <div className="confirm-actions">
          <button type="submit" className="btn-hero" disabled={saving}>
            {saving
              ? "Guardando…"
              : cola.length > 1
                ? "Confirmar y siguiente"
                : "Confirmar"}
          </button>
          {cola.length > 1 && (
            <button type="button" className="btn-secondary" onClick={skip}>
              Omitir esta
            </button>
          )}
          <Link to="/" className="btn-secondary link-btn">
            Nueva captura
          </Link>
        </div>
      </form>
    </section>
  );
}
