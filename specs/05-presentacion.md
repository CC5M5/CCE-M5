# Spec 05: Formato de Presentaciones

## Especificaciones Técnicas del Formato

| Parámetro | Valor | Observación |
|-----------|-------|-------------|
| **Formato base** | 274 Domingo 21 06 2026.pptx | Último PPTX real, no el MASTER |
| **Dimensiones** | 13.33" x 7.50" | 16:9 widescreen |
| **Aspect ratio** | 16:9 | ≈ 1.78:1 |
| **Orientación** | Horizontal | Landscape |
| **Formato de archivo** | .pptx (Office 2007+) | Compatible con LibreOffice |
| **Conversión PDF** | LibreOffice --headless | Para fieles y músicos |
| **Plantilla de referencia** | NAS: `Escolapios/11 Presentaciones PPT CCE M5/274 Domingo 21 06 2026.pptx` | |

## Diferencias MASTER vs. Último Formato

| Característica | MASTER (viejo) | 274 Domingo 21 06 2026 (actual) |
|----------------|------------------|-----------------------------------|
| Dimensiones | 10" x 7.5" | 13.33" x 7.50" |
| Aspect ratio | 4:3 | 16:9 |
| Total diapositivas | 121 | 109 |
| Layouts | 12 (genéricos) | 11 (español: "Diapositiva de título", etc.) |
| Tipo | Plantilla de canciones | Presentación semanal real |
| Uso propuesto | Referencia de canciones | Formato base para generación |

## Estructura de la Presentación Semanal

### Diapositivas Base (Obligatorias)

| Nº | Contenido | Layout | Notas |
|----|-----------|--------|-------|
| 1 | **Portada** | Título y objetos | Imagen de fondo según temporada |
| 2 | [Opcional] **Anuncios/Eventos** | En blanco | Si hay eventos especiales |
| 3 | **Primera Lectura** | Título y objetos | Cita + texto completo |
| 4 | **Salmo Responsorial** | Título y objetos | Cita + antífona + texto |
| 5 | [Opcional] **Segunda Lectura** | Título y objetos | Si aplica |
| 6 | **Evangelio** | Título y objetos | Cita + texto completo |
| 7 | **Entrada** | En blanco | Título + letra SIN acordes |
| 8 | **Perdón** | En blanco | Título + letra SIN acordes |
| 9 | **Gloria** | En blanco | Título + letra SIN acordes |
| 10 | **Salmo (cantado)** | En blanco | Título + letra SIN acordes |
| 11 | **Aleluya** | En blanco | Título + letra SIN acordes |
| 12 | **Ofertorio** | En blanco | Título + letra SIN acordes |
| 13 | **Santo** | En blanco | Título + letra SIN acordes |
| 14 | **Padre Nuestro** | En blanco | Título + letra SIN acordes |
| 15 | **Paz** | En blanco | Título + letra SIN acordes |
| 16 | **Comunión** | En blanco | Título + letra SIN acordes |
| 17 | **Canto a María** | En blanco | Título + letra SIN acordes |
| 18 | **Despedida** | En blanco | Título + letra SIN acordes |
| 19 | [Opcional] **Oración final** | En blanco | |

### Total estimado: 18-20 diapositivas

## Especificaciones Visuales

### Paleta de Colores por Temporada

