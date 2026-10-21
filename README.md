# ProcesoImagen

OCR de códigos de equipos: HITL (0.5), motor de reglas (1), API + BD (2), app de campo (3).

- Requisitos: [`contexto.md`](contexto.md)
- Ciclo: [`procesos_fases.md`](procesos_fases.md)
- Fase 1: [`docs/fase1.md`](docs/fase1.md) — gate **86.9%**
- Fase 2: [`docs/fase2.md`](docs/fase2.md)
- Fase 3: [`docs/fase3.md`](docs/fase3.md)

## Estado: Fase 3

App móvil-first en Vite (puerto **5273**): captura → confirmar código → listado.

| App | URL |
|---|---|
| **Campo (Fase 3)** | http://localhost:5273 |
| HITL dataset (Fase 0.5) | http://localhost:8300/ui/ |
| Swagger API | http://localhost:8300/docs |

### Arranque

```bash
cp .env.example .env
docker compose up --build
```

Frontend local:

```bash
cd frontend && npm install && npm run dev
```

API local:

```bash
docker compose up -d db
cd backend && source .venv/bin/activate
alembic upgrade head
export STORAGE_PATH=../storage DATASET_PATH=../dataset
uvicorn app.main:app --reload --port 8300
```

### Flujo de campo

1. Tomar foto / galería → `POST /api/imagenes`
2. Confirmar o corregir código → `POST /api/registros`
3. Ver listado en `/registros`

### Tests API

```bash
cd backend && pytest -q
```

### Evaluar OCR

```bash
cd backend && python ../scripts/evaluate_ocr.py
```
