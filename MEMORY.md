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

### Próximos Pasos Pendientes
- [x] Corregir errores detectados en la web Astro (COMPLETADO)
- [ ] Fase 6: Refinamiento final
  - [ ] Configurar GitHub Pages en el repositorio remoto
  - [ ] Migrar todo el cancionero escolapio desde Blogspot (actualmente solo 9 canciones)
  - [ ] Mejorar calidad de los mocks de Koinonia y tests del flujo end-to-end
