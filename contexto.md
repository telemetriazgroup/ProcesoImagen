# Documentación de Desarrollo — Sistema de Reconocimiento de Códigos de Equipos (OCR)

**Versión:** 1.0
**Fecha:** Julio 2026
**Estado:** Propuesta de desarrollo

---

## 1. Descripción general del proyecto

### 1.1 Objetivo

Desarrollar una aplicación web que permita a los usuarios subir o tomar fotografías de equipos, y que el sistema reconozca automáticamente el código identificador del equipo mediante OCR, lo valide y lo guarde en base de datos asociado a la imagen.

### 1.2 Casos de reconocimiento

El sistema debe cubrir dos escenarios de detección:

**Caso A — Código con prefijo ZGRU:** el código aparece impreso directamente sobre el equipo, comienza con las letras `ZGRU` seguidas de números, y puede estar orientado en horizontal o en vertical.

**Caso B — Etiqueta de número de serie:** la imagen contiene una etiqueta con alguno de los textos `Serial n`, `Serial number` o `Serial No` (en cualquier combinación de mayúsculas/minúsculas), y el código del equipo es el texto ubicado inmediatamente a la derecha, en la misma línea horizontal.

### 1.3 Alcance

**Incluido:** aplicación web con carga de imágenes desde archivo o cámara del móvil, procesamiento OCR en servidor, extracción del código según reglas, pantalla de confirmación/corrección manual, almacenamiento en base de datos con referencia a la imagen, listado y búsqueda de registros.

**Excluido (fase posterior):** aplicación móvil nativa, procesamiento por lotes masivo, reconocimiento de otros formatos de código (QR, código de barras), integración con sistemas externos (ERP, CMMS).

### 1.4 Stack tecnológico

| Componente | Tecnología | Justificación |
|---|---|---|
| Backend / API | Python 3.11+ con FastAPI | Ecosistema OCR maduro, API asíncrona, documentación automática (Swagger) |
| Motor OCR | PaddleOCR | Gratuito, detecta texto horizontal y vertical de forma nativa, devuelve coordenadas y confianza |
| Preprocesamiento | OpenCV | Mejora de contraste, escala de grises, corrección de inclinación |
| Base de datos | PostgreSQL 15+ | Robusta, gratuita, soporte de índices para búsqueda |
| Almacenamiento de imágenes | Sistema de archivos del servidor (fase 1) / S3 o compatible (producción) | Simplicidad inicial, escalable después |
| Frontend | React (o Vue) + input de cámara HTML5 | Captura directa desde móvil sin app nativa |
| Contenedores | Docker + Docker Compose | Despliegue reproducible |

---

## 2. Arquitectura del sistema

```
[Navegador / Móvil]
   │  (subida de imagen vía HTTPS)
   ▼
[Frontend Web — React]
   │  POST /api/imagenes
   ▼
[API FastAPI]
   ├── 1. Guarda imagen original en almacenamiento
   ├── 2. Preprocesamiento (OpenCV)
   ├── 3. OCR (PaddleOCR) → lista de bloques {texto, coordenadas, confianza}
   ├── 4. Motor de reglas de extracción (ZGRU / Serial No)
   ├── 5. Respuesta con código detectado + confianza
   ▼
[Usuario confirma o corrige]
   │  POST /api/registros (confirmación)
   ▼
[PostgreSQL] ← guarda código + ruta de imagen + metadatos
```

### 2.1 Modelo de datos (tabla principal)

```sql
CREATE TABLE registros_equipos (
    id              SERIAL PRIMARY KEY,
    codigo          VARCHAR(50) NOT NULL,
    tipo_deteccion  VARCHAR(20) NOT NULL,  -- 'ZGRU' | 'SERIAL' | 'MANUAL'
    codigo_ocr      VARCHAR(50),           -- lo que detectó el OCR (antes de corrección)
    confianza       NUMERIC(5,4),          -- score del OCR (0 a 1)
    validado_manual BOOLEAN DEFAULT FALSE,
    ruta_imagen     TEXT NOT NULL,
    orientacion     VARCHAR(12),           -- 'horizontal' | 'vertical'
    usuario_id      INTEGER,
    creado_en       TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_registros_codigo ON registros_equipos (codigo);
```

