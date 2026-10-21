# Fase 0.5 — Piloto con intervención humana (HITL)

**Versión:** 1.1  
**Fecha:** 24 julio 2026  
**Estado:** Activo  
**Relación:** Puente entre OCR crudo y dataset Fase 0 corregido → Fase 1.  
**Documento hermano:** `procesos_fases.md`

---

## 1. Objetivo

Interfaz para:

1. Subir una imagen de equipo.
2. **Ver todos los pasos** del procesamiento (gris, contraste, OCR, cajas…).
3. Decidir si el texto reconocido es **correcto**.
4. **Confirmar** o **corregir** con intervención humana.
5. Guardar esa verdad en el **dataset de Fase 0** (`ground_truth.csv` + imagen).
6. Medir la confianza real del OCR (acierto vs corrección) antes de Fase 1.

No exige prefijo `ZGRU`. El humano define el código correcto.

---

## 2. Flujo de trabajo

```
[Subir foto]
    → pipeline paso a paso (0…6)
    → código propuesto + confianza
    → humano confirma o corrige
    → dataset/images + ground_truth.csv + feedback.jsonl
    → métricas de acierto OCR
    → (cuando haya volumen) evaluar Fase 1 con data ya corregida
```

### Acciones humanas

| Botón | Efecto |
|---|---|
| **Confirmar propuesto** | El código OCR se acepta como correcto (`acierto=true`) |
| **Guardar corrección** | Se guarda el texto editado (`acierto=false`) |

Ambas acciones copian la imagen a `dataset/images/` y actualizan `ground_truth.csv`.

---

## 3. Interfaz

**URL principal (sin Node):** http://localhost:8300/ui/

También: frontend React en `:5273` (si Compose/Node) — misma API.

La UI muestra:

1. Métricas globales (validados, % acierto OCR, correcciones, confianza media).
2. Formulario de subida.
3. **Todos los pasos** en vertical (imágenes intermedias).
4. Panel de validación (propuesto, correcto, tipo, orientación, dificultad, notas).
5. Historial del dataset corregido.

---

## 4. API

| Método | Ruta | Uso |
|---|---|---|
| `POST` | `/api/piloto/analizar` | Sube imagen → pasos + `codigo_propuesto` |
| `POST` | `/api/piloto/validar` | Confirma/corrige → dataset Fase 0 |
| `GET` | `/api/piloto/validaciones` | Historial + métricas |
| `GET` | `/api/piloto/validaciones/{id}` | Detalle de una prueba |
| `PUT` | `/api/piloto/validaciones/{id}` | **Editar** prueba ya hecha |
| `DELETE` | `/api/piloto/validaciones/{id}` | Eliminar prueba del dataset |
| `GET` | `/api/piloto/metricas` | Solo métricas |
| `GET` | `/api/piloto/runs/{run_id}/{file}` | Imagen de un paso |
| `GET` | `/api/piloto/dataset/{file}` | Miniatura del dataset |

### Editar pruebas hechas

En `/ui/` → sección **Dataset corregido** → botón **Editar**:

- Cambia código correcto, tipo, orientación, dificultad, notas.
- Recalcula `acierto` (OCR vs humano).
- Renombra la imagen en `dataset/images/` si cambia el código.
- Sincroniza `ground_truth.csv` y `feedback.jsonl`.
- **Eliminar** quita la prueba del dataset (la imagen del análisis en `storage/piloto/` se conserva).

### Ejemplo validar

```json
{
  "run_id": "uuid-del-analisis",
  "codigo_correcto": "ZGRU12345",
  "tipo": "ZGRU",
  "orientacion": "horizontal",
  "dificultad": "normal",
  "notas": "",
  "confirmar_propuesto": true
}
```

---

## 5. Qué se escribe en Fase 0

| Destino | Contenido |
|---|---|
| `dataset/images/piloto_<id>_<codigo>.jpg` | Original del análisis |
| `dataset/ground_truth.csv` | Código correcto + OCR + acierto + metadatos |
| `dataset/feedback.jsonl` | Auditoría completa por validación |
| `storage/piloto/<run_id>/validacion.json` | Copia local del veredicto |

Columnas de `ground_truth.csv`:

`nombre_archivo, codigo_correcto, tipo, orientacion, dificultad, notas, run_id, codigo_ocr, confianza_ocr, acierto, validado_en`

Así Fase 1 puede entrenar/evaluar contra **código humano**, no contra la salida cruda del OCR.

---

## 6. Pipeline visual (pasos)

| Paso | Nombre | Para qué mirarlo |
|---|---|---|
| 0 | Original | Encuadre y nitidez |
| 1 | Gris | Pérdida de color |
| 2 | CLAHE | ¿Mejoró el contraste de la placa? |
| 3 | Denoise | ¿Se borraron bordes de caracteres? |
| 4 | Binaria | Referencia; si queda ilegible, ajustar preprocess |
| 5 | OCR + cajas | ¿La caja cae sobre el código correcto? |
| 6 | Solo números | Candidatos numéricos |

---

## 7. Arranque

```bash
cd backend
source .venv/bin/activate
export STORAGE_PATH=../storage
export DATASET_PATH=../dataset
uvicorn app.main:app --reload --host 0.0.0.0 --port 8300
```

Abrir: **http://localhost:8300/ui/**

---

## 8. Criterios de salida 0.5

- [x] UI muestra todos los pasos
- [x] Confirmación / corrección humana
- [x] Persistencia en dataset Fase 0
- [x] Métricas de acierto OCR
- [ ] ≥5 (ideal ≥25) validaciones humanas reales
- [ ] Revisión de casos `acierto=false` para ajustar preprocess
- [ ] Decisión motor OCR para Fase 1

---

## 9. Cómo mejora la confianza

1. Cada validación suma a `tasa_acierto_ocr`.
2. Las correcciones (`acierto=false`) son el material de mejora del pipeline.
3. El código **correcto humano** es la etiqueta que usará Fase 1 (`evaluate_ocr.py`).
4. No se avanza a reglas ZGRU/Serial con datos sin validar.

---

## 10. Bitácora de pruebas

| Fecha | Imagen | OCR | Humano | ¿OK? | Nota |
|---|---|---|---|---|---|
| | | | | | |

---

## 11. Archivos clave

| Ruta | Rol |
|---|---|
| `backend/app/static/piloto/` | UI servida en `/ui` |
| `frontend/src/App.tsx` | UI React equivalente |
| `backend/app/services/feedback.py` | Persistencia HITL → Fase 0 |
| `backend/app/api/piloto.py` | Endpoints |
| `dataset/ground_truth.csv` | Dataset corregido |
| `dataset/feedback.jsonl` | Log de aprendizaje |


# pasos de validacion :

cd backend
source .venv/bin/activate
export STORAGE_PATH=../storage DATASET_PATH=../dataset
uvicorn app.main:app --reload --host 0.0.0.0 --port 8300