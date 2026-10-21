# Auditoría Técnica CCE-M5-Web-Presentaciones

**Fecha:** 2026-10-21
**Objetivo:** Preparar el proyecto para migración a otro PC y documentar estado técnico.

---

## 1. Estado actual detectado (post-cambios)

| Aspecto | Estado |
|---|---|
| Servicios systemd | Activos en puertos correctos: `4321` web, `4322` acordes, `4323` admin, `4324` diapositivas |
| Pipeline Mission Control | Eliminado (`cce-m5-pipeline.service`, `.timer`, drop-in) |
| `pyproject.toml` | Activo; entry point legacy `generar_semana` eliminado |
| `__init__.py` | Presentes en todos los paquetes de `src/` |
| `requirements.lock.txt` | Actualizado con `pip freeze`; token filtrado |
| `web/package-lock.json` | Congelado y trackeado en git |
| `.nvmrc` / `package.json` | Node fijado a `22.23.3` |
| `.env` | En `.gitignore`, permisos `600` |
| Tests | 246 pasan en ~35s |
| `ruff` | Limpio en scripts editados |
| `mypy` | Limpio en scripts editados; 42 errores preexistentes en otros módulos |
| `data/schema_full.sql` | Refrescado desde BD real (212 líneas) |
| Backup diario | Migrado al repo: `scripts/systemd/cce-m5-backup-db.sh` |
| Units systemd | Portables en `config/systemd/user/` usando `%h` |

---

## 2. Cambios aplicados durante la auditoría

### A. Portabilidad y migración

1. **Units systemd portables**
   - Creadas en `config/systemd/user/` con `%h` en lugar de `/home/pciath/...`.
   - Añadido `PYTHONPATH=%h/proyectos/CCE-M5-Web-Presentaciones` para importar `src` sin `sys.path`.
   - Añadido `cce-m5-editor-acordes.service` y `cce-m5-backup-db.timer`.

2. **Scripts sin rutas absolutas**
   - `src/rebuild_web.py` parametrizado vía `CCE_PROJECT_DIR`, `CCE_NODE_BIN`, `CCE_BASE_PATH`, `CCE_SITE_URL`.
   - `scripts/run_admin_api.py`, `scripts/init_db.py`, `scripts/editor_acordes_server.py`, `scripts/editor_diapositivas_server.py` limpiados de `sys.path.insert`.

3. **Dependencias congeladas**
   - `requirements.lock.txt` actualizado.
   - `web/package-lock.json` trackeado.
   - Node fijado a `22.23.3`.

### B. Limpieza de legacy y muertos

- `better-sqlite3` y `@types/better-sqlite3` eliminados del frontend.
- `scripts/generar_semana.py` archivado como `archive/generar_semana_legacy.py`.
- Eliminado entry point `cce-m5-generar-semana` de `pyproject.toml`.
- Eliminadas units y drop-ins obsoletos de Mission Control.

### C. Infraestructura de backup

- Creado `scripts/systemd/cce-m5-backup-db.sh` dentro del repo.
- Unit/timer apuntan al script del repo.
- Eliminado el script externo en `~/.local/bin/`.

### D. CI/CD

- `.github/workflows/deploy.yml` actualizado:
  - Node `22.23.3` con cache de `package-lock.json`.
  - `npm ci` en lugar de `npm install`.
  - Python instala `requirements.lock.txt`.
  - Exportación con `PYTHONPATH` correcto.

### E. Documentación

- `docs/SDD/09-despliegue.md` actualizado con infraestructura actual y backup.
- `docs/SDD/10-migracion-nuevo-pc.md` ampliado con checks de verificación.
- `docs/SDD/11-operacion-y-troubleshooting.md` actualizado con comandos y variables de entorno.
- Creado este informe de auditoría.

---

## 3. Problemas resueltos

| Problema | Solución |
|---|---|
| Rutas absolutas en systemd | Units portables con `%h` |
| `sys.path.insert` en scripts | Eliminados; confianza en paquete editable / `PYTHONPATH` |
| `src/rebuild_web.py` con IP/rutas hardcodeadas | Parametrizado vía env |
| `package-lock.json` ignorado | Trackeado para reproducibilidad |
| Backup diario fuera del repo | Migrado a `scripts/systemd/cce-m5-backup-db.sh` |
| Pipeline Mission Control obsoleto | Eliminado |
| Tests con referencias antiguas a `rebuild_web` | Actualizado `tests/unit/test_rebuild_web.py` |
| Token expuesto en `requirements.lock.txt` | Línea editable con token eliminada antes del push |

---

## 4. Problemas pendientes o deuda técnica

| Problema | Prioridad | Notas |
|---|---|---|
| 42 errores `mypy` preexistentes | Media | No se introdujeron en este cambio; afectan `src/generators/presentacion/`, `src/web_admin/database.py`, `src/auto_rebuild_presentaciones.py`, `scripts/editor_diapositivas_server.py` (líneas no tocadas). |
| Build Astro muestra warnings de módulos `.mjs` dinámicos | Baja | El `dist` se genera y el servidor responde `200`. Es un artefacto conocido de Astro 4 con rutas dinámicas. |
| Repositorio pesa ~3,1 GB | Baja | Binarios duplicados en `presentaciones/`, `presentaciones_html/`, `web/public/`, `web/dist/`. Considerar `git-lfs` o archivado externo a largo plazo. |
| Frontend estático hace `fetch()` | Baja | `FormularioComentarios.jsx` y cancionero usan peticiones dinámicas. Ya existe comentarios proxy en admin; documentar limitaciones. |
| CORS/local IP al migrar | Media | Ajustar `CCE_SITE_URL` y `ADMIN_CORS_ORIGINS` en `.env` del nuevo PC. |
| `requirements.lock.txt` editable | Resuelto | Ahora no contiene la URL con token. |

---

## 5. Guía rápida de migración

Ver archivo detallado: `docs/SDD/10-migracion-nuevo-pc.md`.

### En el PC destino

```bash
# 1. Clonar
cd ~
git clone https://github.com/CC5M5/CCE-M5.git proyectos/CCE-M5-Web-Presentaciones
cd proyectos/CCE-M5-Web-Presentaciones

# 2. Python
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.lock.txt
.venv/bin/python -m pip install -e .

# 3. Node
nvm install 22.23.3
nvm use 22.23.3
cd web && npm install && npm run build && cd ..

# 4. Copiar .env (por canal seguro) y BD
cp /ruta/segura/.env .
chmod 600 .env
cp /ruta/segura/db.sqlite3 data/db.sqlite3

# 5. Instalar units systemd
cp config/systemd/user/*.service ~/.config/systemd/user/
cp config/systemd/user/*.timer ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable cce-m5-admin cce-m5-editor-diapositivas cce-m5-editor-acordes cce-m5-web cce-m5-backup-db.timer
systemctl --user start cce-m5-admin cce-m5-editor-diapositivas cce-m5-editor-acordes cce-m5-web

# 6. Verificar
ss -tlnp | grep -E '4321|4322|4323|4324'
curl http://localhost:4323/health
curl http://localhost:4322/
curl http://localhost:4324/
curl http://localhost:4321/
```

---

## 6. Conclusión

El proyecto **ya está preparado para migrar** a otro PC. Las fricciones principales (rutas absolutas, dependencias no congeladas, scripts con `sys.path`, restos de Mission Control) han sido resueltas. Los servicios funcionan correctamente en el PC origen y la documentación refleja el estado actual.

Queda deuda técnica `mypy` preexistente y optimización del tamaño del repo, pero ninguno de esos bloquea la migración.
