# INFORME ESTRATÉGICO: CCE-M5-Web-Presentaciones

## Versión 2.0 Final — Correcciones Aplicadas
**Fecha:** 8 de septiembre de 2026  
**Estado:** Listo para inicio de implementación

---

## RESUMEN EJECUTIVO

Sistema automatizado para preparación semanal de presentaciones litúrgicas con integración de cancionero escolapio, hoja para músicos con acordes, y web de publicación. Arquitectura híbrida: Mission Control + OpenCode + OpenClaw.

---

## CORRECCIONES APLICADAS

| # | Corrección | Estado |
|---|-----------|--------|
| 1 | **Migración completa cancionero**: No solo fuente, sino recrear toda la web | OK Aplicada (Spec 08) |
| 2 | **Vista músicos con acordes**: Nueva pestaña + PDF descargable | OK Aplicada (Spec 09) |
| 3 | **Momentos litúrgicos completos**: Añadidos Perdón, Salmo, Ofertorio | OK Aplicada (12 momentos) |
| 4 | **Acceso NAS verificado**: Confirmado y analizado | OK Completado |
| 5 | **Estructura directorios**: `CCE-M5-Web-Presentaciones` | OK Creada |
| 6 | **Plazos acortados**: De 12 a 8 semanas | OK Ajustado (Spec 07) |
| 7 | **Formato PPTX**: Usar último por fecha, no MASTER | OK Corregido (274 Domingo 21 06 2026) |

---

## VERIFICACIONES REALIZADAS

### NAS: OK ACCESO CONFIRMADO
- **Ruta:** `smb://192.168.1.177/homes/Rafa/Escolapios/11 Presentaciones PPT CCE M5/`
- **Archivos:** 123+ archivos .pptx (2022-2026)
- **Plantilla MASTER:** `MASTER_PowerPoint Eucaristía.pptx` (39.6 MB, 121 diapositivas, 4:3)
- **Último formato:** `274 Domingo 21 06 2026.pptx` (16.6 MB, 109 diapositivas, **16:9**)

### Análisis 274 Domingo 21 06 2026.pptx:
- **Dimensiones:** 13.33" x 7.50" (16:9 widescreen)
- **Diapositivas:** 109
- **Layouts:** 11 (español)
- **Estructura detectada:** Entrada → Perdón → Gloria → Aleluya → Ofertorio → Santo → Padre Nuestro → Paz → Comunión → María → Despedida

**DECISIÓN:** Usar formato 16:9 del 274 como base, MASTER solo como referencia de canciones.

---

## ARQUITECTURA HÍBRIDA (Mission Control + OpenCode + OpenClaw)

```
Mission Control (crshdn) — Orquestador visual y pipeline automático
    ├── Builder → Tester → Reviewer → Verifier
    ├── Convoy Mode: Múltiples tareas en paralelo
    └── Learner: Acumula lecciones aprendidas
    
OpenCode — Fuerza de desarrollo (código complejo)
    ├── Generador PPTX/PDF
    ├── Scraper y parser
    └── Web (Astro)
    
OpenClaw — Comandante humano (validaciones)
    ├── Validación semanal de lecturas
    ├── Selección de canciones
    └── Moderación comentarios
```

---

## AGENTES DEFINIDOS

| Agente | Herramienta | Tarea |
|--------|-------------|-------|
| `lector-liturgico` | OpenClaw | Scraping Koinonia, lecturas |
| `musico-liturgico` | OpenClaw | Matching canciones-lecturas |
| `presentador-fieles` | OpenCode | PPTX sin acordes (16:9) |
| `presentador-musicos` | OpenCode | PDF con acordes |
| `web-developer` | OpenCode | Astro + GitHub Pages |
| `catalogador-canciones` | OpenCode | Scraper Blogspot + parser |
| `moderador-comentarios` | OpenClaw | Moderación cada 6h |

---

## MOMENTOS LITÚRGICOS (12)

