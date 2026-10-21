# Fase 3 — Frontend web (campo)

**Estado:** En curso  
**Fecha:** 25 julio 2026  
**Prerrequisito:** API Fase 2 (`/api/imagenes`, `/api/registros`)

## Objetivo

Interfaz móvil-first para registrar equipos en campo: capturar foto → confirmar/corregir código → ver listado.

## Pantallas

| Ruta | Pantalla | API |
|---|---|---|
| `/` | Captura (cámara + galería) | `POST /api/imagenes` |
| `/confirmar` | Imagen + bbox + código editable | `POST /api/registros` |
| `/registros` | Listado, búsqueda y filtros | `GET /api/registros` |

- Si `sin_deteccion` o confianza &lt; **0.85**, el campo de código arranca vacío (ingreso manual).
- La UI HITL de dataset sigue en `http://localhost:8000/ui/` (no es esta app).

## Arranque

```bash
# API + Postgres
docker compose up -d db api

# Frontend
cd frontend && npm install && npm run dev
# → http://localhost:5173
```

`VITE_API_URL` (Compose) apunta a `http://localhost:8000`. En dev local, Vite hace proxy de `/api`.

## Gate (validación humana)

- [ ] Flujo en Android e iOS reales (cámara)
- [ ] Corregir código en ≤ 3 toques
- [ ] 3–5 usuarios completan “registra este equipo” sin ayuda
- [ ] Foto → confirmación percibida ≤ 10 s en red móvil
