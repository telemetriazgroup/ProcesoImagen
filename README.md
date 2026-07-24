# ProcesoImagen

Sistema web de reconocimiento OCR de códigos de equipos (`ZGRU…` y etiquetas *Serial No*).

- Requisitos y arquitectura: [`contexto.md`](contexto.md)
- Ciclo por fases y gates: [`procesos_fases.md`](procesos_fases.md)
- Convenciones: [`docs/convenciones.md`](docs/convenciones.md)

## Stack

FastAPI · PaddleOCR (Fase 1) · OpenCV · PostgreSQL · React + Vite · Docker Compose

## Arranque (Fase 0)

```bash
cp .env.example .env
docker compose up --build
```

| Servicio | URL |
|---|---|
| API + Swagger | http://localhost:8000/docs |
| Health | http://localhost:8000/api/health |
| Frontend | http://localhost:5173 |
| PostgreSQL | localhost:5432 (`procesoimagen` / `procesoimagen`) |

## Estado

**Fase 0 en curso:** entorno y scaffold listos. Pendiente recolectar ≥100 fotos etiquetadas en `dataset/`.

## Siguiente paso

Ver gate de Fase 0 y plan de Fase 1 en [`procesos_fases.md`](procesos_fases.md).
