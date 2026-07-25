# ProcesoImagen

OCR de códigos de equipos con validación humana (Fase 0.5) y motor de reglas (Fase 1).

- Requisitos: [`contexto.md`](contexto.md)
- Ciclo: [`procesos_fases.md`](procesos_fases.md)
- Piloto HITL: [`previo.md`](previo.md)
- Fase 1: [`docs/fase1.md`](docs/fase1.md)

## Estado: Fase 1

Dataset: **111** imágenes validadas.  
Primera evaluación: **56.8%** exact match (gate 85% en iteración).

### Arranque API

```bash
cd backend
source .venv/bin/activate
export STORAGE_PATH=../storage DATASET_PATH=../dataset
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

| Recurso | URL |
|---|---|
| UI HITL | http://localhost:8000/ui/ |
| OCR Fase 1 | `POST /api/ocr` |
| Swagger | http://localhost:8000/docs |

### Evaluar precisión

```bash
cd backend && source .venv/bin/activate
python ../scripts/evaluate_ocr.py
```

Reporte: `docs/reportes/eval_fase1_latest.md`