Guardar tanto `codigo_ocr` (lo detectado) como `codigo` (lo confirmado) permite medir la precisión real del sistema en producción comparando ambos campos.

---

## 3. Plan de desarrollo por fases

Cada fase termina con una **validación obligatoria (gate)**: no se avanza a la siguiente fase hasta cumplir los criterios de salida.

---

### FASE 0 — Preparación y dataset (1 semana)

**Objetivo:** montar el entorno y, sobre todo, construir el conjunto de imágenes de prueba que servirá para validar todo el proyecto.

**Actividades:**
1. Configurar repositorio Git, entorno Python, Docker Compose con PostgreSQL.
2. Recolectar un **dataset de validación**: mínimo 100 fotos reales de equipos, cubriendo:
   - Códigos ZGRU en horizontal (mín. 25 fotos)
   - Códigos ZGRU en vertical (mín. 25 fotos)
   - Etiquetas "Serial No / Serial number / Serial n" (mín. 25 fotos)
   - Casos difíciles: reflejos, poca luz, ángulo inclinado, placa sucia o rayada (mín. 25 fotos)
3. Etiquetar manualmente cada foto en una hoja de cálculo: `nombre_archivo, codigo_correcto, tipo, orientacion, dificultad`. Este archivo es el **ground truth** contra el que se medirá el OCR.

**Criterios de salida (validación de fase):**
- [ ] Entorno levanta con un solo comando (`docker compose up`).
- [ ] Dataset de ≥100 imágenes etiquetadas y versionado.
- [ ] Documento de convenciones del proyecto (nombres de ramas, formato de commits, estructura de carpetas).

> ⚠️ **Riesgo crítico:** sin un dataset real y variado, todas las métricas posteriores serán ficticias. No usar solo fotos "bonitas" tomadas en condiciones ideales.

---

### FASE 1 — Núcleo OCR y motor de reglas (2–3 semanas)

**Objetivo:** lograr que, dada una imagen, el sistema devuelva el código correcto. Sin interfaz web todavía: se trabaja con scripts y la API mínima.

**Actividades:**
1. **Pipeline de preprocesamiento (OpenCV):** escala de grises → mejora de contraste (CLAHE) → corrección de inclinación → redimensionado. Cada paso debe poder activarse/desactivarse por configuración para medir su aporte real.
2. **Integración de PaddleOCR:** función que recibe una imagen y devuelve lista de bloques `{texto, bbox, confianza, ángulo}`.
3. **Regla A (ZGRU):** buscar en todos los bloques coincidencias con la expresión regular `ZGRU[\s\-]?\d+`. Normalizar el resultado (eliminar espacios/guiones intermedios si aplica). Manejar confusiones típicas del OCR: `O↔0`, `I↔1`, `S↔5`, `B↔8` en la parte numérica.
4. **Regla B (Serial No):** localizar bloque cuyo texto coincida con `serial\s*(n|no|number)\.?:?` (case-insensitive). Dos sub-casos:
   - El OCR unió etiqueta y valor en un bloque → extraer con regex lo que sigue a la etiqueta.
   - Etiqueta y valor en bloques separados → buscar el bloque con centro vertical similar (tolerancia ±40% de la altura del bloque) y coordenada X mayor; elegir el más cercano.
5. **Estrategia de fallback para texto vertical:** si no hay coincidencia, rotar la imagen 90° y 270° y reintentar (red de seguridad aunque PaddleOCR maneje vertical).
6. **Script de evaluación automática:** recorre el dataset de la Fase 0, ejecuta el pipeline y compara contra el ground truth. Genera reporte: precisión global, precisión por categoría (horizontal/vertical/serial/difícil), casos fallados con su imagen.
7. **API mínima:** endpoint `POST /api/ocr` que recibe imagen y devuelve JSON con código, tipo, confianza y bloques detectados.

**Criterios de salida (validación de fase):**
- [ ] **Precisión ≥ 85%** sobre el dataset completo (exact match del código).
- [ ] **Precisión ≥ 90%** en las categorías horizontal y serial (las más comunes).
- [ ] Tiempo de procesamiento ≤ 5 segundos por imagen en el servidor objetivo.
- [ ] El reporte de evaluación se genera con un solo comando y está versionado.
- [ ] Revisión de los casos fallados documentada: para cada fallo, causa identificada (imagen, OCR o regla).

