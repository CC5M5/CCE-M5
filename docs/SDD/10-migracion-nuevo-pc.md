# 10. Migración a Nuevo PC

## 10.1. Requisitos del PC destino

- Linux (preferiblemente Debian/Ubuntu).
- Python 3.13.
- Node.js ≥ 22 (node del sistema o nvm; verificado también con 24.22.1).
- `git`, `npm`, `sqlite3`.
- Usuario sin privilegios para ejecutar los servicios.
- Conexión a Internet para clonar, instalar dependencias y publicar en GitHub Pages (opcional).

## 10.2. Checklist de migración

### En el PC origen

1. Hacer backup online de `data/db.sqlite3`:
   ```bash
   cd ~/proyectos/CCE-M5-Web-Presentaciones
   .venv/bin/python - <<'PY'
   import sqlite3, datetime, os, shutil
   src='data/db.sqlite3'
   conn=sqlite3.connect(src); conn.execute('PRAGMA wal_checkpoint(TRUNCATE)'); conn.close()
   ts=datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
   os.makedirs(f'backups/pre_migracion_{ts}', exist_ok=True)
   shutil.copy2(src, f'backups/pre_migracion_{ts}/db.sqlite3')
   print('Backup DB creado.')
   PY
   ```
2. Verificar que `requirements.lock.txt` y `web/package-lock.json` están actualizados y commiteados.
3. Verificar que `data/schema_full.sql` está actualizado.
4. Revisar `.env` y anotar los valores que el destino necesitará: `CCE_ADMIN_JWT_SECRET`, `CCE_ADMIN_DEFAULT_PASSWORD`, `GITHUB_TOKEN_CC5M5`, etc.

### En el PC destino

1. Clonar el repositorio en `~/proyectos/CCE-M5-Web-Presentaciones`:
   ```bash
   git clone https://github.com/CC5M5/CCE-M5.git ~/proyectos/CCE-M5-Web-Presentaciones
   cd ~/proyectos/CCE-M5-Web-Presentaciones
   ```
2. Crear virtualenv e instalar dependencias congeladas:
   ```bash
   python3 -m venv .venv
   .venv/bin/python -m pip install -r requirements.lock.txt
   .venv/bin/python -m pip install -e .
   ```
3. Asegurar Node ≥ 22 (node del sistema o nvm):
   ```bash
   node --version   # debe ser >= 22
   cd web && npm install
   cd ..
   ```
   Con nvm (alternativa): `nvm install 22.23.3 && nvm use 22.23.3`.
4. Restaurar `data/db.sqlite3` desde el backup.
5. Crear `.env` con los valores del origen (mínimo recomendado):
   ```ini
   CCE_ADMIN_JWT_SECRET=<tu-secreto-seguro>
   CCE_ADMIN_DEFAULT_PASSWORD=<tu-password>
   GITHUB_TOKEN_CC5M5=<tu-token-github>
   # Ajustar si node no está en el path habitual:
   CCE_NODE_BIN=/usr/bin
   # Opcional: IP/nombre del servidor destino para CORS y rebuild
   CCE_SITE_URL=http://<IP_LOCAL>:4321
   ADMIN_CORS_ORIGINS=http://localhost:4321,http://<IP_LOCAL>:4321,http://<IP_LOCAL>:4323
   ```
   Asegurar permisos restrictivos: `chmod 600 .env`.
6. Instalar units systemd en `~/.config/systemd/user/`:
   ```bash
   mkdir -p ~/.config/systemd/user
   cp config/systemd/user/*.service ~/.config/systemd/user/
   cp config/systemd/user/*.timer ~/.config/systemd/user/
   ```
7. Recargar, habilitar y arrancar servicios:
   ```bash
   systemctl --user daemon-reload
   systemctl --user enable --now cce-m5-admin cce-m5-web cce-m5-healthcheck.timer cce-m5-backup-db.timer
   ```
8. Verificar puertos:
   ```bash
   ss -tlnp | grep -E '4321|4323'
   ```
9. Probar un workflow de prueba con una fecha pasada en modo borrador antes de tocar datos reales.

## 10.3. Checks de verificación tras arrancar

| Check | Comando | Resultado esperado |
|---|---|---|
| Admin API responde | `curl http://localhost:4323/health` | JSON con `status: ok` |
| Editor de acordes responde | `curl http://localhost:4323/editor-acordes/` | HTML |
| Editor de diapositivas responde | `curl http://localhost:4323/editor-diapositivas/` | HTML |
| Web local sirve | `curl http://localhost:4321/` | HTML |
| Login admin funciona | Probar en navegador | Entra al panel |
| Build Astro OK | `cd web && npm run build` | `dist/` generado |
| Backup funciona | `bash scripts/systemd/cce-m5-backup-db.sh` | Crea backup en `~/.config/cce-m5/backups/db/` |

## 10.4. Posibles problemas

| Síntoma | Causa probable | Solución |
|---|---|---|
| Admin no arranca en 4323 | `PYTHONPATH` no apunta al proyecto o `.env` falta | Revisar `Environment=PYTHONPATH=%h/proyectos/CCE-M5-Web-Presentaciones` y que `.env` exista. |
| Build Astro falla | `package-lock.json` ausente o Node < 22 | Reinstalar dependencias con `npm install` (Node ≥ 22 verificado, incluida la 24.x). |
| Web local no sirve | `web/dist` no existe | Ejecutar `cd web && npm run build`. |
| Login admin falla | JWT secret diferente | Sincronizar `.env` o borrar `data/.admin_jwt_secret` para regenerarlo. |
| `src` no se encuentra | No se instaló el paquete editable | Ejecutar `.venv/bin/python -m pip install -e .` |
| Matching no encuentra BD | `data/matching_config.json` tenía ruta absoluta antigua | El campo `db_path` se ha eliminado del JSON; el motor usa `settings.db_path`. |

## 10.5. Diferencias con la configuración anterior

- Las units están en `config/systemd/user/` y usan `%h` en lugar de rutas absolutas de `/home/pciath/`.
- Los editores de acordes y diapositivas ya no tienen unidades independientes; viven dentro de `cce-m5-admin.service` en el puerto 4323.
- El pipeline de Mission Control ha sido eliminado.
- El backup diario se ejecuta desde `scripts/systemd/cce-m5-backup-db.sh` en el repo.
- `generar_semana.py` ha sido archivado como `archive/generar_semana_legacy.py`.
