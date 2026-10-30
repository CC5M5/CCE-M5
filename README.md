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
| `CCE_ADMIN_DEFAULT_PASSWORD` | Contraseña del admin inicial (solo si aún no existe el admin) | *(sin valor por defecto; obligatorio en primera instalación)* |
| `CCE_ADMIN_REDIS_URL` | Redis para rate limiting | memoria local |
| `CCE_NODE_BIN` | Directorio con `node`/`npm` | `/usr/bin` |

Los módulos legacy que aún importan `src.web_admin.config` siguen funcionando porque delegan dinámicamente en `src.config.settings`.

## Operación local (systemd)

Para servir la web y el panel de administración de forma persistente, el
repositorio incluye units de systemd usuario en
`config/systemd/user/`:

```bash
# Copiar units (desde el repo)
cp config/systemd/user/cce-m5-admin.service ~/.config/systemd/user/
cp config/systemd/user/cce-m5-web.service ~/.config/systemd/user/
cp config/systemd/user/cce-m5-healthcheck.service ~/.config/systemd/user/
cp config/systemd/user/cce-m5-healthcheck.timer ~/.config/systemd/user/
cp config/systemd/user/cce-m5-backup-db.service ~/.config/systemd/user/
cp config/systemd/user/cce-m5-backup-db.timer ~/.config/systemd/user/

# Recargar, habilitar e iniciar
systemctl --user daemon-reload
systemctl --user enable --now cce-m5-admin cce-m5-web cce-m5-healthcheck.timer cce-m5-backup-db.timer

# Ver estado
systemctl --user status cce-m5-admin cce-m5-web
systemctl --user list-timers cce-m5-healthcheck.timer cce-m5-backup-db.timer
```

Servicios expuestos:

| Puerto | Servicio |
|--------|----------|
| 4321 | Web estática (Astro) |
| 4323 | Admin API (FastAPI) + editores Flask integrados |

Los editores legacy (acordes y diapositivas) se sirven bajo el mismo
servicio FastAPI en:

- http://localhost:4323/editor-acordes/
- http://localhost:4323/editor-diapositivas/

### Healthcheck

El script `scripts/healthcheck.py` verifica que admin, editores y web
respondan. Se ejecuta:

- Como `ExecStartPost` de `cce-m5-admin.service` tras cada arranque.
- Cada hora vía `cce-m5-healthcheck.timer`.

```bash
# Ejecución manual
.venv/bin/python scripts/healthcheck.py
```

### Runbook básico

1. **Ver salud**: `python scripts/healthcheck.py`.
2. **Reiniciar admin**: `systemctl --user restart cce-m5-admin`.
3. **Reiniciar web**: `systemctl --user restart cce-m5-web`.
4. **Ver logs**: `journalctl --user -u cce-m5-admin -f`.
5. **Los servicios antiguos de editores (puertos 4322 y 4324) están
   deshabilitados**; los editores viven dentro del admin en 4323.

## Docker

El proyecto incluye `Dockerfile` y `docker-compose.yml` para levantar todos los servicios:

```bash
# 1. Build de la web estática (host-side)
cd web && npm install && npm run build && cd ..

# 2. Levantar todos los servicios
docker compose up -d

# 3. Verificar health
open http://localhost:4323/health
```

**Nota:** El build de Docker requiere varios GB libres en el disco del host para extraer capas. En este entorno no se ha podido completar por falta de espacio; la imagen se valida con `docker compose config`.

## Exponer a Internet (requisitos)

El servicio está pensado para LAN: los orígenes CORS por defecto son locales,
el rate limiting vive en memoria y ninguno de los servicios emite TLS. Para
exponerlo a Internet se deben cubrir estos puntos:

1. **TLS / reverse proxy.** El admin API (4323) y la web estática (4321) no
   emiten TLS. Servirlos detrás de un reverse proxy con HTTPS (Caddy, nginx,
   etc.) que redirija `http → https`. Si se sirve bajo un subpath
   (p. ej. `https://dominio/cce/`), fijar `CCE_BASE_PATH=/cce/` y
   `CCE_SITE_URL=https://dominio/cce/` en `.env`.
2. **Secreto JWT.** Definir `CCE_ADMIN_JWT_SECRET` explícitamente en `.env`
   (mínimo 32 bytes). Sin valor, se genera uno aleatorio y se persiste en
   `data/.admin_jwt_secret`; si ese archivo no viaja con la instalación, los
   tokens existentes quedan inválidos en cada arranque.
3. **CORS.** El default solo permite orígenes locales. Para el dominio
   público, añadir `ADMIN_CORS_ORIGINS` con los orígenes exactos (sin `*`):
   `ADMIN_CORS_ORIGINS=https://dominio,https://dominio/cce`.
4. **Primera instalación.** `CCE_ADMIN_DEFAULT_PASSWORD` es **obligatorio**
   mientras no exista el usuario admin: el arranque falla explícitamente
   (fail-fast) si falta. Usar una contraseña fuerte; una vez creado el admin,
   la variable deja de usarse y puede eliminarse de `.env`.
5. **Comentarios.** `POST /comentarios` requiere autenticación (401 sin
   token) y está limitado por IP (`CCE_ADMIN_COMENTARIOS_RATE_LIMIT_MAX`,
   default 5 por hora). El proxy usa `GITHUB_TOKEN_CC5M5` solo en el servidor;
   el issue público de GitHub no incluye el email del visitante. Si se corren
   varias instancias de la API tras el proxy, el rate limiting en memoria no
   se comparte: definir `CCE_ADMIN_REDIS_URL` (p. ej. `redis://localhost:6379/0`)
   para un backend común. Con una sola instancia no es necesario.
6. **Backups.** `cce-m5-backup-db.timer` hace un backup diario consistente
   (API de backup de SQLite, salida gzip con permisos 600, retención de 30
   días) en `~/.config/cce-m5/backups/db/` (configurable con
   `CCE_BACKUP_DIR`). Para exposición pública conviene copiar esos backups a
   otro sitio.

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
