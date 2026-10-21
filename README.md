# CCE-M5-Web-Presentaciones

Sistema automatizado para preparacion semanal de presentaciones liturgicas con cancionero escolapio.

## Configuración

La configuración se carga desde variables de entorno con validación y defaults centralizados en `src/config.py` (pydantic-settings). Para entorno de desarrollo copia `.env.example` a `.env` y ajusta los valores:

```bash
cp .env.example .env
# edita .env con tu editor favorito
```

### Variables principales

| Variable | Descripción | Default |
|----------|-------------|---------|
| `CCE_PROJECT_DIR` | Raíz del proyecto | `~/proyectos/CCE-M5-Web-Presentaciones` |
| `CCE_BASE_PATH` | Base path de Astro | `/` |
| `CCE_SITE_URL` | URL base del site local | `http://localhost:4321` |
| `CCE_ADMIN_JWT_SECRET` | Secreto para tokens JWT | generado automáticamente |
| `CCE_ADMIN_DEFAULT_USER` | Usuario admin inicial | `rafael.torres` |
| `CCE_ADMIN_DEFAULT_PASSWORD` | Contraseña admin inicial | `1234` |
| `CCE_ADMIN_REDIS_URL` | Redis para rate limiting | memoria local |
| `CCE_NODE_BIN` | Directorio con `node`/`npm` | `/usr/bin` |

Los módulos legacy que aún importan `src.web_admin.config` siguen funcionando porque delegan dinámicamente en `src.config.settings`.

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