> 💡 Si tras dos iteraciones de ajuste no se alcanza el 85%, evaluar el **plan B**: usar Google Cloud Vision o AWS Textract como motor OCR (mismo motor de reglas, solo cambia el proveedor). Esta decisión debe tomarse aquí, no más adelante.

---

### FASE 2 — API completa y persistencia (1–2 semanas)

**Objetivo:** convertir el núcleo en un servicio real con base de datos.

**Actividades:**
1. Endpoints:
   - `POST /api/imagenes` — sube imagen, ejecuta OCR, devuelve propuesta de código (no guarda registro definitivo).
   - `POST /api/registros` — confirma y guarda el registro (código final, referencia a imagen, si hubo corrección manual).
   - `GET /api/registros` — listado con filtros por código, fecha, tipo.
   - `GET /api/registros/{id}` — detalle con URL de la imagen.
2. Almacenamiento de imágenes con nombre único (UUID) y validaciones: formato permitido (JPEG/PNG/HEIC), tamaño máximo (p. ej. 15 MB), redimensionado de copias para visualización.
3. Migraciones de base de datos (Alembic).
4. Autenticación básica (token JWT) si el sistema tendrá varios usuarios.
5. Pruebas automatizadas: unitarias del motor de reglas (≥ 90% cobertura en ese módulo) e integración de los endpoints.
6. Manejo de errores: imagen ilegible, sin código detectado, formato inválido — cada caso con respuesta HTTP y mensaje claro.

**Criterios de salida (validación de fase):**
- [ ] Todos los endpoints documentados en Swagger y probados.
- [ ] Suite de pruebas pasa en CI (GitHub Actions o similar).
- [ ] Prueba de flujo completo por API: subir foto → recibir código → confirmar → verificar registro en BD con la imagen accesible.
- [ ] Caso "sin detección" devuelve respuesta controlada que permite ingreso manual (nunca error 500).

---

### FASE 3 — Frontend web (2 semanas)

**Objetivo:** interfaz usable desde móvil y escritorio.

**Actividades:**
1. **Pantalla de captura:** botón de subir archivo + captura directa de cámara (`<input type="file" accept="image/*" capture="environment">`). Indicador de carga durante el procesamiento.
2. **Pantalla de confirmación (la más importante):** muestra la imagen con el código detectado resaltado (dibujando el bounding box sobre la foto), el código propuesto en un campo **editable**, el nivel de confianza, y botones "Confirmar" / "Corregir". Si la confianza es baja (< 0.85) o no hubo detección, el campo aparece vacío para ingreso manual.
3. **Pantalla de listado:** tabla de registros con búsqueda por código, miniatura de la imagen, filtros por fecha y tipo, indicador de si fue corregido manualmente.
4. Diseño responsive con prioridad móvil (el uso principal será tomar fotos en campo).

**Criterios de salida (validación de fase):**
- [ ] Flujo completo funciona desde un teléfono real (Android e iOS) usando la cámara.
- [ ] El usuario puede corregir un código erróneo en menos de 3 toques.
- [ ] Prueba con 3–5 usuarios reales (técnicos que usarán el sistema): tarea "registra este equipo" completada sin ayuda por todos.
- [ ] Tiempo total percibido (foto → confirmación) ≤ 10 segundos en red móvil.

---

### FASE 4 — Piloto en condiciones reales (2 semanas)

**Objetivo:** validar el sistema con usuarios y equipos reales antes de darlo por terminado.

**Actividades:**
1. Desplegar en servidor de staging accesible para el equipo piloto.
2. Seleccionar 2–4 usuarios que registren equipos reales durante 2 semanas (objetivo: ≥ 200 registros).
3. Monitorear métricas automáticas:
   - **Tasa de acierto real** = registros donde `codigo == codigo_ocr` / total (gracias a guardar ambos campos).
   - Tasa de "sin detección".
   - Tiempo medio de procesamiento.
   - Errores de servidor.
4. Recoger feedback cualitativo de los usuarios (formulario corto + entrevista).
5. Iterar: ajustar reglas, regex y preprocesamiento con los casos reales fallados. Añadir esos casos al dataset de validación.

