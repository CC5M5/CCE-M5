# MEMORY.md - Memoria de Largo Plazo

## Proyecto: CCE-M5-Web-Presentaciones

<!-- observed: 2026-09-12 | status: active | project: CCE-M5-Web-Presentaciones -->

### Resumen
Sistema automatizado para preparación semanal de presentaciones litúrgicas con cancionero escolapio, hoja para músicos con acordes, y web de publicación. Arquitectura híbrida: Mission Control + OpenCode + OpenClaw.

**Estado actual:** FASE 2 completada (Matching + PPTX). Generador de presentaciones 16:9 funcionando.

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
- **Token GitHub:** Usar fine-grained token con permisos `contents:read` y `contents:write`
- **Mission Control:** Ya instalado en http://192.168.68.244:4000/
- **Posicionamiento de acordes:** Es CRÍTICO para la vista de músicos. Los acordes deben aparecer exactamente encima de la sílaba/letra correspondiente.

### Nuevos Componentes (Fase 2)

#### Scraper Koinonia
**Archivos:**
- `src/scrapers/koinonia_scraper.py` - Scraper principal
- `src/scrapers/koinonia_mock.py` - Datos mock para desarrollo

**Estado:** Funcionando con mock. El sitio koinonia.org tiene timeouts frecuentes.

#### Motor de Matching
**Archivo:** `src/matching_engine.py`

**Funcionalidad:**
- Extrae temas de lecturas y canciones usando palabras clave
- Calcula score de matching basado en temas comunes
- Soporta temas: perdon, paz, esperanza, amor, camino, luz, agua, pan, maria, espiritu, alabanza, servicio, fe, salvacion

#### Generador PPTX
**Archivo:** `src/generators/presentacion_fieles.py`

**Características:**
- Formato 16:9 (13.333" x 7.5")
- Portada con color litúrgico
- Diapositivas de lecturas (Primera, Salmo, Segunda, Evangelio)
- Diapositivas de canciones (sin acordes)
- Fondos blancos para lecturas y canciones

**Estado:** ✅ Genera presentaciones de prueba correctamente
