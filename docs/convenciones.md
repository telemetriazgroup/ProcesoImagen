# Convenciones del proyecto ProcesoImagen

## Ramas

- `main` — estable
- `develop` — integración
- `fase-N/<descripcion>` — trabajo de fase
- `fix/<descripcion>` — correcciones

## Commits

```
tipo(ambito): mensaje en imperativo
```

Tipos: `feat`, `fix`, `docs`, `chore`, `test`, `refactor`.

Ejemplos:

- `feat(ocr): detectar ZGRU con normalización O/0`
- `docs(fases): cerrar gate fase 0`
- `chore(docker): healthcheck postgres`

## Carpetas

| Ruta | Responsabilidad |
|---|---|
| `backend/app/api` | Endpoints HTTP |
| `backend/app/core` | Preprocess, OCR, reglas |
| `backend/app/models` | Modelos SQLAlchemy (Fase 2) |
| `backend/app/schemas` | Schemas Pydantic (Fase 2) |
| `frontend/src` | UI React |
| `dataset/` | Fotos + ground truth |
| `storage/` | Imágenes subidas (no versionar contenido) |
| `docs/reportes/` | Salidas de evaluación OCR |
| `procesos_fases.md` | Ciclo, gates y bitácora |

## API

- Prefijo: `/api`
- Documentación interactiva: `/docs` (Swagger)
- Errores de negocio: nunca 500 por “sin código detectado”; respuesta controlada + ingreso manual

## Imágenes

- Formatos: JPEG, PNG, HEIC (Fase 2)
- Tamaño máximo: 15 MB (configurable)
- Nombre en storage: UUID + extensión original

## Evaluación OCR (Fase 1)

```bash
docker compose exec api python scripts/evaluate_ocr.py
```

El reporte se guarda en `docs/reportes/` y se versiona.
