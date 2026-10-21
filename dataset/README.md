# Dataset Fase 0 (alimentado por el piloto HITL)

Las etiquetas **correctas** se generan con intervención humana en http://localhost:8300/ui/

## Archivos

| Archivo | Rol |
|---|---|
| `images/` | Fotos validadas (`piloto_<run>_<codigo>.jpg`) |
| `ground_truth.csv` | Etiquetas para evaluación Fase 1 |
| `feedback.jsonl` | Auditoría: OCR vs humano, confianza, notas |

## Columnas `ground_truth.csv`

`nombre_archivo, codigo_correcto, tipo, orientacion, dificultad, notas, run_id, codigo_ocr, confianza_ocr, acierto, validado_en`

- `codigo_correcto` = verdad humana (la que cuenta en Fase 1)
- `codigo_ocr` = lo que propuso el piloto
- `acierto` = `true` si coincidieron (normalizado)

## Flujo

1. Analizar imagen en el piloto.  
2. Revisar pasos 0–6.  
3. Confirmar o corregir.  
4. La fila queda lista para `scripts/evaluate_ocr.py` (Fase 1).
