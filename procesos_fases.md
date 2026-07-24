# Ciclo de desarrollo por fases — ProcesoImagen (OCR equipos)

**Versión:** 1.0  
**Fecha:** 24 julio 2026  
**Fuente de requisitos:** `contexto.md`  
**Estado actual:** Fase 0 en curso

---

## 1. Resumen ejecutivo

Aplicación web para fotografiar equipos, reconocer el código (ZGRU o Serial No) con OCR, confirmar/corregir y guardar el registro con la imagen.

**Ciclo total estimado:** 9–11 semanas.  
**Principio de avance:** cada fase cierra con un *gate* de validación; no se inicia la siguiente sin cumplirlo.

---

## 2. Stack open source (al alcance)

| Capa | Tecnología | Licencia / notas | Fase de uso |
|---|---|---|---|
| API | Python 3.11+ / FastAPI + Uvicorn | MIT | 0–5 |
| OCR | PaddleOCR | Apache 2.0 | 1+ |
| Visión | OpenCV (opencv-python-headless) | Apache 2.0 | 1+ |
| BD | PostgreSQL 16 | PostgreSQL License | 0, 2+ |
| ORM / migraciones | SQLAlchemy 2 + Alembic | MIT | 2+ |
| Frontend | React 18 + Vite + TypeScript | MIT | 0 scaffold, 3 |
| Contenedores | Docker + Docker Compose | Apache 2.0 | 0+ |
| Almacenamiento imágenes | Filesystem local (`storage/`) | — | 1–4; S3-compatible después |
| CI | GitHub Actions (cuando exista remoto) | — | 2+ |
| Auth (si multi-usuario) | JWT (python-jose / PyJWT) | MIT | 2 (opcional) |

**Plan B OCR (solo si el gate de Fase 1 falla tras 2 iteraciones):** Google Cloud Vision o AWS Textract — mismo motor de reglas, cambia el proveedor. Decisión en el gate de Fase 1, no después.

**Fuera de alcance inicial (open source futuro):** lectura QR/barras (zxing / pyzbar), app nativa, fine-tuning de modelo.

---

## 3. Estructura del repositorio

```
ProcesoImagen/
├── contexto.md                 # Requisitos y arquitectura de negocio
├── procesos_fases.md           # Este documento (ciclo y gates)
├── README.md                   # Arranque rápido
├── docker-compose.yml
├── .env.example
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── pyproject.toml          # opcional
│   ├── alembic/                # Fase 2
│   └── app/
│       ├── main.py
│       ├── config.py
│       ├── api/                # routers
│       ├── core/               # preprocess, ocr, rules
│       ├── models/
│       ├── schemas/
│       └── services/
├── frontend/                   # Vite + React (scaffold Fase 0)
├── storage/                    # imágenes (gitignored)
│   ├── originals/
│   └── thumbs/
├── dataset/
│   ├── images/                 # fotos de validación (git-lfs o local)
│   ├── ground_truth.csv        # etiquetas
│   └── README.md
├── scripts/
│   ├── evaluate_ocr.py         # Fase 1
│   └── seed_demo.py
└── docs/
    ├── convenciones.md
    └── reportes/               # reportes de evaluación versionados
```

---

## 4. Convención de trabajo

### Ramas

| Rama | Uso |
|---|---|
| `main` | Estable / producción |
| `develop` | Integración |
| `fase-N/<corto>` | Trabajo de fase (ej. `fase-0/scaffold`, `fase-1/reglas-zgru`) |
| `fix/<corto>` | Correcciones |

### Commits

Formato: `tipo(ambito): mensaje`  
Tipos: `feat`, `fix`, `docs`, `chore`, `test`, `refactor`.  
Ejemplo: `feat(ocr): regla Serial No con bloques adyacentes`.

### Definition of Done por fase

1. Criterios de salida (gate) marcados.  
2. Código ejecutable con `docker compose up`.  
3. Documentación de la fase actualizada en este archivo (sección *Estado*).  
4. Sin secretos en el repo (`.env` solo local).

---

## 5. Ciclo de desarrollo

