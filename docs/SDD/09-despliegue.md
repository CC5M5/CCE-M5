# 9. Despliegue e Infraestructura

## 9.1. Servicios systemd

Las unidades oficiales están en `config/systemd/user/` y son **portables**: usan `%h` para el home del usuario, por lo que funcionan en cualquier PC destino sin editar rutas absolutas.

| Unit | Puerto | Estado objetivo | Notas |
|---|---|---|---|
| `cce-m5-admin.service` | 4323 | Habilitado | FastAPI. Requiere `.env` con secretos. |
| `cce-m5-editor-diapositivas.service` | 4324 | Habilitado | Flask. Editor del catálogo de slides. |
| `cce-m5-editor-acordes.service` | 4322 | Habilitado | Flask. Editor del cancionero. |
| `cce-m5-web.service` | 4321 | Habilitado | Sirve `web/dist` estáticamente. |
| `cce-m5-backup-db.service` | — | Activado por timer | Backup diario de `data/db.sqlite3`. |
| `cce-m5-backup-db.timer` | — | Habilitado | Dispara el backup cada día. |
| `cce-m5-pipeline.service` | — | **Eliminado** | Trigger de Mission Control obsoleto. |
| `cce-m5-pipeline.timer` | — | **Eliminado** | Ya no se usa. |

> **Nota importante:** en el PC origen había rutas absolutas `/home/pciath/...`, puertos cruzados y un drop-in de Mission Control. Todas esas configuraciones han sido limpiadas. En el destino basta con copiar las unidades de `config/systemd/user/`.

## 9.2. Variables de entorno

Archivo: `.env` (no commiteado; leído por systemd con `EnvironmentFile=`).

```ini
# Panel de administración
CCE_ADMIN_JWT_SECRET=cambia-esta-clave-en-produccion
CCE_ADMIN_DEFAULT_USER=rafael.torres
CCE_ADMIN_DEFAULT_PASSWORD=1234

# Node local (nvm)
CCE_NODE_BIN=/home/pciath/.nvm/versions/node/v22.23.3/bin

# Rebuild web local
CCE_BASE_PATH=/
CCE_SITE_URL=http://192.168.68.244:4321

# Despliegue (solo si se usa comentarios proxy)
GITHUB_TOKEN_CC5M5=...
```

> **Importante:** `.env` no debe incluir `export` ni comillas para que systemd lo interprete correctamente.

## 9.3. GitHub Actions

Workflow: `.github/workflows/deploy.yml`

- Runner: `ubuntu-22.04`.
- Node: 22.23.3 (via `actions/setup-node@v4`).
- Instalación: `npm install` con `package-lock.json` congelado en el repo.
- Instalación Python: `pip install -r requirements.lock.txt` (dependencias congeladas).
- Copia `presentaciones/` y `presentaciones_html/` a `web/public/`.
- Exporta SQLite a JSON con `scripts/export_data_for_web.py`.
- Build Astro con `BASE_PATH=/CCE-M5/`.
- Publica en GitHub Pages vía `actions/deploy-pages@v4`.

## 9.4. Backup de la base de datos

- Script en el repo: `scripts/systemd/cce-m5-backup-db.sh`.
- Destino por defecto: `$HOME/.config/cce-m5/backups/db/`.
- Retención: 30 días (`CCE_BACKUP_KEEP_DAYS`).
- Timer: `cce-m5-backup-db.timer` (una vez al día).

## 9.5. Seguridad operativa

- Cambiar `CCE_ADMIN_JWT_SECRET` por un token seguro ≥32 bytes.
- Cambiar `CCE_ADMIN_DEFAULT_PASSWORD`.
- No commitear `.env` ni `data/.admin_jwt_secret`.
- Ajustar `ADMIN_CORS_ORIGINS` en `.env` si la IP local cambia.
- Restringir CORS en producción pública.

## 9.6. Limitaciones del sitio estático

La web pública (`web/dist` / GitHub Pages) es **estática**. El JavaScript puede hacer peticiones (`fetch`) al backend, pero con importantes limitaciones:

- **CORS:** el navegador exige que la API (`http://192.168.68.244:4323`) responda con el `Access-Control-Allow-Origin` adecuado. Revisar `ADMIN_CORS_ORIGINS` en `.env`.
- **Red local:** los `fetch` desde GitHub Pages a la API local solo funcionarán si el navegador tiene acceso a la red local del servidor CCE-M5 (VPN, proxy o URL pública).
- **Comentarios:** el formulario de comentarios de la web usa el proxy del admin API (`/api/comentarios`). Si el admin no está expuesto/reachable, el formulario no funciona.
- **Panel admin excluido:** el build de GitHub Pages elimina `src/pages/admin` y `src/pages/admin.astro` para no publicar el panel de administración.

> **Regla general:** la web estática sirve para lectura pública. Cualquier operación de escritura (comentarios, login, workflow) requiere alcanzar el admin API en la red local o a través de un proxy controlado.
