# 7. Cancionero y Acordes

## 7.1. Fuente de datos

- Cancionero escolapio original: `ccem5music.blogspot.com`.
- Se migraron las canciones a SQLite manteniendo `letra_con_acordes` original.
- Nuevas canciones se añaden desde:
  - Editor de acordes (`:4322`).
  - Editor de diapositivas (`:4324/canciones/nueva`).
  - Panel admin API (`POST /canciones`).

## 7.2. Parser de acordes v3

Archivo: `src/parsers/acordes_parser_v3.py`

### Capacidades

- Detecta líneas de acordes emparejadas con líneas de letra.
- Soporta notación española (`Do`, `Re`, `Mi`, `Fa`, `Sol`, `La`, `Si`) e inglesa (`C`, `D`, `E`, `F`, `G`, `A`, `B`).
- Soporta sostenidos (`#`), bemoles (`b`), extensiones (`m`, `7`, `m7`, `maj7`, `sus4`, `add9`, etc.) y slash chords.
- Detecta indicadores de repetición: `(Sol7 si BIS)`, `Do x2`, `Do repetir`.
- Detecta etiquetas de sección: `Intro:`, `Estribillo:`, `Puente:`.
- Limpia líneas de metadatos del Blogspot (`escuchar`, `volver a lista`, `versión en ...`).

### Derivados generados

| Campo | Descripción |
|---|---|
| `estructura_json` | Array de líneas con tipo, acordes posicionales y letra. |
| `html_visual` | HTML con spans para renderizado web. |
| `letra_sin_acordes` | Letra limpia para presentaciones. |
| `tono` | Tono base detectado del primer acorde. |

## 7.3. Visualización web

- Componente `VisorAcordes` (React + Astro).
- Toggle con/sin acordes.
- Transposición de medio tono arriba/abajo.
- Botón de impresión y compartir.
- Estribillos en negrita automática (detección por MAYÚSCULAS) o manual (`**texto**`).

## 7.4. Vista para músicos

- Ruta Astro: `/musicos/YYYY-MM-DD/`.
- Muestra todas las canciones asignadas con acordes, en orden litúrgico.
- Se genera también PDF descargable.

