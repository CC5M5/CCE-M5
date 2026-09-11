# Spec 02: Arquitectura del Sistema

## Diagrama de Componentes

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         USUARIO (RAFA)                                    │
│                    OpenClaw (interfaz principal)                         │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    MISSION CONTROL (crshdn)                             │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐       │
│  │  INBOX  │→│ ASSIGNED │→│IN PROG. │→│ REVIEW  │→│  DONE   │       │
│  └─────────┘  └─────────┘  └─────────┘  └─────────┘  └─────────┘       │
│                                                                         │
│  Pipeline: Builder → Tester → Reviewer → Verifier                       │
│  Convoy Mode: Múltiples tareas en paralelo                              │
│  Learner: Acumula lecciones aprendidas                                  │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
            ┌───────────────────────┼───────────────────────┐
            │                       │                       │
            ▼                       ▼                       ▼
┌──────────────────┐    ┌──────────────────┐    ┌──────────────────┐
│   OPENCLAW         │    │   OPENCODE         │    │   OPENCLAW         │
│   NATIVO           │    │   (Desarrollo)     │    │   AUTOMATIZACIÓN   │
│                    │    │                    │    │                    │
│  ┌──────────────┐ │    │  ┌──────────────┐  │    │  ┌──────────────┐  │
│  │lector-       │ │    │  │presentador-  │  │    │  │moderador-    │  │
│  │liturgico     │ │    │  │fieles        │  │    │  │comentarios   │  │
│  └──────────────┘ │    │  └──────────────┘  │    │  └──────────────┘  │
│  ┌──────────────┐ │    │  ┌──────────────┐  │    └──────────────────┘
│  │musico-       │ │    │  │presentador-  │  │
│  │liturgico     │ │    │  │musicos       │  │
│  └──────────────┘ │    │  └──────────────┘  │
│                   │    │  ┌──────────────┐  │
│                   │    │  │web-developer │  │
│                   │    │  └──────────────┘  │
│                   │    │  ┌──────────────┐  │
│                   │    │  │catalogador-  │  │
│                   │    │  │canciones     │  │
│                   │    │  └──────────────┘  │
└──────────────────┘    └──────────────────┘
            │                       │
            └───────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         CAPA DE DATOS                                   │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                   │
│  │  SQLite/     │  │  Archivos    │  │  Cache       │                   │
│  │  PostgreSQL  │  │  (PPTX/PDF)  │  │  (JSON)      │                   │
│  │              │  │              │  │              │                   │
│  │  lecturas    │  │              │  │  lecturas    │                   │
│  │  canciones   │  │              │  │  canciones   │                   │
│  │  presentaciones│  │              │  │              │                   │
│  └──────────────┘  └──────────────┘  └──────────────┘                   │
└─────────────────────────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    CAPA WEB (GitHub Pages)                                │
│                                                                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                   │
│  │  Presentación│  │  Cancionero  │  │  Vista       │                   │
│  │  semanal     │  │  completo  │  │  Músicos     │                   │
│  │  (PPTX/PDF)  │  │  (todas las  │  │  (acordes)   │                   │
│  │              │  │  canciones)  │  │              │                   │
│  └──────────────┘  └──────────────┘  └──────────────┘                   │
│                                                                         │
│  Backend comentarios: GitHub Issues API                                 │
└─────────────────────────────────────────────────────────────────────────┘
```

## Agentes y Responsabilidades

| Agente | Herramienta | Responsabilidad | Trigger |
|--------|-------------|-----------------|---------|
| `lector-liturgico` | OpenClaw nativo | Scraping Koinonia, extracción lecturas | Cron: lunes 9:00 |
| `musico-liturgico` | OpenClaw nativo | Matching temático, propuesta canciones | Manual (post-lecturas) |
| `presentador-fieles` | OpenCode | Generar PPTX sin acordes | Mission Control pipeline |
| `presentador-musicos` | OpenCode | Generar PDF con acordes | Mission Control pipeline |
| `web-developer` | OpenCode | Generar HTML, desplegar web | Mission Control pipeline |
| `catalogador-canciones` | OpenCode | Scraper Blogspot, parser acordes | Inicial + mensual |
| `moderador-comentarios` | OpenClaw nativo | Revisar, presentar, aprobar | Cron: cada 6h |

## Flujo de Datos

```
1. Koinonia → scraper → JSON lecturas → DB → confirmación usuario
2. Blogspot → scraper → parser acordes → DB canciones (con/sin acordes)
3. DB lecturas + DB canciones → algoritmo matching → propuestas
4. Selección usuario → DB presentaciones → generadores PPTX/PDF
5. PPTX/PDF → web estática → GitHub Pages
6. Comentarios web → GitHub Issues → OpenClaw → usuario → aprobación
```

## Tecnologías por Capa

| Capa | Tecnología | Justificación |
|------|------------|---------------|
| Orquestación | Mission Control (crshdn) | Pipeline automático, UI visual, learner |
| Agentes IA | OpenClaw + OpenCode | Validación humana + desarrollo complejo |
| Scraping | Python (requests, BeautifulSoup) | Ligero, probado |
| Parser acordes | Python (regex, lxml) | Procesamiento texto estructurado |
| Base de datos | SQLite → PostgreSQL | Inicio simple, escala cuando se necesite |
| PPTX | python-pptx | Maduro, manipulación programática |
| PDF | LibreOffice headless + reportlab | Conversión nativa + generación directa |
| Web | Astro (SSG) | Framework moderno, estático, rápido |
| Hosting | GitHub Pages | Gratuito, integrado con git |
| Comentarios | GitHub Issues API | Gratuito, notificaciones nativas |
| CI/CD | GitHub Actions | Automatización despliegue |

## Decisiones Arquitectónicas Clave

### ADR-001: Mission Control como orquestador
- **Contexto**: Necesitamos pipeline automático con validación de calidad
- **Decisión**: Usar Mission Control (crshdn) con Builder→Tester→Reviewer→Verifier
- **Consecuencias**: + Calidad garantizada, + Visibilidad, - Complejidad inicial

### ADR-002: OpenCode para desarrollo complejo
- **Contexto**: Generación PPTX, parseo acordes, web requieren código robusto
- **Decisión**: OpenCode para tareas de desarrollo, OpenClaw para validación humana
- **Consecuencias**: + Código testeable, + Reutilizable, - Setup adicional

### ADR-003: SQLite inicial, PostgreSQL futuro
- **Contexto**: Base de datos pequeña al inicio, posible crecimiento
- **Decisión**: Empezar con SQLite, migrar a PostgreSQL si > 1000 canciones
- **Consecuencias**: + Simple, + Portable, - Limitaciones concurrencia

### ADR-004: GitHub Pages + Issues API
- **Contexto**: Hosting gratuito, comentarios sin backend propio
- **Decisión**: GitHub Pages para web, Issues API para comentarios
- **Consecuencias**: + Gratis, + Integrado, - Dependencia GitHub

### ADR-005: Formato 16:9 (widescreen)
- **Contexto**: El último PPTX real (274 Domingo 21 06 2026) usa 16:9
- **Decisión**: Usar 13.33" x 7.50" (16:9), no el MASTER 4:3
- **Consecuencias**: + Consistente con presentaciones actuales, - Requiere ajustar plantilla
