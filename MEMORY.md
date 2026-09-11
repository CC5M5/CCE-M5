# MEMORY.md - Memoria de Largo Plazo

## Proyecto: CCE-M5-Web-Presentaciones

<!-- observed: 2026-09-08 | status: active | project: CCE-M5-Web-Presentaciones -->

### Resumen
Sistema automatizado para preparación semanal de presentaciones litúrgicas con cancionero escolapio, hoja para músicos con acordes, y web de publicación. Arquitectura híbrida: Mission Control + OpenCode + OpenClaw.

### Ubicación del Proyecto
`~/proyectos/CCE-M5-Web-Presentaciones/`

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
├── .mission-control/    # Mission Control config
├── .openclaw/           # Automatizaciones
├── specs/               # 8 specs SDD
├── data/                # Lecturas, canciones, DB
├── src/                 # Scrapers, parsers, generators
├── presentaciones/      # Output PPTX/PDF
├── web/                 # Astro site
├── docs/                # Documentación + ADRs
└── tests/               # Tests
```

### Stack Tecnológico
- **Orquestación**: Mission Control (crshdn)
- **Agentes desarrollo**: OpenCode
- **Agentes validación**: OpenClaw nativo
- **Base de datos**: SQLite → PostgreSQL
- **PPTX**: python-pptx
- **PDF**: ReportLab/WeasyPrint
- **Web**: Astro + Tailwind CSS
- **Hosting**: GitHub Pages
- **Comentarios**: GitHub Issues API

### Cronograma
8 semanas: Fundación → Scraping → Matching/PPTX → Web → Integración → Refinamiento

### Usuario Principal
**Rafa** - Responsable musical CCE Montequinto. Valida lecturas, elige canciones, aprueba comentarios.
