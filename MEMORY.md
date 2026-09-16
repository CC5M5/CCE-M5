# MEMORY.md - Memoria de Largo Plazo

## Proyecto: CCE-M5-Web-Presentaciones

<!-- observed: 2026-09-12 | status: active | project: CCE-M5-Web-Presentaciones -->

### Resumen
Sistema automatizado para preparación semanal de presentaciones litúrgicas con cancionero escolapio, hoja para músicos con acordes, y web de publicación. Arquitectura híbrida: Mission Control + OpenCode + OpenClaw.

**Estado actual:** FASE 5 completada (Integración end-to-end). PPTX y PDF generados; pendiente corregir errores detectados en la web.

### Ubicación del Proyecto
`~/proyectos/CCE-M5-Web-Presentaciones/`
**Repositorio GitHub:** https://github.com/CC5M5/CCE-M5

### Fuentes de Datos
- **Lecturas**: https://servicioskoinonia.org/biblico/calendario
- **Cancionero**: https://ccem5music.blogspot.com/p/cancionero-escolapio.html
- **Plantillas PPTX**: NAS `//192.168.1.177/homes/Rafa/Escolapios/11 Presentaciones PPT CCE M5/`

### Formato Base PPTX
- **Archivo de referencia**: `274 Domingo 21 06 2026.pptx` (NO el MASTER)
- **Dimensiones**: 16:9 (13.33" x 7.50")
- **Total diapositivas**: ~109
- **Layouts**: 11 (español)

### MASTER (Solo Referencia de Canciones)
- **Archivo**: `MASTER_PowerPoint Eucaristía.pptx`
- **Dimensiones**: 4:3 (10" x 7.5") - **NO USAR PARA FORMATO**
- **Uso**: Referencia de canciones disponibles

### Momentos Litúrgicos (12)
1. Entrada, 2. Perdón, 3. Gloria, 4. Salmo, 5. Aleluya, 6. Ofertorio, 7. Santo, 8. Padre Nuestro, 9. Paz, 10. Comunión, 11. Canto a María, 12. Despedida

### Estructura de Directorios
```
~/proyectos/CCE-M5-Web-Presentaciones/
├── .mission-control/       # Mission Control config
├── .openclaw/              # Automatizaciones
├── specs/                  # 10 specs SDD
├── data/                   # Lecturas, canciones, DB
│   ├── db.sqlite3          # Base de datos SQLite
│   └── canciones/          # Datos de canciones
├── src/                     # Código fuente
│   ├── scrapers/
│   │   └── blogspot_scraper.py
│   ├── parsers/
│   │   ├── acordes_parser.py       # Parser legacy
│   │   └── acordes_parser_v2.py    # Parser con posicionamiento
│   ├── generators/
│   └── api/
├── presentaciones/         # Output PPTX/PDF
├── web/                    # Astro site (pendiente)
├── docs/                   # Documentación + ADRs
│   ├── INFORME_ESTRATEGICO_V3.md
│   └── INFORME_ESTRATEGICO_V3.pdf
└── tests/                  # Tests
```

### Stack Tecnológico
- **Orquestación**: Mission Control (crshdn) - http://192.168.68.244:4000/
- **Agentes desarrollo**: OpenCode
- **Agentes validación**: OpenClaw nativo
- **Base de datos**: SQLite (fase inicial) → PostgreSQL (futuro)
- **PPTX**: python-pptx
- **PDF**: ReportLab/WeasyPrint
- **Web**: Astro + Tailwind CSS
- **Hosting**: GitHub Pages
- **Comentarios**: GitHub Issues API

### Base de Datos SQLite
**Ubicación:** `data/db.sqlite3`

**Tablas:**
- `lecturas` - Lecturas dominicales de Koinonia
- `canciones` - Cancionero escolapio con acordes posicionados
- `presentaciones` - Presentaciones generadas semanalmente
- `comentarios` - Sistema de aprobaciones
- `automation_log` - Log de agentes

**Columnas de canciones (ampliadas):**
- `id`, `titulo`, `titulo_url`
- `letra_con_acordes` - Texto original completo
- `letra_sin_acordes` - Letra limpia
- `estructura_json` - **NUEVO** JSON con acordes posicionados
- `html_visual` - **NUEVO** HTML con acordes sobre letra
- `html_original` - **NUEVO** HTML original del Blogspot
- `tono` - Tono principal detectado
- `fuente`

### Canciones Extraídas (9)
| # | Canción | Tono |
|---|---------|------|
| 1 | CANCIONERO CCE MONTEQUINTO | LA |
| 2 | A TU AMPARO Y PROTECCIÓN | Do |
| 3 | AQUÍ ESTOY, SEÑOR (SALMO 39) | Sol |
| 4 | CANTAD CON GOZO | RE |
| 5 | EL ESPÍRITU DEL SEÑOR, PENTECOSTÉS (KAIROI) | G |
| 6 | HOY COMO AYER | C |
| 7 | MARÍA, MÚSICA DE DIOS | DO |
| 8 | PREPARAD EL CAMINO | SOL |
| 9 | GLORIA TE DAMOS GRACIAS, SEÑOR (R. CARISMÁTICA) | A |

### Parser de Acordes (V2 con Posicionamiento)
**Archivo:** `src/parsers/acordes_parser_v2.py`

**Características:**
- Detecta acordes en notación española (Do, Re, Sol) e inglesa (C, D, G)
- Maneja mayúsculas y minúsculas (SOL, Sol, lam, Lam)
- Guarda posición exacta de cada acorde sobre la letra
- Genera HTML visual con acordes posicionados
- Soporta tres tipos de líneas:
  - `letra` - Solo texto
  - `acordes` - Solo acordes
  - `mixta` - Acordes sobre letra

