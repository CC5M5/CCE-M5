# Spec 07: Cronograma de Implementación (Acortado)

## Línea Temporal: 8 Semanas

```
SEMANA:  1       2       3       4       5       6       7       8
          │       │       │       │       │       │       │       │
FASE 0    ├───────┤
FASE 1            ├───────┤
FASE 2                    ├───────┤
FASE 3                            ├───────┤
FASE 4                                    ├───────┤
FASE 5                                            ├───────┤
INTEGRACIÓN                                             ├───────┤
```

## Detalle por Fase

### FASE 0: Fundación (Semana 1)

| Día | Tarea | Responsable | Entregable |
|-----|-------|-------------|------------|
| 1 | Instalar/verificar Mission Control | Sistema | MC funcionando |
| 1 | Instalar OpenCode | Sistema | OC funcionando |
| 2 | Redactar specs SDD completos | OpenClaw | specs/00-07.md |
| 2 | Configurar agentes en MC | OpenClaw | agents.yaml |
| 3 | Crear base de datos SQLite | OpenCode | db.sqlite3 + schema |
| 4 | Configurar automatizaciones OpenClaw | OpenClaw | automations.yaml |
| 5 | Setup inicial proyecto Astro | OpenCode | web/ con Astro base |
| 5 | Configurar GitHub repo + Pages | Manual | Repo creado |
| 6-7 | Review y ajustes | OpenClaw | Specs aprobadas |

**Entregables Fase 0:**
- ✅ Estructura de directorios
- ✅ Specs SDD completas
- ✅ Base de datos creada
- ✅ Repo GitHub configurado
- ✅ Mission Control configurado

---

### FASE 1: Scraping + Parser + Seed (Semana 2)

| Día | Tarea | Responsable | Entregable |
|-----|-------|-------------|------------|
| 8 | Scraper Koinonia (lecturas) | OpenCode | koinonia_scraper.py |
| 9 | Scraper Blogspot (canciones) | OpenCode | blogspot_scraper.py |
| 10 | Parser acordes | OpenCode | acordes_parser.py |
| 11 | Seed canciones iniciales (~50) | OpenCode | canciones.json |
| 12 | Tests scraping | OpenCode | Tests unitarios |
| 13 | Validación usuario | OpenClaw | Seed aprobado |
| 14 | Correcciones seed | OpenCode | Dataset limpio |

**Entregables Fase 1:**
- ✅ 50+ canciones en base de datos
- ✅ Parser de acordes funcionando
- ✅ Lecturas scraper funcionando
- ✅ Tests unitarios

---

### FASE 2: Matching + Presentación (Semana 3-4)

#### Semana 3

| Día | Tarea | Responsable | Entregable |
|-----|-------|-------------|------------|
| 15-16 | Algoritmo matching temático | OpenCode | matching.py |
| 17-18 | Plantilla PPTX base (16:9) | OpenCode | base.pptx |
| 19 | Generador PPTX fieles | OpenCode | presentacion_fieles.py |
| 20-21 | Tests generación | OpenCode | Tests PPTX |

#### Semana 4

| Día | Tarea | Responsable | Entregable |
|-----|-------|-------------|------------|
| 22-23 | Generador PDF músicos | OpenCode | hoja_musicos.py |
| 24-25 | Conversión PPTX→PDF | OpenCode | Conversión automatizada |
| 26 | Pipeline MC: Build→Test→Review | Mission Control | Pipeline funcionando |
| 27-28 | Integración OpenClaw ↔ MC | OpenClaw | Flujo end-to-end |

**Entregables Fase 2:**
- ✅ Matching canciones-lecturas funcionando
- ✅ PPTX generado desde plantilla 16:9
- ✅ PDF músicos con acordes
- ✅ Pipeline MC automatizado

---

### FASE 3: Web + Publicación (Semana 5-6)

#### Semana 5

| Día | Tarea | Responsable | Entregable |
|-----|-------|-------------|------------|
| 29-31 | Desarrollo web Astro | OpenCode | Páginas principales |
| 32-33 | Cancionero completo | OpenCode | /cancionero/ funcional |
| 34 | Vista músicos | OpenCode | /musicos/ funcional |

#### Semana 6

