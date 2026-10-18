# 2. Arquitectura Actual

> **Nota importante:** las especificaciones originales (`specs/`) describían un sistema con Mission Control, OpenCode, formato 16:9 y migración futura a PostgreSQL. El sistema real difiere de ellas. Este capítulo refleja el sistema tal como funciona hoy.

## 2.1. Diagrama de componentes

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           USUARIO (RAFA)                                  │
│         Navegador en red local 192.168.68.x o en el propio PC             │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                     PANEL DE ADMINISTRACIÓN CCE-M5                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │   Admin API  │  │   Editor de   │  │  Editor de   │  │   Cancionero │  │
│  │   FastAPI    │  │  Diapositivas │  │   Acordes    │  │    Astro     │  │
│  │   :4323      │  │   Flask :4324 │  │  Flask :4322 │  │   :4321      │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘  │
│        │                  │                  │                  │        │
│        └──────────────────┴──────────────────┴──────────────────┘        │
│                                    │                                      │
│                                    ▼                                      │
│                         data/db.sqlite3 (SQLite)                          │
│                 Base de datos única para todo el sistema                  │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         GENERADORES LOCALES                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │  Koinonia    │  │ Ciudad Red.  │  │ Matching     │  │ Generador    │  │
│  │  scraper     │  │  scraper     │  │  temático    │  │ presentación │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                         OUTPUTS SEMANALES                                │
│  presentaciones/         presentaciones_html/        web/public/       │
│  ├── YYYY-MM-DD_*.pptx   ├── YYYY-MM-DD_presentacion/  ├── dist/        │
│  ├── YYYY-MM-DD_*.pdf    │   ├── index.html (Reveal)   └── (Astro)      │
│  └── YYYY-MM-DD_*.pdf    │   ├── *.json intermedio                    │
│                          │   └── *.pptx / *.pdf                         │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      GITHUB PAGES (público)                              │
│              https://cc5m5.github.io/CCE-M5/                             │
│   Generado automáticamente por .github/workflows/deploy.yml              │
└─────────────────────────────────────────────────────────────────────────┘
```

## 2.2. Servicios y puertos

| Servicio | Puerto | Tecnología | Unit systemd | Descripción |
|---|---|---|---|---|
| Admin API | **4323** | FastAPI + uvicorn | `cce-m5-admin.service` | Workflow de presentaciones, auth JWT, gestión de usuarios. |
| Panel admin UI | 4323 | HTML estático servido por FastAPI | (mismo servicio) | `/admin/` y `/admin/login.html`. |
| Editor de diapositivas | **4324** | Flask | `cce-m5-editor-diapositivas.service` | Catálogo de slides, composición por fecha, preview 4:3. |
| Editor de acordes | **4322** | Flask | (sin unit; arranque manual) | CRUD de canciones, regeneración de derivados. |
| Cancionero web | **4321** | Astro estático + http.server | `cce-m5-web.service` | `web/dist` servido en LAN. |

> **Nota histórica:** durante semanas los units tenían los puertos cruzados (`admin→4324`, `editor→4323`) y había procesos manuales corriendo. Desde 2026-10-18 los units están corregidos, pero el arranque limpio requiere que no haya procesos manuales ocupando esos puertos.

## 2.3. Decisiones arquitectónicas clave

### DA-001: Panel de administración propio (2026-09-28)
- **Contexto:** Mission Control dejó de ser usable como orquestador.
- **Decisión:** Crear un panel web propio con FastAPI, JWT y workflow manual paso a paso.
- **Consecuencias:** +Control directo, +Sin dependencias externas, -Requiere mantener auth y BD admin.

### DA-002: SQLite como única base de datos
- **Contexto:** El volumen de datos es pequeño (<1000 canciones, una presentación por semana).
- **Decisión:** Quedarse en SQLite; no migrar a PostgreSQL.
- **Consecuencias:** +Simple, +Portátil, -Concurrencia limitada (suficiente para uso local).

### DA-003: Formato 4:3 real (2026-09-21)
- **Contexto:** Las specs originales proponían 16:9, pero el formato real usado en la comunidad es 4:3.
- **Decisión:** Generar PPTX/HTML/PDF a 33,87 cm × 25,4025 cm (4:3).
- **Consecuencias:** +Consistente con la proyección real, -Requiere ajustes visuales en HTML y Astro.

### DA-004: HTML, PPTX y PDF desde el mismo JSON intermedio
- **Contexto:** Evitar divergencias entre lo que se ve en web, lo que se descarga y lo que proyectan.
- **Decisión:** `GeneradorDesdeComposicion` escribe un JSON común y luego renderiza PPTX, HTML y PDF desde él.
- **Consecuencias:** +Coherencia total, +Facilita testing, -El generador es más grande.

### DA-005: Cancionero N:M con `cancion_momentos`
- **Contexto:** Una misma canción puede usarse en varios momentos.
- **Decisión:** Tabla `cancion_momentos` (cancion_id, momento_liturgico). El campo `momento_liturgico` de `canciones` queda en desuso.
- **Consecuencias:** +Flexibilidad, -Requiere migrar/corregir datos antiguos.

### DA-006: Auto-rebuild al cambiar canciones (2026-10-08)
- **Contexto:** Al editar una canción, había que crear manualmente las slides `cancion_<id>` y regenerar presentaciones.
- **Decisión:** `auto_rebuild_presentaciones.py` crea slides y regenera presentaciones futuras automáticamente.
- **Consecuencias:** +Menos trabajo manual, -Posible regeneración no deseada si se edita una canción antigua.

## 2.4. Flujo de datos semanal

```
1. Admin panel: crear workflow para fecha de domingo.
2. Obtener lecturas: Koinonia → Ciudad Redonda → entrada manual.
3. Verificar lecturas en el panel.
4. Proponer canciones con matching temático + fallback por momento.
5. Verificar y ajustar asignación.
6. Generar assets: PPTX (fieles), PDF (fieles), PDF (músicos), HTML Reveal.js.
7. Publicar: exportar SQLite a JSON, copiar assets, npm run build.
8. Subir a GitHub Pages vía push a main (GitHub Actions).
```

## 2.5. Tecnologías

| Capa | Tecnología | Justificación |
|---|---|---|
| Backend | Python 3.13 + FastAPI/Flask | Ligero, maduro, fácil de mantener. |
| Frontend web | Astro 4.16 + React + Tailwind | SSG rápido, islands architecture. |
| Base de datos | SQLite | Portabilidad para un solo operador. |
| PPTX | python-pptx | Manipulación programática madura. |
| PDF músicos | fpdf2 + Courier New | Precisión de posición de acordes. |
| Scraping | requests + BeautifulSoup | Fuentes Koinonia y Ciudad Redonda. |
| Deploy | GitHub Pages + GitHub Actions | Gratuito e integrado. |