**Ejemplo de estructura JSON:**
```json
{
  "tipo": "acordes",
  "acordes": [
    {"acorde": "SOL", "posicion": 0},
    {"acorde": "Lam", "posicion": 6},
    {"acorde": "Sim", "posicion": 17}
  ]
}
```

### Scraper Blogspot
**Archivo:** `src/scrapers/blogspot_scraper.py`

**Funcionalidad:**
- Extrae canciones de https://ccem5music.blogspot.com/p/cancionero-escolapio.html
- Guarda en SQLite con formato posicionado
- Mantiene HTML original como backup
- Pausa entre requests (1 segundo)

### GitHub Repository
**URL:** https://github.com/CC5M5/CCE-M5
**Token:** Guardado en variable de entorno `GITHUB_TOKEN_CC5M5` (configurado en `.env`)
**Commits realizados:**
- `484aa4d` - Fase 0: Fundacion
- `ffa9c8e` - Fase 1: Scraper completo del cancionero
- `704ceaa` - Fix: Parser de acordes corregido
- `19fb5a8` - Feat: Parser con posicionamiento de acordes
- `7120d60` - Docs: Actualizar MEMORY.md y spec 07-cancionero
- `4c091d9` - Fase 2: Scraper Koinonia, matching engine y generador PPTX 16:9

### Configuración Git
**Remote:** `https://github.com/CC5M5/CCE-M5.git`
**Helper de credenciales:** Configurado para usar token desde variable de entorno
**Script de push:** `/tmp/push_github.sh` (usado temporalmente)

### Cronograma
8 semanas:
1. ✅ **Semana 1: Fundación** - Specs, DB, repo, MC
2. ✅ **Semana 2: Scraping + Seed** - 9 canciones extraídas con parser posicionado
3. ✅ **Semana 3-4: Matching + PPTX** - Scraper Koinonia (con mock), motor de matching, generador PPTX 16:9
4. **Semana 5-6: Web + Deploy** - Astro, GitHub Pages
5. **Semana 7: Integración** - Flujo end-to-end
6. **Semana 8: Refinamiento** - Optimizaciones

### Usuario Principal
**Rafa** - Responsable musical CCE Montequinto. Valida lecturas, elige canciones, aprueba comentarios.

### Notas Importantes
- **Formato PPTX:** Usar SIEMPRE `274 Domingo 21 06 2026.pptx` (16:9), nunca el MASTER (4:3)
- **Token GitHub:** Token clásico (`classic`) con permisos `repo` completos (lectura y escritura de contenidos).
- **Mission Control:** Ya instalado en http://192.168.68.244:4000/
- **Posicionamiento de acordes:** Es CRÍTICO para la vista de músicos. Los acordes deben aparecer exactamente encima de la sílaba/letra correspondiente.

### OpenCode Configurado ✅
**Estado:** Funcionando con Kimi-k2.7-code:cloud via Ollama
**Comando:** `opencode run -m ollama/kimi-k2.7-code:cloud "prompt"`
**Context7 MCP:** Instalado y funcionando (mcporter)

**Ejemplo aplicado:**
- Revisión completa del scraper de Blogspot con Context7
- Identificación de 10+ problemas de seguridad y rendimiento
- Mejoras aplicadas: reintentos, validación, logging, manejo seguro de BD

### Commits Recientes (Sesión 12 Sep 2026)
- `127ef1d` - Refactor: Corregir db_manager y blogspot_scraper con OpenCode+Context7
- `60b275f` - Fix: Parser de acordes v3 con posicionamiento exacto y sin falsos positivos
- `0a35bff` - Refactor: Aplicar correcciones OpenCode+Context7 a matching, PPTX y Koinonia
- `1d3199d` - Docs: Actualizar MEMORY.md con progreso completo de revisión OpenCode+Context7
- `1d5031d` - Mejoras aplicadas por OpenCode + Kimi: scraper robusto con reintentos, validación y logging
- `5fddd97` - Mejoras manuales: koinonia scraper, matching engine, generador PPTX
- `c235f57` - Fix: Mejoras críticas de seguridad y rendimiento de OpenCode+Context7

### Parser de Acordes V3 (corregido)
**Archivo:** `src/parsers/acordes_parser_v3.py`

**Correcciones críticas:**
- Ya no detecta "LA" en "ESCUCHAD LA PALABRA" como acorde
- Empareja líneas de acordes con la siguiente línea de letra
- Preserva el texto de la letra sin modificarlo
- Soporta bemoles, sostenidos dobles, extensiones y slash chords
- HTML monoespaciado con spans posicionados en `ch`
- Limpia etiquetas HTML y metadatos del blogspot (`escuchar`, `volver a lista`, `Version en`, `/`)
- Normaliza NBSP y espacios múltiples
- 4 tests incluidos, todos pasan

**Archivos relacionados:**
- `docs/auditoria_parser_acordes.md` - Informe completo de auditoría
- `web/cancion_preview.html` - Preview visual

### Mejoras de Seguridad Aplicadas (OpenCode + Context7)

#### Scraper Blogspot (blogspot_scraper.py)
- ✅ Añadido `import time` (bug crítico)
- ✅ Validación estricta de scheme `https`
- ✅ Normalización de URLs (decode, lowercase netloc)
- ✅ Bug corregido: `cancion.get('titulo_url')` → `cancion.get('url')`
- ✅ Crea tabla `canciones` si no existe
- ✅ Manejo de excepciones alrededor del parser
- ✅ Import del parser al inicio
- ✅ Context manager `__enter__`/`__exit__`
- ✅ Conexión SQLite persistente + inserciones en batch (`executemany`)
- ✅ Límite de tamaño de respuesta (10 MB)
- ✅ Progreso guardado en `data/scraper_progress.json` para reanudar
- ✅ Usa `acordes_parser_v3` (posicionamiento correcto)