```
Fase 0 → Fase 1 → Fase 2 → Fase 3 → Fase 4 → Fase 5
 Prep     OCR+reglas  API+BD    Frontend   Piloto    Producción
 1 sem    2–3 sem     1–2 sem   2 sem      2 sem     1 sem
```

Cada flecha = gate aprobado.

---

### FASE 0 — Preparación y dataset *(en curso)*

**Duración:** 1 semana  
**Objetivo:** entorno reproducible + ground truth para medir OCR.

| # | Actividad | Entregable |
|---|---|---|
| 0.1 | Repo, Docker Compose (API + PostgreSQL), `.env.example` | `docker compose up` |
| 0.2 | Scaffold FastAPI + healthcheck | `GET /api/health` |
| 0.3 | Scaffold frontend Vite/React | App mínima |
| 0.4 | Carpetas `dataset/`, plantilla `ground_truth.csv` | Convenciones de etiquetado |
| 0.5 | Documento de convenciones | `docs/convenciones.md` |
| 0.6 | Recolectar ≥100 fotos reales etiquetadas | Dataset + CSV |

**Distribución mínima del dataset:**

| Categoría | Mínimo |
|---|---|
| ZGRU horizontal | 25 |
| ZGRU vertical | 25 |
| Serial No / number / n | 25 |
| Difíciles (luz, reflejo, ángulo, suciedad) | 25 |

**Gate Fase 0:**

- [ ] `docker compose up` levanta API + PostgreSQL
- [ ] Dataset ≥100 imágenes con `ground_truth.csv` completo
- [ ] Convenciones documentadas y estructura de carpetas estable

**Riesgo:** sin fotos reales de campo, las métricas de Fase 1 no sirven.

---

### FASE 1 — Núcleo OCR y motor de reglas

**Duración:** 2–3 semanas  
**Objetivo:** dada una imagen → código correcto (sin UI completa).

| # | Actividad |
|---|---|
| 1.1 | Preprocesamiento OpenCV configurable (CLAHE, skew, resize) |
| 1.2 | Integración PaddleOCR → bloques `{texto, bbox, confianza, ángulo}` |
| 1.3 | Regla A: `ZGRU[\s\-]?\d+` + normalización O/0, I/1, etc. |
| 1.4 | Regla B: etiqueta Serial + valor (mismo bloque o adyacente) |
| 1.5 | Fallback rotación 90° / 270° |
| 1.6 | Script `scripts/evaluate_ocr.py` + reporte en `docs/reportes/` |
| 1.7 | `POST /api/ocr` (propuesta, sin persistir registro) |

**Gate Fase 1:**

- [ ] Precisión ≥ 85% dataset completo (exact match)
- [ ] ≥ 90% en horizontal y serial
- [ ] ≤ 5 s/imagen en servidor objetivo
- [ ] Reporte con un comando; fallos con causa documentada
- [ ] Si no se alcanza tras 2 iteraciones → decidir Plan B OCR

---

### FASE 2 — API completa y persistencia

**Duración:** 1–2 semanas

| Endpoint | Rol |
|---|---|
| `POST /api/imagenes` | Sube imagen, OCR, propuesta (no registro final) |
| `POST /api/registros` | Confirma y persiste |
| `GET /api/registros` | Listado + filtros |
| `GET /api/registros/{id}` | Detalle + URL imagen |

También: UUID en storage, validación JPEG/PNG/HEIC, Alembic, tests, manejo “sin detección” sin 500. JWT si hay multi-usuario.

**Gate Fase 2:**

- [ ] Swagger completo y probado
- [ ] CI en verde
- [ ] Flujo E2E API: subir → confirmar → ver en BD + imagen
- [ ] Sin detección → ingreso manual controlado

---

### FASE 3 — Frontend web

**Duración:** 2 semanas  
Prioridad móvil (cámara en campo).

1. Captura: archivo + `capture="environment"`  
2. Confirmación: bbox, código editable, confianza, Confirmar/Corregir  
3. Listado: búsqueda, miniatura, filtros, flag corrección manual  

**Gate Fase 3:**

