# Fase 1 — Núcleo OCR y motor de reglas

**Estado:** Gate cumplido — **86.9%** (113/130) · 25 julio 2026  
**Baseline iter 4:** 78.4% (antes de ampliar/limpiar dataset)

## Reglas de dominio (algoritmo actual)

1. **SERIAL (horizontal)**  
   Al detectar `Serial` / `Serial No` / `Serial number`:
   - el código está a la **derecha**, en la misma línea (o columna derecha cercana);
   - se recorta esa banda, se **amplía** y se vuelve a hacer OCR;
   - se aceptan códigos **cortos** (4–6 dígitos) y prefijos `E0` / `CIM` / `MMAU` / `MNBU`;
   - se rechazan fechas (`06/2024`), refrigerantes (`R134A`) y modelos `SC…` cuando hay un serial numérico corto.

2. **ZGRU**  
   Si aparece el prefijo `ZGRU`, se buscan los **7 dígitos** (columna debajo / línea vertical).  
   Si ya hay un `ZGRU+7` limpio del OCR global, el ROI de columna **no lo pisa**.

3. **OTRO / vertical (≡ ZGRU sin prefijo)**  
   Seguir la **línea vertical**, ampliar, agrupar exactamente **7 dígitos**.  
   Fallback: rotación 90°/270° + crops de borde del contenedor.

## Módulos

| Archivo | Rol |
|---|---|
| `backend/app/core/preprocess.py` | CLAHE, variantes, strips laterales |
| `backend/app/core/ocr.py` | RapidOCR (ONNX) |
| `backend/app/core/rules.py` | Extracción Serial / ZGRU / 7 dígitos |
| `backend/app/core/roi.py` | Recortes geométricos (derecha de Serial, columna ZGRU/7) |
| `backend/app/core/pipeline.py` | Orquestación multipaso (`detect_code`) |
| `scripts/evaluate_ocr.py` | Eval vs `dataset/ground_truth.csv` |
| `POST /api/ocr` | API del pipeline |

## Evaluación

```bash
cd backend && source .venv/bin/activate
export STORAGE_PATH=../storage DATASET_PATH=../dataset
python ../scripts/evaluate_ocr.py
# → docs/reportes/eval_fase1_latest.md
```

| Iteración | Global | OTRO | SERIAL | ZGRU | Vertical | Horizontal | t medio |
|---|---|---|---|---|---|---|---|
| 1 | 56.8% | 34% | 74% | 62% | 39% | 72% | 1.5s |
| 2 | 64.0% | 50% | 74% | ~70% | 55% | 70% | 1.0s |
| 3 | 70.3% | 65.9% | 70.4% | 84.6% | 68.6% | 71.7% | ~5.7s |
| **4** | **78.4%** | **72.7%** | **88.9%** | **53.8%*** | **64.7%** | **90.0%** | ~7.3s |

\*ZGRU baja en iter 4 por ROI de columna que a veces pisa lecturas buenas; el código ya evita pisar `ZGRU+7` confiable — re-evaluar tras limpiar GT.

Gate ≥ 85% **aún no**. Mejoras claras en **SERIAL corto** y **horizontal**.

Reporte: `docs/reportes/eval_fase1_latest.md`

## Próximo ciclo (dataset)

Tras guardar este algoritmo:

1. Añadir más imágenes al dataset (HITL `/ui/`).
2. Corregir verdades erróneas en `ground_truth.csv`.
3. Eliminar imágenes que no corresponden.
4. Volver a correr `evaluate_ocr.py` y comparar contra esta baseline **78.4%**.

## API

```bash
curl -F "file=@foto.jpg" http://localhost:8000/api/ocr
```