#### Gestor de Base de Datos (db_manager.py)
- ✅ Variable de entorno `CCE_PROJECT_DIR` con fallback
- ✅ PRAGMAs: `journal_mode=WAL`, `foreign_keys=ON`, `synchronous=NORMAL`, `trusted_schema=OFF`
- ✅ `PRAGMA integrity_check` al conectar
- ✅ `create_connection()` con `row_factory=sqlite3.Row`, `timeout=30`, `isolation_level=DEFERRED`
- ✅ Tabla `schema_version` para migraciones
- ✅ Migración automática: añade columna `celebracion` a `lecturas` si falta
- ✅ Índices faltantes en FK y campos de búsqueda
- ✅ Logging en lugar de print
- ✅ Carga `data/schema.sql` si existe

#### Motor de Matching (matching_engine.py)
- ✅ Arquitectura separada: `TextPreprocessor`, `ThemeExtractor`, `ScoreNormalizer`, `MatchRepository`, `MatchingService`
- ✅ Tokenización con palabras completas (evita "amor" en "amoroso")
- ✅ Score normalizado al rango [0, 1]
- ✅ Afinidad momento litúrgico - tema (boost configurable)
- ✅ Caché de vectores lectura/canción
- ✅ Validación de inputs

#### Generador PPTX (presentacion_fieles.py)
- ✅ Carga template real `274_Domingo_21_06_2026.pptx`
- ✅ Bug corregido: `letra_limpia` ya no usa `texto` por error
- ✅ Bug corregido: acceso a `RGBColor` por índice (no `.r`/`.g`/`.b`)
- ✅ Letra de canciones en PPTX limpia de metadatos del blogspot
- ✅ Color de fondo configurable con contraste automático de texto
- ✅ Sanitización de nombres de archivo y texto XML
- ✅ `sqlite3.Row` para acceso por nombre
- ✅ Precarga de canciones con un solo query `IN(...)`
- ✅ Fuente y márgenes consistentes
- ✅ Manejo de errores específico

#### Scraper Koinonia (koinonia_scraper.py)
- ✅ Validación regex de fecha `YYYYMMDD`
- ✅ Separación: `KoinoniaClient`, `KoinoniaParser`, `KoinoniaRepository`
- ✅ Caché HTTP con `requests-cache` TTL 12h
- ✅ Selectores CSS con `find_next_sibling`
- ✅ Cita bíblica extraída con regex del título
- ✅ Zona horaria `Europe/Madrid`
- ✅ Validación de lecturas completas

### Scripts de Demo
- `scripts/demo_blogspot.py` - Demo del scraper de Blogspot
- `scripts/demo_koinonia.py` - Demo del scraper de Koinonia
- `scripts/demo_matching.py` - Demo del motor de matching
- `scripts/init_db.py` - Inicialización de base de datos
- `src/generators/demo_presentacion.py` - Demo del generador PPTX

### Estado Actual del Proyecto (Post-revisión OpenCode)

| Componente | Estado | Notas |
|-----------|--------|-------|
| Scraper Blogspot | ✅ Mejorado | Bugs críticos corregidos, usa parser v3 |
| Scraper Koinonia | ✅ Mejorado | Arquitectura separada, caché, validación |
| Parser Acordes V2 | ✅ Reemplazado por V3 | Posicionamiento exacto, tests pasan |
| Motor Matching | ✅ Mejorado | Scoring 0-1, tokenización robusta |
| Generador PPTX | ✅ Mejorado | Template real, bugs corregidos |
| db_manager | ✅ Mejorado | PRAGMAs, migraciones, índices |
| OpenCode | ✅ Configurado | Kimi-k2.7-code:cloud via Ollama |
| Context7 MCP | ✅ Instalado | mcporter configurado |

### Fase 3-4: Web + Deploy ✅
**Estado:** Proyecto web creado y funcionando en build local

**Stack:** Astro 4.x + Tailwind CSS + React islands + better-sqlite3

**Estructura en `web/`:**
- `package.json`, `astro.config.mjs`, `tailwind.config.mjs`
- `src/pages/` con todas las rutas del spec 06-web
- `src/components/` React: BuscadorCanciones, FiltroMomentos, VisorAcordes, FormularioComentarios
- `src/lib/db.js` - lectura de SQLite en build time
- `src/layouts/Layout.astro` - layout base con navegación y SEO
- `src/styles/global.css` - tokens de colores litúrgicos y fuentes
- `.github/workflows/deploy.yml` - despliegue en GitHub Pages

**Build verificado:**
```bash
BASE_PATH=/ SITE_URL=http://localhost npm run build
# Resultado: 15 páginas generadas, sitemap creado
```

**Skills de OpenCode instaladas:**
- `.opencode/skills/` desde `farmage/opencode-skills` (66 skills)
- Usadas para revisión: `code-reviewer`, `react-expert`, `typescript-pro`

**Correcciones tras revisión con skills:**
- `comentarios.astro`: etiqueta `</blockquote>` cerrada correctamente
- `VisorAcordes.jsx`: sanitización robusta con parser DOM + whitelist
- `FormularioComentarios.jsx`: validación de inputs, maxLength, escape de datos

**Commits de la fase:**
- `7258866` - Feat: Fase 3-4 - Proyecto web Astro + Tailwind + GitHub Pages
- `29c26ac` - Fix: Correcciones criticas tras revision OpenCode con skills
- `f9b0a48` - Chore: Instalar skills de OpenCode (farmage/opencode-skills) para revisiones

### Fase 5: Integración End-to-End ✅
**Estado:** Completada

**Archivo principal:** `scripts/generar_semana.py`

