const API = "";

let current = null;
let editingId = null;
let historyCache = [];

const el = (id) => document.getElementById(id);

async function refreshHealth() {
  try {
    const r = await fetch(`${API}/api/health`);
    const d = await r.json();
    el("health").textContent = `API: ${d.status} · fase ${d.phase}`;
  } catch {
    el("health").textContent = "API: no disponible";
  }
}

function renderMetrics(m) {
  el("m-total").textContent = m.total_validados ?? 0;
  el("m-acierto").textContent =
    m.tasa_acierto_ocr == null ? "—" : `${Math.round(m.tasa_acierto_ocr * 100)}%`;
  el("m-corr").textContent = m.correcciones_humanas ?? 0;
  el("m-conf").textContent =
    m.confianza_media_ocr == null ? "—" : m.confianza_media_ocr.toFixed(2);
}

function openEdit(item) {
  editingId = item.id;
  el("edit-error").hidden = true;
  el("edit-meta").textContent = `run ${String(item.run_id || "").slice(0, 8)} · ${item.validado_en || ""}`;
  el("edit-preview").src = `${API}/api/piloto/dataset/${encodeURIComponent(item.nombre_archivo)}?t=${Date.now()}`;
  el("edit-codigo-ocr").value = item.codigo_ocr || "";
  el("edit-codigo-ok").value = item.codigo_correcto || "";
  el("edit-tipo").value = item.tipo || "OTRO";
  el("edit-orientacion").value = item.orientacion || "n/a";
  el("edit-dificultad").value = item.dificultad || "normal";
  el("edit-notas").value = item.notas || "";
  el("edit-dialog").showModal();
}

function closeEdit() {
  editingId = null;
  el("edit-dialog").close();
}

async function refreshHistory() {
  const r = await fetch(`${API}/api/piloto/validaciones?limit=300`);
  const d = await r.json();
  renderMetrics(d.metricas || {});
  historyCache = d.items || [];
  const list = el("history-list");
  list.innerHTML = "";
  if (!historyCache.length) {
    list.innerHTML = `<p class="hint">Aún no hay validaciones. Analiza una imagen y confirma/corrige el código.</p>`;
    return;
  }
  for (const item of historyCache) {
    const card = document.createElement("article");
    card.className = "hist-item";
    const badge = item.acierto ? "OK OCR" : "CORREGIDO";
    card.innerHTML = `
      <img src="${API}/api/piloto/dataset/${encodeURIComponent(item.nombre_archivo)}" alt="" />
      <div>
        <strong>${item.codigo_correcto}</strong>
        <div class="hint">OCR: ${item.codigo_ocr || "—"} · ${item.tipo} · ${item.dificultad}</div>
      </div>
      <div class="hist-actions">
        <span class="badge ${item.acierto ? "ok" : "bad"}">${badge}</span>
        <button type="button" class="btn-edit secondary" data-id="${item.id}">Editar</button>
      </div>
    `;
    card.querySelector(".btn-edit").addEventListener("click", () => openEdit(item));
    list.appendChild(card);
  }
}

function renderSteps(resultado) {
  const box = el("steps");
  box.innerHTML = "";
  for (const paso of resultado.pasos) {
    const card = document.createElement("article");
    card.className = "step-card";
    card.innerHTML = `
      <h3>${paso.id} — ${paso.titulo}</h3>
      <p>${paso.descripcion}</p>
      <img src="${API}${paso.imagen_url}" alt="${paso.titulo}" loading="lazy" />
    `;
    box.appendChild(card);
  }
}

function renderBlocks(resultado) {
  const box = el("blocks");
  if (!resultado.bloques?.length) {
    box.innerHTML = `<p class="hint">Sin bloques OCR.</p>`;
    return;
  }
  box.innerHTML = resultado.bloques
    .map(
      (b) =>
        `<div class="${b.es_numero ? "num" : ""}"><strong>${b.es_numero ? "NUM" : "TXT"}</strong> ${b.texto} <em>(${Number(b.confianza).toFixed(2)})</em></div>`,
    )
    .join("");
}

function showResult(resultado) {
  current = resultado;
  el("workspace").hidden = false;
  renderSteps(resultado);
  renderBlocks(resultado);
  el("codigo-ocr").value = resultado.codigo_propuesto || "";
  el("codigo-ok").value = resultado.codigo_propuesto || "";
  el("conf-ocr").textContent =
    resultado.confianza_propuesta != null
      ? Number(resultado.confianza_propuesta).toFixed(2)
      : "—";
  el("save-msg").hidden = true;
}

