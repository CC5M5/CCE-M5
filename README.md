# CCE-M5-Web-Presentaciones

Sistema automatizado para preparacion semanal de presentaciones liturgicas con cancionero escolapio.

## Funcionalidades

- Scraping semanal de lecturas desde Koinonia
- Migracion completa del cancionero escolapio desde Blogspot
- Matching tematico entre lecturas y canciones
- Generacion de presentaciones PPTX 16:9 sin acordes para fieles
- Generacion de hoja PDF con acordes para musicos
- Web estatica con cancionero, presentaciones y vista de musicos
- Sistema de comentarios con moderacion

## Arquitectura

- **Mission Control**: Orquestacion de pipeline automatico
- **OpenCode**: Desarrollo de scrapers, generadores y web
- **OpenClaw**: Validacion humana y automatizaciones

## Tecnologias

- Python (scrapers, PPTX, PDF)
- Astro + Tailwind CSS (web)
- SQLite (base de datos)
- GitHub Pages (hosting)

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

## Estructura

```
.
├── data/           # Base de datos y archivos de datos
├── specs/          # Especificaciones del proyecto
├── src/            # Codigo fuente
├── web/            # Sitio web (Astro)
├── docs/           # Documentacion
└── tests/          # Pruebas
```

## Estado

🚧 En desarrollo - Fase 0: Fundacion