**Flujo automatizado para cada domingo (`--fecha YYYY-MM-DD`):**
1. Obtiene lecturas de Koinonia (con cache y timeout; fallback a mock si falla la red).
2. Permite asignación manual de canciones vía `--config config.json`.
3. Si no hay config manual, usa `src.matching_engine` para proponer canciones para los 12 momentos; con fallback a una asignación por defecto basada en las canciones disponibles.
4. Genera PPTX para fieles: `presentaciones/YYYY-MM-DD_celebracion.pptx`.
5. Genera PDF para músicos: `presentaciones/YYYY-MM-DD_hoja_musicos.pdf`.
6. Registra la presentación en la tabla `presentaciones` de SQLite con fecha, rutas, canciones_json, lectura_json y notas.

**Prueba realizada:**
```bash
python scripts/generar_semana.py --fecha 2026-09-13
```
- Lectura ID: 3
- Presentación ID: 6
- PPTX generado: `presentaciones/2026-09-13_celebracion.pptx`
- PDF generado: `presentaciones/2026-09-13_hoja_musicos.pdf` (10 páginas)
- 12 momentos litúrgicos con canciones asignadas.

**Notas:**
- ✅ Error `'RGBColor' object has no attribute 'r'` corregido en `presentacion_fieles.py` (RGBColor se accede por índice, no por `.r`/`.g`/`.b`).
- ✅ Letra de las canciones en el PPTX ahora se limpia con `limpiar_texto_cancion`: no aparecen "escuchar" (como metadato), "volver a lista" ni "Version en".
- ✅ `limpiar_texto_cancion` ahora normaliza NBSP y espacios múltiples, y filtra variantes de las líneas de metadatos del blogspot.
- ✅ `src/db_manager.py` crea la columna `celebracion` en `lecturas` y migra tablas existentes automáticamente.
- El generador PPTX principal produce presentaciones completas (126 diapositivas con template real).
- Se corrigió import faltante `os` en `src/matching_engine.py`.

### Servidor Web Local Permanente ✅
**Estado:** Servicio systemd `cce-m5-web.service` instalado y funcionando

**IP del servidor:** `192.168.68.244`
**Puerto:** `4321`
**URL de acceso desde la red local:** http://192.168.68.244:4321/

**Características del servicio:**
- Se inicia automáticamente al arrancar el PC
- Reconstruye la web con `npm run build` antes de servir
- Sirve desde `web/dist/` en `0.0.0.0:4321`
- Se reinicia automáticamente si falla

**Comando de instalación usado:**
```bash
sudo bash /tmp/install_cce_m5_web_service.sh
```

**Archivos del servicio:**
- `/etc/systemd/system/cce-m5-web.service`
- `/tmp/install_cce_m5_web_service.sh`
- `/tmp/cce-m5-web.service`

**Comandos útiles:**
```bash
sudo systemctl status cce-m5-web.service   # Ver estado
sudo systemctl restart cce-m5-web.service  # Reiniciar
sudo systemctl stop cce-m5-web.service     # Detener
sudo systemctl disable cce-m5-web.service  # Deshabilitar inicio automático
```

### Estado Actual del Proyecto

| Componente | Estado | Notas |
|-----------|--------|-------|
| Scraper Blogspot | ✅ Mejorado | Bugs críticos corregidos, usa parser v3 |
| Scraper Koinonia | ✅ Mejorado | Arquitectura separada, caché, validación |
| Parser Acordes | ✅ V3 estable | Posicionamiento exacto, tests pasan |
| Motor Matching | ✅ Mejorado | Scoring 0-1, tokenización robusta |
| Generador PPTX | ✅ Mejorado | Template real, bugs corregidos |
| db_manager | ✅ Mejorado | PRAGMAs, migraciones, índices |
| Web Astro | ✅ Funcionando | Build local OK, 15 páginas generadas |
| Servidor web local | ✅ Permanente | systemd, accesible en red local |
| Generador PDF músicos | ✅ Integrado | 10 páginas, sin ruido HTML |
| Skills OpenCode | ✅ Instaladas | farmage/opencode-skills en `.opencode/` |
| OpenCode | ✅ Configurado | Kimi-k2.7-code:cloud via Ollama |
| Context7 MCP | ✅ Instalado | mcporter configurado |
| Integración end-to-end | ✅ Funcionando | `scripts/generar_semana.py` genera PPTX/PDF y registra en DB |

### Correcciones Web del Cancionero (2026-09-14)
**Commits:** `5555777`, `f979eea`, `2c82cca`

**Problemas detectados y corregidos:**
1. **Spam de metadatos** - Eliminado "escuchar", "/", "volver a lista de canciones" del HTML visual.
2. **Toggle sin/con acordes** - Reimplementado con Astro + JS vanilla (antes React con hidratación problemática).
3. **Posición del tono** - Badge "Tono: X" junto al botón toggle; se oculta automáticamente al quitar acordes.
4. **Botón "Audio no disponible"** - Visible cuando `enlace_audio` es NULL.
5. **Botón "Volver al cancionero"** - Enlace funcional a `/cancionero/`.
6. **Alineación acordes-letra** - `white-space: nowrap` en `.linea-acordes` para que los acordes se muestren horizontalmente sobre la letra.
7. **Título repetido** - Eliminado `<div class="letra-solo">TÍTULO</div>` del inicio del HTML visual; la canción empieza directamente con los acordes.

**Cambios técnicos:**
- `web/src/components/VisorAcordes.astro`: componente puro Astro reemplazando al React `.jsx`
- `web/src/styles/global.css`: limpiado CSS duplicado, añadido `white-space: nowrap`, eliminado `white-space: pre` del contenedor
- `web/tailwind.config.mjs`: safelist para clases de acordes
- Parser v3: todas las canciones usan el mismo formato automáticamente

**Nota:** El formato se aplica a TODAS las canciones automáticamente porque el componente `VisorAcordes.astro` es compartido por todas las páginas de canción.