- [ ] Flujo en Android e iOS reales
- [ ] Corrección en ≤ 3 toques
- [ ] 3–5 usuarios reales completan “registra este equipo” sin ayuda
- [ ] Foto → confirmación ≤ 10 s en red móvil

---

### FASE 4 — Piloto

**Duración:** 2 semanas · ≥200 registros reales · 2–4 usuarios

Métricas: acierto real (`codigo == codigo_ocr`), sin detección, latencia, errores. Feedback + ampliar dataset con fallos.

**Gate Fase 4:**

- [ ] Acierto real ≥ 90%
- [ ] Cero pérdidas de datos
- [ ] Sin bloqueantes de usabilidad
- [ ] Backlog post-lanzamiento priorizado

---

### FASE 5 — Producción y cierre

**Duración:** 1 semana

HTTPS, respaldos BD/imágenes, monitoreo, manuales (usuario + operación + técnico), capacitación, plan de mantenimiento mensual de acierto.

**Gate Fase 5:**

- [ ] Producción + restauración de respaldo verificada
- [ ] Documentación entregada
- [ ] Acta de aceptación

---

## 6. Cronograma

| Fase | Semanas | Entregable clave | Gate |
|---|---|---|---|
| 0 Preparación | 1 | Entorno + dataset | Compose + ground truth |
| 1 OCR y reglas | 2–3 | Motor + evaluación | ≥85% precisión |
| 2 API y BD | 1–2 | REST + persistencia | E2E API + CI |
| 3 Frontend | 2 | App responsive | Usuarios en móvil |
| 4 Piloto | 2 | ≥200 registros | ≥90% acierto real |
| 5 Producción | 1 | Deploy + docs | Acta |
| **Total** | **9–11** | | |

---

## 7. Modelo de datos (referencia)

```sql
CREATE TABLE registros_equipos (
    id              SERIAL PRIMARY KEY,
    codigo          VARCHAR(50) NOT NULL,
    tipo_deteccion  VARCHAR(20) NOT NULL,  -- ZGRU | SERIAL | MANUAL
    codigo_ocr      VARCHAR(50),
    confianza       NUMERIC(5,4),
    validado_manual BOOLEAN DEFAULT FALSE,
    ruta_imagen     TEXT NOT NULL,
    orientacion     VARCHAR(12),
    usuario_id      INTEGER,
    creado_en       TIMESTAMPTZ DEFAULT NOW()
);
CREATE INDEX idx_registros_codigo ON registros_equipos (codigo);
```

Guardar `codigo_ocr` y `codigo` permite medir precisión real en piloto/producción.

---

## 8. Métricas de éxito

| Métrica | Objetivo |
|---|---|
| Precisión automática en producción | ≥ 90% (`codigo` vs `codigo_ocr`) |
| Tiempo de registro | ≤ 15 s foto → guardado |
| Integridad | Cero imágenes huérfanas / registros perdidos |
| Adopción | Uso voluntario tras piloto |

---

## 9. Estado del proyecto (bitácora)

| Fecha | Fase | Avance |
|---|---|---|
| 2026-07-24 | 0 | Creado `procesos_fases.md`. Scaffold: Docker Compose (api+db+frontend), FastAPI `/api/health`, React/Vite mínimo, `dataset/ground_truth.csv`, `docs/convenciones.md`. Pendiente: ≥100 fotos reales etiquetadas. |

### Checklist operativo Fase 0

- [x] Documentar ciclo en `procesos_fases.md`
- [x] Scaffold backend + Docker Compose
- [x] Scaffold frontend
- [x] Plantilla dataset + convenciones
- [ ] Recolección y etiquetado ≥100 imágenes *(equipo de campo)*
- [ ] Verificar `docker compose up --build` en la máquina de desarrollo *(pendiente de ejecutar en host)*

---

## 10. Cómo continuar en la siguiente sesión

1. Completar etiquetado del dataset (bloqueante para gate Fase 0).  
2. Al cerrar Fase 0, abrir `fase-1/nucleo-ocr` e implementar preprocess + PaddleOCR + reglas.  
3. No avanzar a frontend completo (Fase 3) hasta API + persistencia (Fase 2).  
4. Actualizar la sección **9. Estado** al cerrar cada gate.