async function analyze(ev) {
  ev.preventDefault();
  el("error").hidden = true;
  const file = el("file").files?.[0];
  if (!file) return;
  const btn = el("btn-analyze");
  btn.disabled = true;
  btn.textContent = "Analizando…";
  try {
    const body = new FormData();
    body.append("file", file);
    const r = await fetch(`${API}/api/piloto/analizar`, { method: "POST", body });
    const d = await r.json();
    if (!r.ok) throw new Error(d.detail || `HTTP ${r.status}`);
    showResult(d);
  } catch (err) {
    el("error").hidden = false;
    el("error").textContent = err.message || "Error al analizar";
  } finally {
    btn.disabled = false;
    btn.textContent = "Analizar paso a paso";
  }
}

async function saveValidation({ confirmProposed }) {
  if (!current) return;
  el("error").hidden = true;
  el("save-msg").hidden = true;
  const codigo = confirmProposed
    ? el("codigo-ocr").value.trim()
    : el("codigo-ok").value.trim();
  if (!codigo) {
    el("error").hidden = false;
    el("error").textContent = "Indica el código correcto.";
    return;
  }
  el("codigo-ok").value = codigo;
  try {
    const r = await fetch(`${API}/api/piloto/validar`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        run_id: current.run_id,
        codigo_correcto: codigo,
        tipo: el("tipo").value,
        orientacion: el("orientacion").value,
        dificultad: el("dificultad").value,
        notas: el("notas").value,
        confirmar_propuesto: confirmProposed,
      }),
    });
    const d = await r.json();
    if (!r.ok) throw new Error(d.detail || `HTTP ${r.status}`);
    el("save-msg").hidden = false;
    el("save-msg").textContent = d.mensaje;
    if (d.metricas) renderMetrics(d.metricas);
    await refreshHistory();
    current = null;
  } catch (err) {
    el("error").hidden = false;
    el("error").textContent = err.message || "Error al validar";
  }
}

async function saveEdit(ev) {
  ev.preventDefault();
  if (!editingId) return;
  el("edit-error").hidden = true;
  const codigo = el("edit-codigo-ok").value.trim();
  if (!codigo) {
    el("edit-error").hidden = false;
    el("edit-error").textContent = "El código correcto no puede estar vacío.";
    return;
  }
  const btn = el("btn-edit-save");
  btn.disabled = true;
  try {
    const r = await fetch(`${API}/api/piloto/validaciones/${editingId}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        codigo_correcto: codigo,
        tipo: el("edit-tipo").value,
        orientacion: el("edit-orientacion").value,
        dificultad: el("edit-dificultad").value,
        notas: el("edit-notas").value,
      }),
    });
    const d = await r.json();
    if (!r.ok) throw new Error(d.detail || `HTTP ${r.status}`);
    closeEdit();
    el("save-msg").hidden = false;
    el("save-msg").textContent = d.mensaje;
    await refreshHistory();
  } catch (err) {
    el("edit-error").hidden = false;
    el("edit-error").textContent = err.message || "Error al editar";
  } finally {
    btn.disabled = false;
  }
}

async function deleteEdit() {
  if (!editingId) return;
  if (!confirm("¿Eliminar esta prueba del dataset Fase 0?")) return;
  el("edit-error").hidden = true;
  try {
    const r = await fetch(`${API}/api/piloto/validaciones/${editingId}`, {
      method: "DELETE",
    });
    const d = await r.json();
    if (!r.ok) throw new Error(d.detail || `HTTP ${r.status}`);
    closeEdit();
    el("save-msg").hidden = false;
    el("save-msg").textContent = d.mensaje;
    await refreshHistory();
  } catch (err) {
    el("edit-error").hidden = false;
    el("edit-error").textContent = err.message || "Error al eliminar";
  }
}

el("upload-form").addEventListener("submit", analyze);
el("btn-confirm").addEventListener("click", () => saveValidation({ confirmProposed: true }));
el("btn-save").addEventListener("click", () => saveValidation({ confirmProposed: false }));
el("edit-form").addEventListener("submit", saveEdit);
el("btn-edit-cancel").addEventListener("click", closeEdit);
el("btn-edit-delete").addEventListener("click", deleteEdit);

refreshHealth();
refreshHistory();
