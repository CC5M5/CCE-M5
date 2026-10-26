# 1. Introducción

## Propósito del documento

Este Software Design Description (SDD) describe la arquitectura, componentes, flujo de datos y decisiones técnicas del proyecto **CCE-M5-Web-Presentaciones**. Su objetivo es servir como fuente de verdad para el mantenimiento, la migración a otro equipo y la incorporación de nuevos desarrolladores o agentes.

## Alcance

El sistema prepara semanalmente presentaciones litúrgicas para la Comunidad Cristiana Escolapia Montequinto (CCE M5), incluyendo:

- Obtención de lecturas dominicales.
- Propuesta y asignación de canciones del cancionero escolapio.
- Edición de canciones y diapositivas litúrgicas.
- Generación de presentaciones PPTX, HTML (Reveal.js), PDF fieles y PDF músicos.
- Publicación de cancionero y presentaciones en GitHub Pages.

## Stakeholders

| Rol | Descripción |
|---|---|
| Rafa | Responsable musical; valida lecturas, canciones y publicación final. |
| Coro CCE M5 | Usuarios de la hoja de músicos con acordes. |
| Comunidad | Usuarios de las presentaciones y del cancionero web. |

## Referencias clave

| Recurso | Ubicación |
|---|---|
| Repositorio | `https://github.com/CC5M5/CCE-M5` |
| Proyecto local | `~/proyectos/CCE-M5-Web-Presentaciones` |
| Sitio público | `https://cc5m5.github.io/CCE-M5/` |
| Panel admin local | `http://<IP_LOCAL>:4323/admin/` |
| Cancionero local | `http://<IP_LOCAL>:4321/` |
| Editor de acordes | `http://<IP_LOCAL>:4323/editor-acordes/` |
| Editor de diapositivas | `http://<IP_LOCAL>:4323/editor-diapositivas/` |

## Términos y definiciones

| Término | Significado |
|---|---|
| **Momento litúrgico** | Cada parte de la celebración: entrada, gloria, salmo, aleluya, ofertorio, santo, padre_nuestro, paz, comunion, maria, despedida, etc. |
| **Slide / diapositiva** | Unidad visual del catálogo (`slides`) que se compone en una presentación. |
| **Composición** | Secuencia concreta de `presentacion_slides` para un domingo concreto. |
| **JSON intermedio** | Archivo `presentaciones_html/YYYY-MM-DD_presentacion/YYYY-MM-DD_presentacion.json` que alimenta PPTX, HTML y PDF. |
| **Hoja de músicos** | Documento PDF con todas las canciones de la semana con acordes, en orden litúrgico. |
