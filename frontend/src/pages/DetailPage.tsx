import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { apiUrl, getRegistro, listarRegistros } from "../api/client";
import { BBoxImage } from "../components/BBoxImage";
import type { Registro } from "../types";

export function DetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const registroId = Number(id);
  const [reg, setReg] = useState<Registro | null>(null);
  const [ids, setIds] = useState<number[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!Number.isFinite(registroId)) return;
    getRegistro(registroId)
      .then(setReg)
      .catch((err) =>
        setError(err instanceof Error ? err.message : "Error al cargar"),
      );
    listarRegistros({ limit: 200 })
      .then((data) => setIds(data.items.map((i) => i.id)))
      .catch(() => undefined);
  }, [registroId]);

  if (error) {
    return (
      <section className="page-list">
        <p className="error">{error}</p>
        <Link to="/registros">Volver</Link>
      </section>
    );
  }

  if (!reg) {
    return (
      <section className="page-list">
        <p className="hint">Cargando…</p>
      </section>
    );
  }

  const pos = ids.indexOf(reg.id);
  const prevId = pos > 0 ? ids[pos - 1] : null;
  const nextId = pos >= 0 && pos < ids.length - 1 ? ids[pos + 1] : null;

  return (
    <section className="page-confirm">
      <header className="confirm-head">
        <p className="eyebrow">Registro #{reg.id}</p>
        <h1>{reg.codigo}</h1>
      </header>

      <div className="result-nav">
        <button
          type="button"
          className="btn-secondary"
          disabled={!prevId}
          onClick={() => prevId && navigate(`/registros/${prevId}`)}
        >
          ← Anterior
        </button>
        <span className="hint">
          {pos >= 0 ? `${pos + 1} / ${ids.length}` : "—"}
        </span>
        <button
          type="button"
          className="btn-secondary"
          disabled={!nextId}
          onClick={() => nextId && navigate(`/registros/${nextId}`)}
        >
          Siguiente →
        </button>
      </div>

      <BBoxImage src={apiUrl(reg.url_imagen)} alt={reg.codigo} />

      <div className="meta-chips">
        <span className="chip">{reg.tipo_deteccion}</span>
        {reg.validado_manual ? (
          <span className="chip warn">CORREGIDO</span>
        ) : (
          <span className="chip ok">OK OCR</span>
        )}
        {reg.tiempo_proceso_s != null && (
          <span className="chip muted">{reg.tiempo_proceso_s.toFixed(2)} s</span>
        )}
        {reg.confianza != null && (
          <span className="chip muted">
            {(reg.confianza * 100).toFixed(0)}%
          </span>
        )}
      </div>

      <p className="hint">
        OCR: {reg.codigo_ocr || "—"}
        {reg.fuente ? ` · ${reg.fuente}` : ""}
      </p>

      <label className="obs-label">
        Observaciones
        <textarea
          className="obs-field"
          readOnly
          rows={10}
          value={reg.observaciones || "Sin observaciones"}
        />
      </label>

      <Link to="/registros" className="btn-secondary link-btn">
        Volver al listado
      </Link>
    </section>
  );
}