1. Entrada
2. Perdón (Acto penitencial)
3. Gloria
4. Salmo (Responsorial)
5. Aleluya (Aclamación)
6. Ofertorio
7. Santo
8. Padre Nuestro
9. Paz
10. Comunión
11. Canto a María
12. Despedida

---

## FLUJO SEMANAL AUTOMATIZADO

```
Lunes 9:00
├── 1. Scraper Koinonia → lecturas JSON
├── 2. Usuario confirma lecturas
├── 3. Matching temático → propuestas canciones
├── 4. Usuario elige canciones
├── 5. Pregunta eventos especiales
├── 6. OpenCode genera:
│   ├── PPTX fieles (16:9, sin acordes)
│   ├── PDF músicos (con acordes)
│   └── Web estática (Astro)
├── 7. Despliegue GitHub Pages
└── 8. Notificación usuario

Cada 6h: Moderación comentarios
```

---

## CRONOGRAMA: 8 SEMANAS

| Semana | Fase | Entregables |
|--------|------|-------------|
| 1 | Fundación | Specs, DB, repo, MC configurado |
| 2 | Scraping + Seed | 50+ canciones, parser acordes |
| 3-4 | Matching + PPTX | Matching, PPTX 16:9, PDF músicos |
| 5-6 | Web + Deploy | Web completa, GitHub Pages |
| 7 | Integración | Flujo end-to-end, tests |
| 8 | Refinamiento | Optimizaciones, documentación |

---

## NUEVAS FUNCIONALIDADES CLAVE

### 1. Migración Cancionero Completo (Spec 08)
- Scraper de TODO el Blogspot ccem5music.blogspot.com
- 50+ canciones con acordes parseados
- Estructura JSON posicional para acordes
- Web navegable con búsqueda y filtros

### 2. Vista para Músicos (Spec 09)
- Pestaña `/musicos/YYYY-MM-DD/` en web
- PDF descargable con acordes bien posicionados
- Una sola página/documento, sin navegación
- Formato A4 vertical, legible a distancia
- Toggle mostrar/ocultar acordes en web

---

## DIRECTORIO DEL PROYECTO

```
~/proyectos/CCE-M5-Web-Presentaciones/
├── .mission-control/       # Mission Control
├── .openclaw/              # Automatizaciones
├── specs/                  # 8 specs SDD
├── data/                   # Lecturas, canciones, DB
├── src/                    # Scrapers, parsers, generators
├── presentaciones/         # Output PPTX/PDF
├── web/                    # Astro site
├── docs/                   # Documentación + ADRs
└── tests/                  # Tests unitarios/integración
```

---

## ENTREGABLES DE ESTE INFORME

| Formato | Ruta | Estado |
|---------|------|--------|
| Specs SDD | `~/proyectos/CCE-M5-Web-Presentaciones/specs/` | OK Generado |
| Informe MD | `~/proyectos/CCE-M5-Web-Presentaciones/docs/INFORME_ESTRATEGICO_V2.md` | OK Generado |
| PDF | Pendiente conversión | PENDIENTE |
| Telegram | Pendiente envío | PENDIENTE |

---

## PRÓXIMOS PASOS (Mañana)

1. OK **Revisión usuario** de este informe
2. EN PROGRESO **Generar PDF** del informe (LibreOffice/pandoc)
3. EN PROGRESO **Enviar por Telegram** (si se proporciona canal)
4. EN PROGRESO **Guardar en memoria** largo plazo
5. PENDIENTE **Comenzar FASE 0** (Fundación)

---

## CONCLUSIÓN

Todas las correcciones solicitadas han sido aplicadas. El sistema está diseñado para ser escalable, automatizado y centrado en el flujo litúrgico semanal. La integración Mission Control + OpenCode + OpenClaw proporciona pipeline automático con validación humana en los puntos críticos.

**¿Aprobado para inicio mañana?**
