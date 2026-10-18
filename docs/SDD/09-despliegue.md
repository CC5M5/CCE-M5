# 9. Despliegue e Infraestructura

## 9.1. Servicios systemd

| Unit | Estado objetivo | Notas |
|---|---|---|
| `cce-m5-admin.service` | Habilitado, puerto 4323 | Corrige puerto cruzado anterior. |
| `cce-m5-editor-diapositivas.service` | Habilitado, puerto 4324 | Corrige puerto cruzado anterior. |
| `cce-m5-web.service` | Habilitado, puerto 4321 | Sirve `web/dist` estáticamente. |
| `cce-m5-pipeline.service` | **Deshabilitado** | Trigger de Mission Control obsoleto. |
| `cce-m5-pipeline.timer` | **Deshabilitado** | Ya no se usa. |

## 9.2. Variables de entorno

Archivo: `.env` (no commiteado; leído por systemd con `EnvironmentFile=`).

```ini
# Panel de administración
CCE_ADMIN_JWT_SECRET=cambia-esta-clave-en-produccion
CCE_ADMIN_DEFAULT_USER=rafael.torres
CCE_ADMIN_DEFAULT_PASSWORD=1234

# Node local
CCE_NODE_BIN=/home/pciath/.nvm/versions/node/v22.23.3/bin

# Despliegue
GITHUB_TOKEN_CC5M5=...
```

> **Importante:** `.env` no debe incluir `export` ni comillas para que systemd lo interprete correctamente.

## 9.3. GitHub Actions

Workflow: `.github/workflows/deploy.yml`

- Runner: `ubuntu-22.04`.
- Node: 22.
- Instalación: `npm install` (no `npm ci`; `package-lock.json` está en `.gitignore`).
- Copia `presentaciones/` y `presentaciones_html/` a `web/public/`.
- Exporta SQLite a JSON con Python.
- Build Astro con `BASE_PATH=/CCE-M5/`.
- Publica en GitHub Pages vía `actions/deploy-pages@v4`.

## 9.4. Seguridad operativa

- Cambiar `CCE_ADMIN_JWT_SECRET` por un token seguro ≥32 bytes.
- Cambiar `CCE_ADMIN_DEFAULT_PASSWORD`.
- No commitear `.env` ni `data/.admin_jwt_secret`.
- Restringir CORS en producción pública.

