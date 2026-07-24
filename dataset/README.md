# Dataset de validación (Fase 0)

Fotos reales de equipos para medir precisión OCR. **Sin este dataset, el gate de Fase 1 no es válido.**

## Estructura

```
dataset/
├── images/           # archivos .jpg / .jpeg / .png / .heic
├── ground_truth.csv  # etiquetas (ground truth)
└── README.md
```

## Cómo etiquetar

1. Copiar fotos a `dataset/images/` con nombres estables, p. ej. `zgru_h_001.jpg`.
2. Añadir una fila en `ground_truth.csv` por imagen.
3. Columnas:

| Columna | Valores | Descripción |
|---|---|---|
| `nombre_archivo` | nombre con extensión | Debe existir en `images/` |
| `codigo_correcto` | ej. `ZGRU12345` | Código real del equipo |
| `tipo` | `ZGRU` \| `SERIAL` | Tipo de detección esperada |
| `orientacion` | `horizontal` \| `vertical` \| `n/a` | Orientación del texto |
| `dificultad` | `normal` \| `dificil` | Condiciones de captura |
| `notas` | texto libre | Opcional |

## Cupos mínimos (gate Fase 0)

- 25 ZGRU horizontal  
- 25 ZGRU vertical  
- 25 Serial No / number / n  
- 25 difíciles (reflejo, poca luz, ángulo, suciedad)

**Total ≥ 100.** Preferir fotos de campo, no solo condiciones ideales.

## Privacidad

No subir al remoto imágenes con datos personales sensibles sin acuerdo del responsable del proyecto.