| Día | Tarea | Responsable | Entregable |
|-----|-------|-------------|------------|
| 35-36 | Lecturas histórico | OpenCode | /lecturas/ funcional |
| 37 | Formulario comentarios | OpenCode | /comentarios/ funcional |
| 38-39 | GitHub Issues API backend | OpenCode | Backend comentarios |
| 40 | Despliegue GitHub Pages | OpenCode | Web online |

**Entregables Fase 3:**
- ✅ Web completa en GitHub Pages
- ✅ Cancionero migrado
- ✅ Vista músicos funcional
- ✅ Sistema de comentarios

---

### FASE 4: Integración + Flujo Completo (Semana 7)

| Día | Tarea | Responsable | Entregable |
|-----|-------|-------------|------------|
| 41-42 | Integrar flujo semanal completo | Mission Control | Pipeline liturgia-semanal |
| 43 | Prueba con semana real | OpenClaw | Presentación generada |
| 44-45 | Correcciones y ajustes | OpenCode | Fixes aplicados |
| 46-47 | Documentación final | OpenClaw | docs/ completos |
| 48 | Review final con usuario | OpenClaw | Aprobación usuario |

**Entregables Fase 4:**
- ✅ Flujo semanal automatizado
- ✅ Pipeline MC completo
- ✅ Documentación actualizada
- ✅ Aprobación usuario

---

### FASE 5: Refinamiento (Semana 8)

| Día | Tarea | Responsable | Entregable |
|-----|-------|-------------|------------|
| 49-50 | Optimizar matching | OpenCode | Algoritmo mejorado |
| 51-52 | Añadir canciones PDFs personales | OpenCode | +canciones |
| 53-54 | Ajustes visuales web | OpenCode | Polish UI |
| 55-56 | Métricas y logging | OpenCode | Dashboard básico |

**Entregables Fase 5:**
- ✅ Matching optimizado
- ✅ Cancionero ampliado
- ✅ Web pulida
- ✅ Métricas disponibles

---

## Milestones

| Fecha | Milestone | Estado |
|-------|-----------|--------|
| Semana 1 | Fundación completa | ⏳ Pendiente |
| Semana 2 | Dataset canciones listo | ⏳ Pendiente |
| Semana 4 | Presentaciones generándose | ⏳ Pendiente |
| Semana 6 | Web publicada | ⏳ Pendiente |
| Semana 7 | Flujo semanal automatizado | ⏳ Pendiente |
| Semana 8 | Sistema en producción | ⏳ Pendiente |

## Recursos Necesarios

| Recurso | Cantidad | Coste |
|---------|----------|-------|
| GitHub (repo + Pages) | 1 | Gratis |
| Mission Control hosting | 1 | ~5€/mes VPS |
| OpenCode (local) | 1 | Gratis |
| OpenClaw (existente) | 1 | Ya disponible |
| NAS (almacenamiento) | Existente | Ya disponible |

## Riesgos y Mitigaciones

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|-------------|---------|------------|
| Koinonia cambia estructura web | Media | Alto | Cache local + fallback manual |
| Blogspot bloquea scraping | Media | Alto | Rate limiting + User-Agent real |
| Formato PPTX incompatible | Baja | Alto | Validar con python-pptx antes |
| Demora en aprobación usuario | Alta | Medio | Notificaciones proactivas |
| GitHub Pages limitaciones | Baja | Medio | Evaluar Vercel/Netlify si es necesario |

## Criterios de Éxito

1. ✅ Pipeline genera presentación completa < 5 minutos
2. ✅ Web publicada y accesible públicamente
3. ✅ Cancionero completo migrado y navegable
4. ✅ Hoja músicos generada con acordes correctos
5. ✅ Usuario confirma lecturas y canciones cada semana
6. ✅ Comentarios funcionan y se moderan

## Post-Lanzamiento (Fase 6+ — No incluida)

| Feature | Prioridad | Estimación |
|---------|-----------|------------|
| App móvil (PWA) | Media | 2 semanas |
| Integración proyección directa | Baja | 3 semanas |
| Multi-idioma (es/en) | Baja | 2 semanas |
| Sistema de usuarios/login | Baja | 3 semanas |
| Analytics de uso | Baja | 1 semana |
