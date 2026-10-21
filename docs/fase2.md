# Fase 2 — API completa y persistencia

**Estado:** En curso  
**Fecha:** 24 julio 2026  
**Prerrequisito:** Gate Fase 1 cumplido — **86.9%** (113/130) · ver `docs/reportes/eval_fase1_latest.md`

## Objetivo

Convertir el núcleo OCR en servicio con PostgreSQL: subir imagen → propuesta → confirmar registro → listar/consultar.

## Alcance

- Endpoints: `POST /api/imagenes`, `GET /api/imagenes/{id}/archivo`, `POST/GET /api/registros`, `GET /api/registros/{id}`
- Storage UUID (`storage/originals` + thumbs), JPEG/PNG/WebP/HEIC (HEIC→JPEG)
- Alembic + SQLAlchemy
- Sin JWT (API abierta en LAN); `usuario_id` nullable para fases siguientes
- Tests E2E + CI GitHub Actions

## Flujo

1. Cliente sube foto → `POST /api/imagenes` → guarda archivo + propuesta OCR en tabla `imagenes`.
2. Usuario confirma/corrige → `POST /api/registros` con `imagen_id` + `codigo`.
3. Listado/detalle → `GET /api/registros` / `{id}` con `url_imagen`.

## Endpoints

| Método | Ruta | Rol |
|---|---|---|
| POST | `/api/imagenes` | Sube + OCR + propuesta (`imagenes`) |
| GET | `/api/imagenes/{id}/archivo` | Original (`?thumb=1` miniatura) |
| POST | `/api/registros` | Confirma código final |
| GET | `/api/registros` | Listado + filtros |
| GET | `/api/registros/{id}` | Detalle |

## Gate

- [x] Endpoints documentados en Swagger (`/docs`)
- [x] Suite de pruebas (unit + integración Fase 2)
- [x] CI GitHub Actions (`.github/workflows/ci.yml`)
- [ ] Verificar E2E manual en entorno local/Compose
- [x] Sin detección → ingreso manual (test + respuesta 201 controlada)

## Cómo probar

```bash
docker compose up -d db
cd backend && source .venv/bin/activate
alembic upgrade head
uvicorn app.main:app --reload --port 8000
# Swagger: http://localhost:8000/docs
pytest -q
```
