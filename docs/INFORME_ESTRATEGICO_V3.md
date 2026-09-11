# CCE-M5-Web-Presentaciones - Informe Estrategico V3.0

## Resumen Ejecutivo

Sistema automatizado para preparacion semanal de presentaciones liturgicas con cancionero escolapio, hoja para musicos con acordes, y web de publicacion. Arquitectura hibrida: Mission Control + OpenCode + OpenClaw.

## Fuentes de Datos

- **Lecturas**: https://servicioskoinonia.org/biblico/calendario
- **Cancionero**: https://ccem5music.blogspot.com/p/cancionero-escolapio.html
- **Presentaciones**: NAS //192.168.1.177/homes/Rafa/Escolapios/11 Presentaciones PPT CCE M5/

## Formato Base PPTX

- **Archivo**: 274 Domingo 21 06 2026.pptx (NO el MASTER)
- **Dimensiones**: 16:9 (13.33" x 7.50")
- **Diapositivas**: 109
- **Layouts**: 11 (espanol)

## Momentos Liturgicos (12)

1. Entrada
2. Perdon
3. Gloria
4. Salmo
5. Aleluya
6. Ofertorio
7. Santo
8. Padre Nuestro
9. Paz
10. Comunion
11. Canto a Maria
12. Despedida

## Arquitectura Hibrida

Mission Control (crshdn) - Orquestador visual y pipeline automatico
- Builder -> Tester -> Reviewer -> Verifier
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

## Agentes Definidos

| Agente | Herramienta | Tarea | Trigger |
|--------|-------------|-------|---------|
| lector-liturgico | OpenClaw | Scraping Koinonia | Lunes 9:00 |
| musico-liturgico | OpenClaw | Matching tematico | Manual |
| presentador-fieles | OpenCode | PPTX sin acordes | Pipeline |
| presentador-musicos | OpenCode | PDF con acordes | Pipeline |
| web-developer | OpenCode | Astro + GitHub Pages | Pipeline |
| catalogador-canciones | OpenCode | Scraper Blogspot | Inicial |
| moderador-comentarios | OpenClaw | Moderacion | Cada 6h |

## Flujo Semanal

Lunes 9:00:
1. Scraper Koinonia -> lecturas JSON
2. Usuario confirma lecturas
3. Matching tematico -> propuestas canciones
4. Usuario elige canciones
5. Pregunta eventos especiales
6. OpenCode genera: PPTX fieles, PDF musicos, Web estatica
7. Despliegue GitHub Pages
8. Notificacion usuario

Cada 6h: Moderacion comentarios

## Cronograma: 8 Semanas

| Semana | Fase | Entregables |
|--------|------|-------------|
| 1 | Fundacion | Specs, DB, repo, MC |
| 2 | Scraping + Seed | 50+ canciones, parser |
| 3-4 | Matching + PPTX | PPTX 16:9, PDF musicos |
| 5-6 | Web + Deploy | Web completa, GitHub Pages |
| 7 | Integracion | Flujo end-to-end, tests |
| 8 | Refinamiento | Optimizaciones, docs |

## Correcciones Aplicadas

- Formato PPTX: 16:9 (ultimo: 274 Domingo 21 06 2026)
- Migracion completa cancionero
- Vista musicos con acordes + PDF
- 12 momentos liturgicos
- Cronograma 8 semanas

## Estructura del Proyecto

```
~/proyectos/CCE-M5-Web-Presentaciones/
├── .mission-control/
├── .openclaw/
├── specs/ (10 archivos)
├── data/
├── src/
├── presentaciones/
├── web/
├── docs/
└── tests/
```

Aprobado para inicio.