**Criterios de salida (validación de fase):**
- [ ] Tasa de acierto real ≥ 90% (el usuario no tuvo que corregir).
- [ ] Cero pérdidas de datos: toda imagen subida tiene su registro o su error registrado.
- [ ] Feedback de usuarios sin bloqueantes ("no lo usaría porque...").
- [ ] Backlog de mejoras priorizado para post-lanzamiento.

---

### FASE 5 — Producción y cierre (1 semana)

**Objetivo:** despliegue estable y entrega formal.

**Actividades:**
1. Despliegue en producción: HTTPS, dominio, respaldos automáticos de base de datos e imágenes, logs centralizados.
2. Monitoreo y alertas (caída del servicio, errores de OCR anómalos, disco lleno).
3. Documentación de entrega:
   - Manual de usuario (con capturas, 2–3 páginas).
   - Manual de operación: cómo desplegar, respaldar, restaurar y actualizar.
   - Documentación técnica: arquitectura, decisiones tomadas, cómo agregar un nuevo patrón de código en el futuro.
4. Capacitación breve a los usuarios finales.
5. Definir plan de mantenimiento: quién revisa mensualmente la tasa de acierto y los casos fallados.

**Criterios de salida (validación de fase):**
- [ ] Sistema en producción con respaldo verificado (probar una restauración real).
- [ ] Documentación entregada y revisada.
- [ ] Acta de aceptación firmada por el responsable del proyecto.

---

## 4. Resumen de cronograma

| Fase | Duración estimada | Entregable clave | Gate de validación |
|---|---|---|---|
| 0. Preparación y dataset | 1 semana | Dataset etiquetado ≥100 imágenes | Entorno reproducible + ground truth |
| 1. Núcleo OCR y reglas | 2–3 semanas | Motor de detección + reporte de precisión | Precisión ≥ 85% global |
| 2. API y persistencia | 1–2 semanas | API REST completa con BD | Flujo E2E por API + CI en verde |
| 3. Frontend web | 2 semanas | App web responsive | Prueba con usuarios reales en móvil |
| 4. Piloto | 2 semanas | ≥200 registros reales | Acierto real ≥ 90% |
| 5. Producción | 1 semana | Sistema desplegado + documentación | Acta de aceptación |
| **Total** | **9–11 semanas** | | |

---

## 5. Riesgos principales y mitigación

| Riesgo | Probabilidad | Impacto | Mitigación |
|---|---|---|---|
| Precisión OCR insuficiente en fotos de campo | Media | Alto | Dataset realista desde Fase 0; plan B con Cloud Vision/Textract decidido en gate de Fase 1; confirmación manual siempre disponible |
| Confusión de caracteres (O/0, I/1) | Alta | Medio | Normalización por posición (letras al inicio, números después); mostrar código al usuario para confirmar |
| Fotos con dos códigos en la misma imagen | Baja | Medio | Si hay múltiples coincidencias, mostrar todas y que el usuario elija |
| Texto vertical mal detectado | Media | Medio | Fallback de rotación 90°/270°; casos verticales obligatorios en el dataset |
| Usuarios confirman sin revisar (acierto "falso") | Media | Medio | Resaltar el código sobre la foto; auditoría mensual comparando `codigo` vs `codigo_ocr` en muestras |
| Crecimiento de almacenamiento de imágenes | Alta a largo plazo | Bajo | Comprimir copias de visualización; política de retención definida en Fase 5 |

---

## 6. Métricas de éxito del proyecto

- **Precisión de detección automática:** ≥ 90% en producción (medida real vía `codigo` vs `codigo_ocr`).
- **Tiempo de registro por equipo:** ≤ 15 segundos desde foto hasta guardado.
- **Adopción:** los usuarios piloto siguen usando el sistema voluntariamente tras el lanzamiento.
- **Cero registros perdidos** o imágenes huérfanas.

---

## 7. Evolución futura (fuera de alcance inicial)

- Lectura de códigos QR / códigos de barras como vía alternativa más fiable.
- Procesamiento por lotes (subir 50 fotos de una vez).
- Modelo de detección entrenado a medida (fine-tuning) si aparecen formatos de placa muy específicos.
- Integración con el sistema de mantenimiento o inventario de la empresa.
- App móvil nativa con funcionamiento offline.