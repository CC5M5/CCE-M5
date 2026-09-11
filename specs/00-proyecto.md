# Spec 00: Visión del Proyecto CCE-M5-Web-Presentaciones

## Información General

| Campo | Valor |
|-------|-------|
| **Nombre** | CCE-M5-Web-Presentaciones |
| **Fecha inicio** | 2026-09-08 |
| **Versión** | 2.0 |
| **Autor** | OpenClaw Agent (main) |
| **Cliente/Usuario** | Rafa (Comunidad Cristiana Escolapia Montequinto) |

## Propósito

Sistema automatizado para la preparación semanal de presentaciones litúrgicas y cancionero escolapio, incluyendo:
1. Búsqueda automática de lecturas dominicales desde servicioskoinonia.org
2. Selección inteligente de canciones del cancionero escolapio
3. Generación de presentaciones PPTX (formato 16:9, basado en último PPTX: 274 Domingo 21 06 2026)
4. Generación de hoja para músicos con acordes (PDF descargable)
5. Publicación web con cancionero completo migrado
6. Moderación de comentarios de la comunidad

## Stakeholders

- **Rafa**: Responsable musical, valida lecturas y selección de canciones
- **Coro CCE M5**: Usuarios de la hoja de músicos con acordes
- **Comunidad**: Usuarios de presentaciones y web

## Alcance

### Incluido
- Scraping de lecturas de Koinonia
- Base de datos de 50+ canciones escolapias (con/sin acordes)
- Algoritmo de matching temático lecturas-canciones
- Generación PPTX 16:9 (basado en formato real 274 Domingo 21 06 2026)
- Generación PDF para músicos con acordes
- Web estática con cancionero completo migrado
- Sistema de comentarios con moderación

### Excluido (futuras fases)
- Integración con proyección en tiempo real
- App móvil nativa
- Sistema de usuarios/login
- Streaming de audio

## Referencias Clave

| Recurso | URL/Ruta |
|---------|----------|
| Fuente lecturas | https://servicioskoinonia.org/biblico/calendario |
| Cancionero escolapio | https://ccem5music.blogspot.com/p/cancionero-escolapio.html |
| Plantilla formato (referencia) | NAS: `Escolapios/11 Presentaciones PPT CCE M5/274 Domingo 21 06 2026.pptx` |
| Repositorio canciones (MASTER) | NAS: `Escolapios/11 Presentaciones PPT CCE M5/MASTER_PowerPoint Eucaristía.pptx` |
| Presentaciones históricas | NAS: `Escolapios/11 Presentaciones PPT CCE M5/` (123+ archivos) |