8. **Página /musicos/ con formato** — Creado `musicos/index.astro` con listado de hojas de músicos disponibles, evitando el listado de directorio del servidor Python.
9. **Página /presentacion/ con formato** — Creado `presentacion/index.astro` con listado de presentaciones disponibles, evitando el listado de directorio del servidor Python.
10. **Fuente de lecturas visible** — Añadida atribución "Fuente: Ciudad Redonda" o "Fuente: Koinonia" al final de la página de lecturas, con enlace a la web origen.
11. **Enlace Presentación en navegación** — Añadido "Presentación" al menú de navegación del header (entre Inicio y Cancionero).
12. **Descarga de archivos PPTX/PDF** — Copia de archivos desde `presentaciones/` a `web/dist/presentaciones/` tras cada build para que `python -m http.server` pueda servirlos.

**Cambios técnicos adicionales:**
- `web/src/layouts/Layout.astro`: navLinks actualizado con Presentación
- `web/src/lib/db.js`: `getPresentacionByFecha` ahora incluye `fuente_scraping` de la tabla lecturas
- `web/src/pages/lecturas/[fecha].astro`: muestra fuente_scraping con enlace a ciudadredonda.org o servicioskoinonia.org
- Nuevos archivos: `web/src/pages/musicos/index.astro`, `web/src/pages/presentacion/index.astro`

### Transposición de Tono (2026-09-14)
**Commits:** `96e4c23`, `f2bd386`

**Funcionalidad añadida:**
- Controles en dos filas: fila 1 (toggle, audio, volver) + fila 2 (tono, transposición)
- Botones `+` / `−` suben/bajan un semitono todos los acordes de la canción
- Badge "Tono: X" se actualiza dinámicamente reflejando el desplazamiento
- Botón "Original" resetea al tono inicial (`semitonos = 0`)
- Guardado de valores originales en `data-acorde-original` y `data-acordes-original` para poder resetear

