import { FormEvent, useCallback, useEffect, useState } from "react";

const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

type Paso = {
  id: string;
  titulo: string;
  descripcion: string;
  archivo: string;
  imagen_url: string;
};

type Bloque = {
  texto: string;
  confianza: number;
  bbox: number[][];
  es_numero: boolean;
};

type Resultado = {
  run_id: string;
  motor_ocr: string;
  pasos: Paso[];
  bloques: Bloque[];
  numeros_detectados: string[];
  texto_completo: string;
  error_ocr: string | null;
  codigo_propuesto: string;
  confianza_propuesta: number;
};

type Metricas = {
  total_validados: number;
  aciertos_ocr: number;
  correcciones_humanas: number;
  tasa_acierto_ocr: number | null;
  confianza_media_ocr: number | null;
};

type Validacion = {
  id: string;
  run_id: string;
  codigo_ocr: string;
  codigo_correcto: string;
  acierto: boolean;
  tipo: string;
  orientacion: string;
  dificultad: string;
  notas: string;
  nombre_archivo: string;
  confianza_ocr: number;
  validado_en?: string;
};

export default function App() {
  const [health, setHealth] = useState("comprobando…");
  const [busy, setBusy] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [okMsg, setOkMsg] = useState<string | null>(null);
  const [resultado, setResultado] = useState<Resultado | null>(null);
  const [codigoOk, setCodigoOk] = useState("");
  const [tipo, setTipo] = useState("OTRO");
  const [orientacion, setOrientacion] = useState("n/a");
  const [dificultad, setDificultad] = useState("normal");
  const [notas, setNotas] = useState("");
  const [metricas, setMetricas] = useState<Metricas | null>(null);
  const [historial, setHistorial] = useState<Validacion[]>([]);
  const [editItem, setEditItem] = useState<Validacion | null>(null);
  const [editCodigo, setEditCodigo] = useState("");
  const [editTipo, setEditTipo] = useState("OTRO");
  const [editOrientacion, setEditOrientacion] = useState("n/a");
  const [editDificultad, setEditDificultad] = useState("normal");
  const [editNotas, setEditNotas] = useState("");
  const [editError, setEditError] = useState<string | null>(null);

  const loadFeedback = useCallback(async () => {
    const res = await fetch(`${API_URL}/api/piloto/validaciones?limit=300`);
    if (!res.ok) return;
    const data = await res.json();
    setMetricas(data.metricas);
    setHistorial(data.items ?? []);
  }, []);

  function openEdit(item: Validacion) {
    setEditItem(item);
    setEditCodigo(item.codigo_correcto || "");
    setEditTipo(item.tipo || "OTRO");
    setEditOrientacion(item.orientacion || "n/a");
    setEditDificultad(item.dificultad || "normal");
    setEditNotas(item.notas || "");
    setEditError(null);
  }

  async function saveEdit() {
    if (!editItem) return;
    if (!editCodigo.trim()) {
      setEditError("El código correcto no puede estar vacío.");
      return;
    }
    setSaving(true);
    setEditError(null);
    try {
      const res = await fetch(
        `${API_URL}/api/piloto/validaciones/${editItem.id}`,
        {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            codigo_correcto: editCodigo.trim(),
            tipo: editTipo,
            orientacion: editOrientacion,
            dificultad: editDificultad,
            notas: editNotas,
          }),
        },
      );
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail ?? `Error HTTP ${res.status}`);
      setOkMsg(data.mensaje);
      setEditItem(null);
      await loadFeedback();
    } catch (err) {
      setEditError(err instanceof Error ? err.message : "Error al editar");
    } finally {
      setSaving(false);
    }
  }

  async function deleteEdit() {
    if (!editItem) return;
    if (!confirm("¿Eliminar esta prueba del dataset Fase 0?")) return;
    setSaving(true);
    setEditError(null);
    try {
      const res = await fetch(
        `${API_URL}/api/piloto/validaciones/${editItem.id}`,
        { method: "DELETE" },
      );
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail ?? `Error HTTP ${res.status}`);
      setOkMsg(data.mensaje);
      setEditItem(null);
      await loadFeedback();
    } catch (err) {
      setEditError(err instanceof Error ? err.message : "Error al eliminar");
    } finally {
      setSaving(false);
    }
  }

  useEffect(() => {
    fetch(`${API_URL}/api/health`)
      .then((r) => r.json())
      .then((data) => setHealth(`${data.status} · fase ${data.phase}`))
      .catch(() => setHealth("API no disponible"));
    loadFeedback().catch(() => undefined);
  }, [loadFeedback]);

  async function onSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setError(null);
    setOkMsg(null);
    setResultado(null);

    const form = e.currentTarget;
    const input = form.elements.namedItem("imagen") as HTMLInputElement;
    const file = input.files?.[0];
    if (!file) {
      setError("Selecciona una imagen.");
      return;
    }

    const body = new FormData();
    body.append("file", file);
    setBusy(true);
    try {
      const res = await fetch(`${API_URL}/api/piloto/analizar`, {
        method: "POST",
        body,
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail ?? `Error HTTP ${res.status}`);
      setResultado(data as Resultado);
      setCodigoOk(data.codigo_propuesto ?? "");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al analizar");
    } finally {
      setBusy(false);
    }
  }

  async function validar(confirmarPropuesto: boolean) {
    if (!resultado) return;
    const codigo = confirmarPropuesto
      ? resultado.codigo_propuesto
      : codigoOk.trim();
    if (!codigo) {
      setError("Indica el código correcto.");
      return;
    }
    setCodigoOk(codigo);
    setSaving(true);
    setError(null);
    setOkMsg(null);
    try {
      const res = await fetch(`${API_URL}/api/piloto/validar`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          run_id: resultado.run_id,
          codigo_correcto: codigo,
          tipo,
          orientacion,
          dificultad,
          notas,
          confirmar_propuesto: confirmarPropuesto,
        }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail ?? `Error HTTP ${res.status}`);
      setOkMsg(data.mensaje);
      setMetricas(data.metricas);
      setResultado(null);
      await loadFeedback();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Error al validar");
    } finally {
      setSaving(false);
    }
  }

  const pct =
    metricas?.tasa_acierto_ocr == null
      ? "—"
      : `${Math.round(metricas.tasa_acierto_ocr * 100)}%`;

  return (
    <main className="page">
      <header className="brand">
        <p className="eyebrow">Fase 0.5 · intervención humana</p>
        <h1>ProcesoImagen</h1>
        <p className="lead">
          Revisa todos los pasos, confirma o corrige el texto reconocido y
          alimenta el dataset de Fase 0 con datos validados.
        </p>
        <p className="pill">API: {health}</p>
      </header>

      <section className="metrics">
        <h2>Confianza del sistema</h2>
        <div className="metric-grid">
          <div>
            <span>{metricas?.total_validados ?? 0}</span>
            <label>Validados</label>
          </div>
          <div>
            <span>{pct}</span>
            <label>Acierto OCR</label>
          </div>
          <div>
            <span>{metricas?.correcciones_humanas ?? 0}</span>
            <label>Correcciones</label>
          </div>
          <div>
            <span>
              {metricas?.confianza_media_ocr == null
                ? "—"
                : metricas.confianza_media_ocr.toFixed(2)}
            </span>
            <label>Confianza media</label>
          </div>
        </div>
      </section>

      <form className="upload" onSubmit={onSubmit}>
        <label className="file-label">
          <span>1. Sube o captura una imagen</span>
          <input
            name="imagen"
            type="file"
            accept="image/jpeg,image/png,image/webp,image/*"
            capture="environment"
          />
        </label>
        <button type="submit" disabled={busy}>
          {busy ? "Analizando…" : "Analizar paso a paso"}
        </button>
      </form>

      {error && <p className="error">{error}</p>}
      {okMsg && <p className="ok">{okMsg}</p>}

      {resultado && (
        <section className="workspace">
          <div className="steps-all">
            {resultado.pasos.map((paso) => (
              <article key={paso.id} className="step-card">
                <h3>
                  {paso.id} — {paso.titulo}
                </h3>
                <p>{paso.descripcion}</p>
                <img src={`${API_URL}${paso.imagen_url}`} alt={paso.titulo} />
              </article>
            ))}
          </div>

          <aside className="validate-panel">
            <h2>2. Validar reconocimiento</h2>
            <p className="hint">
              Si el propuesto no es el código del equipo, corrígelo. Al guardar
              entra al dataset Fase 0 (`ground_truth.csv`).
            </p>

            <label>
              Código propuesto (OCR)
              <input
                value={resultado.codigo_propuesto || ""}
                readOnly
              />
            </label>
            <p className="conf-line">
              Confianza OCR:{" "}
              <strong>{resultado.confianza_propuesta?.toFixed(2) ?? "—"}</strong>
            </p>

            <label>
              Código correcto (humano)
              <input
                value={codigoOk}
                onChange={(e) => setCodigoOk(e.target.value)}
                placeholder="Escribe o confirma el código"
              />
            </label>

            <div className="row">
              <label>
                Tipo
                <select value={tipo} onChange={(e) => setTipo(e.target.value)}>
                  <option value="OTRO">OTRO</option>
                  <option value="ZGRU">ZGRU</option>
                  <option value="SERIAL">SERIAL</option>
                  <option value="MANUAL">MANUAL</option>
                </select>
              </label>
              <label>
                Orientación
                <select
                  value={orientacion}
                  onChange={(e) => setOrientacion(e.target.value)}
                >
                  <option value="n/a">n/a</option>
                  <option value="horizontal">horizontal</option>
                  <option value="vertical">vertical</option>
                </select>
              </label>
              <label>
                Dificultad
                <select
                  value={dificultad}
                  onChange={(e) => setDificultad(e.target.value)}
                >
                  <option value="normal">normal</option>
                  <option value="dificil">dificil</option>
                </select>
              </label>
            </div>

            <label>
              Notas
              <textarea
                rows={2}
                value={notas}
                onChange={(e) => setNotas(e.target.value)}
                placeholder="Reflejo, ángulo, confusión O/0…"
              />
            </label>

            <div className="actions">
              <button
                type="button"
                className="primary"
                disabled={saving}
                onClick={() => validar(true)}
              >
                Confirmar propuesto
              </button>
              <button
                type="button"
                className="secondary"
                disabled={saving}
                onClick={() => validar(false)}
              >
                Guardar corrección
              </button>
            </div>

            <ul className="blocks">
              {resultado.bloques.map((b, i) => (
                <li key={`${b.texto}-${i}`} className={b.es_numero ? "num" : ""}>
                  <span>{b.es_numero ? "NUM" : "TXT"}</span> {b.texto}{" "}
                  <em>({b.confianza.toFixed(2)})</em>
                </li>
              ))}
            </ul>
          </aside>
        </section>
      )}

      <section className="history">
        <h2>3. Dataset corregido (Fase 0)</h2>
        <p className="hint">
          Usa <strong>Editar</strong> para corregir pruebas ya hechas. Dataset:{" "}
          <code>ground_truth.csv</code>.
        </p>
        <div className="history-list">
          {!historial.length && (
            <p className="hint">Aún no hay validaciones.</p>
          )}
          {historial.map((item) => (
            <article key={item.id} className="hist-item">
              <img
                src={`${API_URL}/api/piloto/dataset/${encodeURIComponent(item.nombre_archivo)}`}
                alt=""
              />
              <div>
                <strong>{item.codigo_correcto}</strong>
                <div className="hint">
                  OCR: {item.codigo_ocr || "—"} · {item.tipo} · {item.dificultad}
                </div>
              </div>
              <div className="hist-actions">
                <span className={`badge ${item.acierto ? "ok" : "bad"}`}>
                  {item.acierto ? "OK OCR" : "CORREGIDO"}
                </span>
                <button
                  type="button"
                  className="secondary"
                  onClick={() => openEdit(item)}
                >
                  Editar
                </button>
              </div>
            </article>
          ))}
        </div>
      </section>

      {editItem && (
        <div className="modal-backdrop">
          <div className="edit-form">
            <h2>Editar prueba</h2>
            <p className="hint">
              run {editItem.run_id.slice(0, 8)} · {editItem.validado_en || ""}
            </p>
            <img
              src={`${API_URL}/api/piloto/dataset/${encodeURIComponent(editItem.nombre_archivo)}`}
              alt=""
            />
            <label>
              Código OCR
              <input value={editItem.codigo_ocr || ""} readOnly />
            </label>
            <label>
              Código correcto
              <input
                value={editCodigo}
                onChange={(e) => setEditCodigo(e.target.value)}
              />
            </label>
            <div className="row">
              <label>
                Tipo
                <select
                  value={editTipo}
                  onChange={(e) => setEditTipo(e.target.value)}
                >
                  <option value="OTRO">OTRO</option>
                  <option value="ZGRU">ZGRU</option>
                  <option value="SERIAL">SERIAL</option>
                  <option value="MANUAL">MANUAL</option>
                </select>
              </label>
              <label>
                Orientación
                <select
                  value={editOrientacion}
                  onChange={(e) => setEditOrientacion(e.target.value)}
                >
                  <option value="n/a">n/a</option>
                  <option value="horizontal">horizontal</option>
                  <option value="vertical">vertical</option>
                </select>
              </label>
              <label>
                Dificultad
                <select
                  value={editDificultad}
                  onChange={(e) => setEditDificultad(e.target.value)}
                >
                  <option value="normal">normal</option>
                  <option value="dificil">dificil</option>
                </select>
              </label>
            </div>
            <label>
              Notas
              <textarea
                rows={2}
                value={editNotas}
                onChange={(e) => setEditNotas(e.target.value)}
              />
            </label>
            {editError && <p className="error">{editError}</p>}
            <div className="actions edit-actions">
              <button
                type="button"
                className="primary"
                disabled={saving}
                onClick={saveEdit}
              >
                Guardar cambios
              </button>
              <button
                type="button"
                className="secondary"
                onClick={() => setEditItem(null)}
              >
                Cancelar
              </button>
              <button
                type="button"
                className="danger"
                disabled={saving}
                onClick={deleteEdit}
              >
                Eliminar
              </button>
            </div>
          </div>
        </div>
      )}
    </main>
  );
}
