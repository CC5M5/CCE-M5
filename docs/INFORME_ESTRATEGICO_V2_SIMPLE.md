# CCE-M5-Web-Presentaciones - Informe Estratégico V2.0

## Resumen Ejecutivo

Sistema automatizado para preparacion semanal de presentaciones liturgicas con cancionero escolapio, hoja para musicos con acordes, y web de publicacion. Arquitectura hibrida: Mission Control + OpenCode + OpenClaw.

## Correcciones Aplicadas

1. **Formato PPTX**: Corregido a usar ultimo por fecha (274 Domingo 21 06 2026, 16:9) en lugar del MASTER (4:3)
2. **Migracion cancionero completa**: No solo fuente, sino recrear toda la web
3. **Vista musicos con acordes**: Nueva pestana + PDF descargable
4. **Momentos liturgicos completos**: 12 momentos incluyendo Perdon, Salmo, Ofertorio
5. **Plazos acortados**: De 12 a 8 semanas

## Verificaciones Realizadas

### NAS: ACCESO CONFIRMADO
- **Ruta**: smb://192.168.1.177/homes/Rafa/Escolapios/11 Presentaciones PPT CCE M5/
- **Archivos**: 123+ archivos .pptx (2022-2026)
- **Plantilla MASTER**: MASTER_PowerPoint Eucaristia.pptx (39.6 MB, 121 diapositivas, 4:3)
- **Ultimo formato**: 274 Domingo 21 06 2026.pptx (16.6 MB, 109 diapositivas, 16:9)

### Analisis 274 Domingo 21 06 2026.pptx:
- **Dimensiones**: 13.33" x 7.50" (16:9 widescreen)
- **Diapositivas**: 109
- **Layouts**: 11 (espanol)
- **Estructura detectada**: Entrada → Perdon → Gloria → Aleluya → Ofertorio → Santo → Padre Nuestro → Paz → Comunion → Maria → Despedida

**DECISION**: Usar formato 16:9 del 274 como base, MASTER solo como referencia de canciones.

## Arquitectura Hibrida

```
Mission Control (crshdn) - Orquestador visual y pipeline automatico
    - Builder → Tester → Reviewer → Verifier
    - Convoy Mode: Multiples tareas en paralelo
    - Learner: Acumula lecciones aprendidas
    
OpenCode - Fuerza de desarrollo (codigo complejo)
    - Generador PPTX/PDF
    - Scraper y parser
    - Web (Astro)
    
OpenClaw - Comandante humano (validaciones)
    - Validacion semanal de lecturas
    - Seleccion de canciones
    - Moderacion comentarios
```

## Agentes Definidos

| Agente | Herramienta | Tarea |
|--------|-------------|-------|
| lector-liturgico | OpenClaw | Scraping Koinonia, lecturas |
| musico-liturgico | OpenClaw | Matching canciones-lecturas |
| presentador-fieles | OpenCode | PPTX sin acordes (16:9) |
| presentador-musicos | OpenCode | PDF con acordes |
| web-developer | OpenCode | Astro + GitHub Pages |
| catalogador-canciones | OpenCode | Scraper Blogspot + parser |
| moderador-comentarios | OpenClaw | Moderacion cada 6h |

## Momentos Liturgicos (12)

1. Entrada
2. Perdon (Acto penitencial)
3. Gloria
4. Salmo (Responsorial)
5. Aleluya (Aclamacion)
6. Ofertorio
7. Santo
8. Padre Nuestro
9. Paz
10. Comunion
11. Canto a Maria
12. Despedida

## Flujo Semanal Automatizado

Lunes 9:00
1. Scraper Koinonia → lecturas JSON
2. Usuario confirma lecturas
3. Matching tematico → propuestas canciones
4. Usuario elige canciones
5. Pregunta eventos especiales
6. OpenCode genera: PPTX fieles, PDF musicos, Web estatica
7. Despliegue GitHub Pages
8. Notificacion usuario

Cada 6h: Moderacion comentarios

## Cronograma: 8 Semanas

| Semana | Fase | Entregables |
|--------|------|-------------|
| 1 | Fundacion | Specs, DB, repo, MC configurado |
| 2 | Scraping + Seed | 50+ canciones, parser acordes |
| 3-4 | Matching + PPTX | Matching, PPTX 16:9, PDF musicos |
| 5-6 | Web + Deploy | Web completa, GitHub Pages |
| 7 | Integracion | Flujo end-to-end, tests |
| 8 | Refinamiento | Optimizaciones, documentacion |

## Nuevas Funcionalidades Clave

### 1. Migracion Cancionero Completo (Spec 08)
- Scraper de TODO el Blogspot ccem5music.blogspot.com
- 50+ canciones con acordes parseados
- Estructura JSON posicional para acordes
- Web navegable con busqueda y filtros

### 2. Vista para Musicos (Spec 09)
- Pestana /musicos/YYYY-MM-DD/ en web
- PDF descargable con acordes bien posicionados
- Una sola pagina/documento, sin navegacion
- Formato A4 vertical, legible a distancia
- Toggle mostrar/ocultar acordes en web

## Directorio del Proyecto

```
~/proyectos/CCE-M5-Web-Presentaciones/
├── .mission-control/       # Mission Control
├── .openclaw/              # Automatizaciones
├── specs/                  # 8 specs SDD
├── data/                   # Lecturas, canciones, DB
├── src/                    # Scrapers, parsers, generators
├── presentaciones/         # Output PPTX/PDF
├── web/                    # Astro site
├── docs/                   # Documentacion + ADRs
└── tests/                  # Tests unitarios/integracion
```

## Conclusion

Todas las correcciones solicitadas han sido aplicadas. El sistema esta disenado para ser escalable, automatizado y centrado en el flujo liturgico semanal. La integracion Mission Control + OpenCode + OpenClaw proporciona pipeline automatico con validacion humana en los puntos criticos.

**Aprobado para inicio.**