**Correcciones de la transposición:**
1. **Notas de 3 letras (Sol)** — El patrón regex `([A-Za-z][a-z]?)` solo capturaba 2 letras, fallando con "Sol". Reemplazado por búsqueda por prefijo ordenado por longitud descendente.
2. **Acordes sueltos (linea-acordes-suelta)** — Las líneas como "Sol La Re" no estaban en spans individuales; ahora también se transponen dividiendo por espacios.
3. **Notas menores (Sim, Lam)** — El sufijo "m" de menor se preserva correctamente al transponer (Sim → Do#m, Lam → Si#m).

**Implementación técnica:**
- Array cromático español: `['Do','Do#','Re','Re#','Mi','Fa','Fa#','Sol','Sol#','La','La#','Si']`
- Función `transponerAcorde(token, delta)` busca la nota base más larga que coincida al inicio del token
- Soporte para alteraciones (#, b) y extensiones (m, 7, maj7, sus4, dim, aug, add9, slash chords)
- El componente sigue siendo puro Astro (sin React) para evitar problemas de hidratación


13. **Lema del curso en presentaciones** — Añadido `LEMA_CURSO = "Somos uno"` en `src/generators/presentacion_fieles.py`; método `_crear_footer_lema` añade el lema en la parte inferior de cada diapositiva generada (portada, lecturas, canciones). URL de referencia: `https://escolappios.es/somos-uno-lema-del-curso-26-27/`
14. **Título limpio de Ciudad Redonda** — El scraper elimina el prefijo "Evangelio y Lecturas de" al guardar `celebracion`, dejando solo "XXV Domingo del Tiempo Ordinario".
15. **Presentación 2026-09-20 regenerada** — PPTX y PDF de músicos actualizados con lema correcto y lecturas de Ciudad Redonda (Is 55,6-9; Sal 144; Fil 1,20c-24.27a; Mt 20,1-16). Portada: "Evangelio y Lecturas de XXV Domingo del Tiempo Ordinario".

**Nota técnica:** La plantilla PPTX base (`data/templates/274_Domingo_21_06_2026.pptx`) contiene 109 diapositivas preexistentes del cancionero. El generador añade diapositivas al final, resultando en ~126 slides. Para futuro, considerar usar una plantilla vacía o limpiar la base antes de generar.


16. **Plantilla PPTX limpia** — El generador ahora elimina todas las slides existentes de la plantilla antes de generar (`_limpiar_slides_existentes`). La presentación del 20 de septiembre tiene 17 slides en vez de 126.
17. **Imagen del lema en plantilla** — `image2.jpeg` en la plantilla reemplazada por el logo "Somos uno" (rojo, cruz + texto). Descargado desde `https://www.escolapiosbetania.org/Catalogo/Item/1984_Item/somos-uno-lema-del-curso-26-27.jpg`.
18. **Logo del lema en diapositivas** — Método `_crear_logo_lema` añade el texto del lema en la esquina inferior izquierda (rojo escolapio). Para futuro: implementar como imagen real usando `slide.shapes.add_picture()`.

**Nota para cambio anual de lema:**
Para cambiar el lema en años futivos (ej. 2027-28):
1. Reemplazar `LEMA_CURSO` en `src/generators/presentacion_fieles.py`
2. Reemplazar `image2.jpeg` en `data/templates/274_Domingo_21_06_2026.pptx` con la nueva imagen
3. Opcionalmente, actualizar `URL_LEMA_CURSO` con el enlace del nuevo lema



## Sesión 2026-09-14 - Trabajo realizado

### Correcciones completadas

19. **Plantilla PPTX recuperada** — Descargada `MASTER_PowerPoint Eucaristía.pptx` (40MB, 121 slides) del NAS (`192.168.1.177/homes/Rafa/Escolapios/11 Presentaciones PPT CCE M5/`). Contiene estilo artístico completo con imágenes de canciones, menús y transiciones.

20. **Imagen lema "Somos uno" descargada** — Obtenida desde `https://www.escolapiosbetania.org/Catalogo/Item/1984_Item/somos-uno-lema-del-curso-26-27.jpg`. Guardada en `data/lemas/somos_uno.jpg`. Reemplazó temporalmente `image2.jpeg` en plantilla.

21. **Configuración lema anual** — Creado `config/lema.py` con variables centralizadas: `LEMA_CURSO`, `URL_LEMA_CURSO`, `IMAGEN_LEMA_PATH`. Facilita cambio anual.

22. **Generador `presentacion_master.py` creado** — Nuevo generador que copia slides específicas desde plantilla MASTER según canciones asignadas. Mapeo completo de ~100 canciones a slides. Método `_rebuild_pptx` reconstruye PPTX manteniendo solo slides seleccionadas.

23. **Integración en `generar_semana.py`** — Generador principal ahora usa `GeneradorPPTXMaster` en lugar del generador antiguo.

### Problemas identificados

- **PPTX generado tiene demasiadas slides** (134 en vez de ~15-20). El método `_rebuild_pptx` no elimina correctamente las slides no usadas del XML de presentación.
- **Slides de lecturas no implementadas** — Falta crear diapositivas de Primera Lectura, Salmo, Segunda Lectura y Evangelio con el estilo artístico de la plantilla.
- **Esquema completo no implementado** — Faltan diapositivas de transición, portada, credo, y orden correcto según esquema litúrgico.
- **Lema "Somos uno" no aparece en slides** — Solo se añadió como texto en generador anterior (ya descartado), no en el nuevo `presentacion_master.py`.
- **Matching de canciones asigna todas "PREPARAD EL CAMINO"** — El motor de matching no funciona correctamente con las 9 canciones actuales. Necesita más canciones o lógica de fallback mejorada.



### Actualización 2026-09-14 (continuación)

24. **Generador `presentacion_master.py` COMPLETADO** — 4 de 6 pasos implementados:
    - ✅ Paso 1: `_rebuild_pptx` corregido (elimina slides correctamente)
    - ✅ Paso 2: Slides de lecturas con estilo (fondo color litúrgico, tipografía Calibri)
    - ✅ Paso 3: Esquema completo (portada, transiciones, lecturas, canciones)
    - ✅ Paso 4: Lema "Somos uno" como imagen en esquina inferior de slides nuevas
    - ✅ Paso 5: Matching arreglado (usa `DEFAULT_ASIGNACION` cuando hay <20 canciones)
    - ❌ Paso 6: Migrar más canciones desde Blogspot (pendiente)

25. **Matching de canciones corregido (v1)** — `proponer_canciones_matching` ahora detecta cuando hay menos de 20 canciones y usa `DEFAULT_ASIGNACION` directamente, evitando que todas las canciones sean "PREPARAD EL CAMINO". Esta corrección fue mejorada más tarde el mismo día (punto 48).

26. **Presentación 2026-09-20 regenerada con éxito** — Con `presentacion_master.py`: 10 slides (menú + Preparad el Camino + 4 lecturas + 3 transiciones + portada). PPTX de 6.8MB servido en web. Más tarde se regeneró con `presentacion_html.py` (punto 49).



### Actualización 2026-09-15 (mañana)

27. **Nuevo enfoque de presentaciones aprobado** — Se descarta el uso de la plantilla MASTER PPTX. El generador `presentacion_html.py` crea un formato intermedio JSON + HTML + PPTX con estilo propio.

28. **Estilo visual "liturgia" aprobado** — Tipografía Fredoka/Nunito, colores púrpura/dorado, tarjetas redondeadas, barra decorativa superior, ilustraciones de Fano/Pati.te/Sara BG en esquina inferior derecha (uso pastoral no comercial). URLs de prueba:
    - HTML/web: http://192.168.68.244:4321/presentacion/2026-09-20/
    - PPTX descargable: http://192.168.68.244:4321/presentaciones_html/2026-09-20_presentacion/2026-09-20_presentacion.pptx
    - PDF: http://192.168.68.244:4321/presentaciones_html/2026-09-20_presentacion/2026-09-20_presentacion.pdf

29. **PPTX/HTML mejorado con estilo visual** — Tarjetas redondeadas, colores púrpura/dorado, imágenes grandes sin tapar texto, lema "Somos uno" como imagen en esquina inferior izquierda en HTML y PPTX. No se usa directamente `pptx-designer`; se usan sus tokens de color como inspiración.

30. **Paginación automática** — Textos largos (lecturas, evangelio) se dividen en varias slides si exceden el espacio.

31. **Credo completo** — Versión corta del Credo apostólico escrita entera.

32. **Interlineado de canciones reducido** — Líneas más compactas, párrafos intermedios eliminados.

33. **Playwright instalado** — Generación automática de PDF desde el HTML.

34. **Ilustraciones reales integradas**:
    - Fano: descargados 10 dibujos desde https://diocesismalaga.es/dibujos-fano
    - Pati.te: láminas de la Virgen de Fátima desde https://www.patite.es/
    - Sara BG: ilustración religiosa desde https://sarabg.com/

35. **Canciones: política actual** — Por ahora, canciones solo en Entrada, Salmo, Ofertorio, Comunión y Despedida. Los demás momentos usan textos litúrgicos fijos. En el futuro, cuando haya más canciones importadas, se asignarán también a Perdón, Gloria, Aleluya, Santo, Padre Nuestro, Paz y Canto a María.

36. **Commits de la sesión**:
    - `21614ed`: generador presentacion_html con ilustraciones, paginación, PDF y web
    - `ae03033`: mejora PPTX con estilo litúrgico visual

### Actualización 2026-09-15 (mediodía - scraper cancionero)

37. **Scraper del cancionero reparado** — `blogspot_scraper.py` era incompatible con `acordes_parser_v3` (devuelve objetos `LineaCancion`, no diccionarios; eliminó `detectar_momento_liturgico`). Se actualizó para:
    - Leer atributos del dataclass (`linea.tipo`, `linea.letra`, `linea.texto`).
    - Convertir estructura a JSON serializable.
    - Detectar momento litúrgico con función propia del scraper basada en palabras clave.

38. **Scraper ejecutado con éxito** — 8/8 canciones del blogspot procesadas correctamente, 0 fallidas.

39. **Límite real identificado** — El blog `ccem5music.blogspot.com` solo publica 8 canciones en su índice. Para ampliar el cancionero hará falta otra fuente (blog de Escolapios Betania, cancionero manual, etc.) o importación manual.

40. **Commit:** `4e3772c` — fix: blogspot_scraper compatible con acordes_parser_v3 y detección momento litúrgico.

### Actualización 2026-09-15 (tarde)

41. **Importación completa del cancionero Betania** — Se añadieron 98 canciones desde `https://betaniamusic.blogspot.com/2018/07/cancionero-escolapio.html`. Total en BD: 107 canciones.

42. **Preprocesador Betania robusto** — El scraper ahora soporta múltiples formatos de publicación:
    - Posts con URL `/YYYY/MM/slug.html` (no solo `/p/`).
    - Acordes en spans de color rojo (`#c00000`) dentro de `<div>`, `<p>` o `<h1>`.
    - Acordes pegados (`LamSol`, `DoFaDo`) separados automáticamente.
    - Deduplicación de líneas causada por anidación de etiquetas.

43. **Dos canciones problemáticas recuperadas**:
    - `PADRE NUESTRO (Simon y Garfunquel)` → ID 73, tono Lam, momento ofertorio.
    - `QUÉ TE PUEDO DAR` → ID 82, tono La, momento general.

44. **Web Admin descartado** — El usuario prefiere editar los momentos litúrgicos manualmente.

45. **Presentación 2026-09-20 regenerada con cancionero ampliado** — 21 slides, con asignación automática por matching:
    - Entrada: PREPARAD EL CAMINO
    - Perdón: OTRA OPORTUNIDAD
    - Gloria: EL ESPÍRITU DEL SEÑOR, PENTECOSTÉS
    - Salmo: AQUÍ ESTOY, SEÑOR (SALMO 39)
    - Aleluya: JESÚS RESUCITA HOY
    - Ofertorio: PADRE NUESTRO DE LA VIDA
    - Santo: QUIERO HACER LO MISMO
    - Padre Nuestro: PADRE NUESTRO (Gallego)
    - Paz: UNA NUEVA ESPERANZA
    - Comunión: ORACIÓN DEL POBRE
    - Canto a María: BENDIGAMOS AL SEÑOR
    - Despedida: VEN JESÚS

46. **Commits de la sesión:**
    - `92b4ab7`: scraper Betania soporta h1, acordes pegados y spans rojos; importadas 98 canciones más

### Actualización 2026-09-15 (tarde - correcciones web y matching)

47. **Corrección de slugs del cancionero con tildes** — Las páginas de canciones con caracteres especiales no se generaban correctamente (p. ej. `a-tu-amparo-y-proteccin` en el listado apuntaba a una carpeta distinta de la que Astro creaba). Se centralizó la generación de slugs en `web/src/lib/slug.js` usando normalización Unicode NFD, eliminación de diacríticos, minúsculas y limpieza de caracteres no alfanuméricos. Se actualizaron `web/src/lib/db.js`, `web/src/pages/cancionero/[slug].astro`, `web/src/pages/cancionero/index.astro` e `index.astro` para usar el helper común. La URL de ejemplo `http://192.168.68.244:4321/cancionero/a-tu-amparo-y-proteccion/` ahora funciona.

48. **Corrección del matching de canciones (v2)** — `scripts/generar_semana.py` asignaba la misma canción (`PREPARAD EL CAMINO`) a todos los momentos porque `proponer_canciones_matching` elegía siempre el primer resultado del ranking global. Se reescribió para:
    - Pedir un ranking ampliado (10× candidatos).
    - Priorizar canciones cuyo `momento_liturgico` coincida exactamente con el momento solicitado.
    - Probar coincidencia parcial y título antes de recurrir al fallback.
    - Usar `DEFAULT_ASIGNACION` como fallback en lugar de la canción genérica top-1.

49. **Regeneración de la presentación 2026-09-20 con `presentacion_html.py`** — No existía fila en `presentaciones`; se generó de nuevo con lecturas de Ciudad Redonda (Koinonia caído) y matching corregido. El generador produce portada como slide 1 e incluye el logo del lema "Somos uno" en esquina inferior izquierda de todas las slides, tanto en HTML como en PPTX. Asignación final:
    - Entrada: PREPARAD EL CAMINO
    - Perdón: OTRA OPORTUNIDAD
    - Gloria: EL ESPÍRITU DEL SEÑOR, PENTECOSTÉS
    - Salmo: AQUÍ ESTOY, SEÑOR (SALMO 39)
    - Aleluya: JESÚS RESUCITA HOY
    - Ofertorio: PADRE NUESTRO DE LA VIDA
    - Santo: QUIERO HACER LO MISMO
    - Padre Nuestro: PADRE NUESTRO (Gallego)
    - Paz: UNA NUEVA ESPERANZA
    - Comunión: MARÍA, MÚSICA DE DIOS
    - Canto a María: MARÍA, MÚSICA DE DIOS
    - Despedida: PREPARAD EL CAMINO

50. **HTML/PPTX/PDF de la presentación regenerados** — Se ejecutó `src/generators/presentacion_html.py` para actualizar `presentaciones_html/2026-09-20_presentacion/` con JSON, HTML, PPTX y PDF. Luego se hizo `npm run build` en `web/` para servir la web actualizada.

51. **Commits de la sesión (tarde - correcciones):**
    - `be0f243`: fix(web): normaliza slugs del cancionero para tildes y caracteres especiales
    - `708f84d`: fix(generar): mejora matching por momento litúrgico y evita repetir misma canción

### Actualización 2026-09-15 (noche - pipeline Mission Control)

52. **Pipeline semanal automatizado con Mission Control** — Se creó en Mission Control:
    - Workspace `CCE-M5` (ID `908036db-88c7-451d-b758-fd57abfedeb6`, icono ⛪).
    - Agente `Capillita` importado desde OpenClaw gateway (`gateway_agent_id: capillita`), rol `Liturgical Pipeline Operator`, master del workspace.
    - Binding a Telegram (`accountId: 480498977`) para notificaciones.

53. **Timer systemd** — `cce-m5-pipeline.timer` dispara cada lunes a las 08:00 el script `/home/pciath/.openclaw/capillita/bin/cce-m5-weekly-trigger.sh`, que crea en Mission Control la tarea `Generar presentación semana YYYY-MM-DD` para el domingo siguiente, asignada a Capillita.

54. **Runbook de Capillita** — Escritos `SOUL.md`, `USER.md`, `MEMORY.md` e `IDENTITY.md` en `/home/pciath/.openclaw/capillita/` con las reglas del pipeline, verificaciones y limitaciones (no tocar Home Assistant, pedir confirmación antes de regenerar, reportar con tabla de checks).

55. **Tareas de prueba limpiadas** — Se borraron todas las tareas previas del workspace CCE-M5 antes de dejar el timer en producción.

56. **Próximo hito** — Lunes 21 de septiembre de 2026 a las 08:00: primera ejecución automática que creará la tarea para el domingo 27 de septiembre.

### Próximos pasos pendientes (actualizado)

1. **Validar ejecución automática del lunes 21 de septiembre** — Confirmar que el timer crea la tarea y Capillita ejecuta/ reporta el pipeline.
2. **Migrar más canciones** — Si es necesario, ampliar el cancionero más allá de las 107 canciones actuales.
3. **Configurar GitHub Pages** — Cuando se quiera desplegar fuera del servidor local.
4. **Tests del flujo end-to-end** — Automatizar smoke tests tras el deploy.

### Notas técnicas importantes

- La plantilla MASTER (`274_Domingo_21_06_2026.pptx`) tiene 121 slides con TODO el cancionero. Cada canción tiene su propia slide con imagen de fondo y letra.
- El generador antiguo (`presentacion_fieles.py`) fue descartado porque creaba slides de texto plano sin estilo.
- El nuevo generador (`presentacion_master.py`) copia slides XML desde la plantilla MASTER. Requiere manipulación de XML del PPTX (presentation.xml, rels, etc.).
- El lema cambia cada año. Para 2027-28: actualizar `config/lema.py` y reemplazar imagen en plantilla.
- El generador `presentacion_html.py` produce actualmente las presentaciones web (JSON + HTML + PPTX/PDF) con estilo propio, mientras `presentacion_master.py` queda como alternativa basada en plantilla PPTX.

**Pendiente:** Implementar `_crear_logo_lema` como imagen real (add_picture) en lugar de texto plano.

### Corrección de Acordes y Editor (2026-09-16)
**Estado:** En progreso

**Decisiones tomadas:**
- Se implementará un **editor web local** para ajustes manuales de acordes. Los cambios se guardan en SQLite y se commitean automáticamente al repo.
- GitHub Pages será **solo lectura**; la edición se hace en el servidor local.
- Se creará un **script de corrección masiva desde la web de origen** (`titulo_url`) que se ejecutará **una sola vez**, generará un informe comparativo para validación humana, y aplicará las correcciones validadas a la BD.
- Formato de edición: **texto libre con acordes posicionados** (igual que el almacenado en `letra_con_acordes`).

**Implementado:**
- `scripts/corregir_acordes_desde_origen.py` — Corrección masiva desde web de origen.
  - Descarga HTML original conservando espacios de posicionamiento.
  - Genera informe comparativo en `docs/correcciones_acordes/informe_acordes.html`.
  - Modo `--apply --ids N` regenera `html_visual`, `estructura_json`, `letra_sin_acordes`, `tono` y guarda en BD.
- `scripts/editor_acordes_server.py` — Editor web local en http://localhost:4322.
  - Listado de 107 canciones.
  - Editor con textarea + preview visual.
  - Botón "Guardar y commitear" actualiza BD y hace `git commit` + `git push`.
- Se instaló **Flask** en el entorno virtual.

**Pendiente:**
- Validar informe generado y aplicar correcciones masivas aprobadas.
- Reconstruir web Astro tras aplicar correcciones para reflejar cambios en cancionero.

### Próximos Pasos Pendientes
- [x] Corregir errores detectados en la web Astro (COMPLETADO)
- [x] Implementar scraper Ciudad Redonda como backup de Koinonia (COMPLETADO)
- [x] Corregir centrado vertical de slides en Reveal.js (COMPLETADO 2026-09-16)
- [x] Limpiar presentaciones duplicadas y del 27 de septiembre (COMPLETADO 2026-09-16)
- [ ] Fase 6: Refinamiento final
  - [ ] Configurar GitHub Pages en el repositorio remoto
  - [ ] Migrar todo el cancionero escolapio desde Blogspot (actualmente 107 canciones, parcialmente completo)
  - [ ] Mejorar calidad de los mocks de Koinonia y tests del flujo end-to-end
  - [ ] Sistema de corrección de acordes (edición local + commit automático)
  - [ ] Script de corrección masiva desde web de origen (una sola vez, validación humana)
  - [ ] Editor web local para ajustes manuales de acordes con commit automático
