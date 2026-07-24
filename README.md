# ProcesoImagen

OCR de códigos de equipos con **validación humana** antes de reglas de negocio.

- Requisitos: [`contexto.md`](contexto.md)
- Ciclo por fases: [`procesos_fases.md`](procesos_fases.md)
- **Piloto HITL 0.5:** [`previo.md`](previo.md)

## Estado: Fase 0.5 (intervención humana)

1. Sube una foto  
2. Ves **todos** los pasos del preprocess/OCR  
3. Confirmas o corriges el texto  
4. Eso alimenta `dataset/` (Fase 0) con data ya corregida  

### Arranque

```bash
cd backend
source .venv/bin/activate
export STORAGE_PATH=../storage DATASET_PATH=../dataset
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Abrir **http://localhost:8000/ui/**

| Recurso | URL |
|---|---|
| Interfaz piloto | http://localhost:8000/ui/ |
| Swagger | http://localhost:8000/docs |
| Dataset | `dataset/ground_truth.csv` + `dataset/images/` |
| Feedback log | `dataset/feedback.jsonl` |

## Stack

FastAPI · OpenCV · RapidOCR · React (opcional) · PostgreSQL (Fase 2+) · Docker Compose