| Temporada | Color principal | Color texto | Imagen fondo |
|-----------|----------------|-------------|--------------|
| **Tiempo Ordinario** | Verde (#4CAF50) | Blanco (#FFFFFF) | Naturaleza, camino |
| **Adviento** | Violeta (#9C27B0) | Blanco (#FFFFFF) | Velas, estrella |
| **Navidad** | Blanco/Dorado (#FFFFFF/#FFD700) | Azul oscuro | Nacimiento, luz |
| **Cuaresma** | Violeta (#9C27B0) | Blanco | Desierto, cruz |
| **Pascua** | Blanco/Dorado (#FFFFFF/#FFD700) | Rojo oscuro | Resurrección, luz |
| **Pentecostés** | Rojo (#F44336) | Blanco | Lenguas de fuego |
| **Solemnidades** | Blanco/Oro (#FFFFFF/#FFD700) | Azul oscuro | Según solemnidad |

### Tipografía

| Elemento | Fuente | Tamaño | Estilo | Color |
|----------|--------|--------|--------|-------|
| Título celebración | Arial | 36-40pt | Bold | Blanco |
| Título canción | Arial | 32-36pt | Bold | Blanco |
| Letra canción | Arial | 24-28pt | Regular | Blanco |
| Cita bíblica | Arial | 18-20pt | Italic | Amarillo claro |
| Texto lectura | Arial | 20-22pt | Regular | Blanco |
| Notas/alerts | Arial | 16-18pt | Italic | Amarillo |

### Layouts Utilizados (basado en 274)

| Layout ID | Nombre | Uso |
|-----------|--------|-----|
| 0 | Diapositiva de título | Portada, secciones |
| 1 | Título y objetos | Lecturas con imagen lateral |
| 6 | En blanco | Canciones (imagen de fondo + texto) |

## Formato de Canciones en PPTX (Sin Acordes)

```
┌────────────────────────────────────────────────────────────┐
│                                                            │
│                    [IMAGEN DE FONDO]                       │
│                                                            │
│         ┌────────────────────────────────┐                 │
│         │                                │                 │
│         │   TÍTULO DE LA CANCIÓN         │                 │
│         │   ─────────────────────        │                 │
│         │                                │                 │
│         │   Primera línea de la letra    │                 │
│         │   Segunda línea de la letra    │                 │
│         │   Tercera línea de la letra    │                 │
│         │                                │                 │
│         │   (CORO)                       │                 │
│         │   Primera línea del coro      │                 │
│         │   Segunda línea del coro      │                 │
│         │                                │                 │
│         └────────────────────────────────┘                 │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

## Formato de Lecturas en PPTX

```
┌────────────────────────────────────────────────────────────┐
│                                                            │
│  [IMAGEN DE FONDO]                                       │
│                                                            │
│  ┌────────────────────────────────────────────────────┐  │
│  │                                                    │  │
│  │  PRIMERA LECTURA                                   │  │
│  │  Eclo 27, 30 – 28, 7                               │  │
│  │  ─────────────────────────────────────────────────  │  │
│  │                                                    │  │
│  │  Texto completo de la lectura aquí...              │  │
│  │  Segunda línea del texto...                        │  │
│  │  Tercera línea del texto...                        │  │
│  │  ...                                               │  │
│  │  Última línea del texto.                           │  │
│  │                                                    │  │
│  │  Palabra de Dios.                                  │  │
│  │                                                    │  │
│  └────────────────────────────────────────────────────┘  │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

## Generación de PDF para Músicos (Con Acordes)

### Especificaciones del PDF

| Parámetro | Valor |
|-----------|-------|
| **Formato** | A4 o Letter |
| **Orientación** | Vertical (portrait) |
| **Márgenes** | 2cm |
| **Fuente acordes** | Courier New / monospace, 11pt, bold |
| **Fuente letra** | Times New Roman / serif, 12pt |
| **Interlineado** | 1.5 para acordes, 1.2 para letra |

### Ejemplo de Formato

```
══════════════════════════════════════════════════════════════════
     COMUNIDAD CRISTIANA ESCOLAPIA MONTEQUINTO
     Hoja de Músicos — Domingo XXIV T.O.
     13 de Septiembre de 2026
══════════════════════════════════════════════════════════════════

1. ENTRADA — "Al encuentro" (Do)
──────────────────────────────────────────────────────────────────
Do      Sol     Lam     Fa
AL ENCUENTRO VOY, CAMINANDO VOY,
Do              Sol     Fa      Sol
BUSCANDO LA VERDAD QUE HABITA EN TI.

[... estrofas ...]

──────────────────────────────────────────────────────────────────

2. PERDÓN — "Perdónanos, Señor" (Re)
──────────────────────────────────────────────────────────────────
Re      La7     Sol     La
PERDÓNANOS, SEÑOR, PERDÓNANOS,

[...]

══════════════════════════════════════════════════════════════════
NOTAS: 
• Cambio de tono en Gloria: modulación a Mi
• Evento especial: Confirmación de Pedro
══════════════════════════════════════════════════════════════════
```

## Estructura de Directorios de Output

```
presentaciones/
└── 2026/
    └── 09/
        └── 2026-09-13_domingo-xxiv-tiempo-ordinario/
            ├── presentacion.pptx              # Para fieles (sin acordes)
            ├── presentacion.pdf                # Versión PDF fieles
            ├── hoja_musicos.pdf               # Para músicos (CON acordes)
            ├── assets/
            │   ├── portada.png
            │   └── fondo_temporada.png
            └── index.html                     # Página web específica
```

## Reglas de Generación

1. **Portada**: Incluir nombre de la celebración, fecha, temporada, color litúrgico
2. **Lecturas**: Texto completo, citas en formato abreviado español
3. **Canciones**: Solo letra, sin acordes, sin notación musical
4. **Imágenes**: Fondo según temporada, opcionalmente imagen de la iglesia
5. **Numeración**: No numerar diapositivas (presentación litúrgica)
6. **Transiciones**: Sin transiciones automáticas (control manual)
7. **Eventos especiales**: Diapositiva adicional al inicio o final según corresponda
