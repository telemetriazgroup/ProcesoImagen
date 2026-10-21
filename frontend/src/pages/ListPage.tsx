import { useCallback, useEffect, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { apiUrl, listarRegistros } from "../api/client";
import type { Registro } from "../types";

export function ListPage() {
  const location = useLocation();
  const navigate = useNavigate();
  const justSaved = (location.state as { justSaved?: string } | null)?.justSaved;

  const [items, setItems] = useState<Registro[]>([]);
  const [total, setTotal] = useState(0);
  const [codigo, setCodigo] = useState("");
  const [tipo, setTipo] = useState("");
  const [manual, setManual] = useState<"" | "true" | "false">("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await listarRegistros({
        codigo: codigo.trim() || undefined,
        tipo: tipo || undefined,
        validado_manual:
          manual === "true" ? true : manual === "false" ? false : "",
        limit: 50,
      });
      setItems(data.items);
      setTotal(data.total);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al listar");
    } finally {
      setLoading(false);
    }
  }, [codigo, tipo, manual]);

  useEffect(() => {
    const t = setTimeout(() => {
      load().catch(() => undefined);
    }, 200);
    return () => clearTimeout(t);
  }, [load]);

  return (
    <section className="page-list">
      <header className="brand compact">
        <p className="eyebrow">Registros</p>
        <h1>Equipos guardados</h1>
        {justSaved && (
          <p className="ok">
            Guardado: <strong>{justSaved}</strong>
          </p>
        )}
      </header>

      <div className="filters">
        <label>
          Buscar código
          <input
            value={codigo}
            onChange={(e) => setCodigo(e.target.value)}
            placeholder="CIM… / ZGRU…"
          />
        </label>
        <div className="filter-row">
          <label>
            Tipo
            <select value={tipo} onChange={(e) => setTipo(e.target.value)}>
              <option value="">Todos</option>
              <option value="SERIAL">SERIAL</option>
              <option value="ZGRU">ZGRU</option>
              <option value="OTRO">OTRO</option>
              <option value="MANUAL">MANUAL</option>
            </select>
          </label>
          <label>
            Corrección
            <select
              value={manual}
              onChange={(e) =>
                setManual(e.target.value as "" | "true" | "false")
              }
            >
              <option value="">Todas</option>
              <option value="true">Solo corregidas</option>
              <option value="false">Sin corrección</option>
            </select>
          </label>
        </div>
      </div>

      <p className="hint">{loading ? "Cargando…" : `${total} registro(s)`}</p>
      {error && <p className="error">{error}</p>}

      <div className="reg-list">
        {!loading && !items.length && (
          <p className="hint">
            Aún no hay registros. <Link to="/">Captura el primero</Link>.
          </p>
        )}
        {items.map((item) => (
          <article
            key={item.id}
            className="reg-item clickable"
            onClick={() => navigate(`/registros/${item.id}`)}
            onKeyDown={(e) => {
              if (e.key === "Enter") navigate(`/registros/${item.id}`);
            }}
            role="button"
            tabIndex={0}
          >
            <img
              src={apiUrl(item.url_thumb || item.url_imagen)}
              alt=""
              loading="lazy"
            />
            <div className="reg-body">
              <strong>{item.codigo}</strong>
              <div className="hint">
                {item.tipo_deteccion}
                {item.tiempo_proceso_s != null
                  ? ` · ${item.tiempo_proceso_s.toFixed(1)} s`
                  : ""}
              </div>
              <div className="hint obs-preview">
                {(item.observaciones || "").split("\n").slice(-1)[0] ||
                  new Date(item.creado_en).toLocaleString("es")}
              </div>
            </div>
            {item.validado_manual ? (
              <span className="badge bad">CORREGIDO</span>
            ) : (
              <span className="badge ok">OK OCR</span>
            )}
          </article>
        ))}
      </div>

      <Link to="/" className="btn-hero fab-new">
        Nuevo registro
      </Link>
    </section>
  );
}
