# 10. Migración a Nuevo PC

## 10.1. Requisitos del PC destino

- Linux (preferiblemente Debian/Ubuntu).
- Python 3.13.
- Node.js 22.23.3 (gestionar con nvm).
- `git`, `npm`, `sqlite3`.
- Usuario sin privilegios para ejecutar los servicios.

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
4. Copiar las units desde `config/systemd/user/` al destino.
5. Copiar `.env` de forma segura (no por git).

### En el PC destino

1. Clonar el repositorio en `~/proyectos/CCE-M5-Web-Presentaciones`.
2. Crear virtualenv e instalar dependencias congeladas:
   ```bash
   cd ~/proyectos/CCE-M5-Web-Presentaciones
   python3 -m venv .venv
   .venv/bin/python -m pip install -r requirements.lock.txt
   .venv/bin/python -m pip install -e .
   ```
3. Instalar Node 22.23.3:
   ```bash
   nvm install 22.23.3
   nvm use 22.23.3
   cd web && npm install
   ```
4. Restaurar `data/db.sqlite3` desde el backup.
5. Copiar `.env` al proyecto (`chmod 600 .env`).
6. Instalar units systemd en `~/.config/systemd/user/`:
   ```bash
   mkdir -p ~/.config/systemd/user
   cp config/systemd/user/*.service ~/.config/systemd/user/
   cp config/systemd/user/*.timer ~/.config/systemd/user/
   ```
7. Recargar, habilitar y arrancar servicios:
   ```bash
   systemctl --user daemon-reload
   systemctl --user enable cce-m5-admin cce-m5-editor-diapositivas cce-m5-editor-acordes cce-m5-web cce-m5-backup-db.timer
   systemctl --user start cce-m5-admin cce-m5-editor-diapositivas cce-m5-editor-acordes cce-m5-web cce-m5-backup-db.timer
   ```
8. Verificar puertos:
   ```bash
   ss -tlnp | grep -E '4321|4322|4323|4324'
   ```
9. Probar un workflow de prueba con una fecha pasada en modo borrador antes de tocar datos reales.

## 10.3. Checks de verificación tras arrancar

| Check | Comando | Resultado esperado |
|---|---|---|
| Admin API responde | `curl http://localhost:4323/health` | JSON con `status: ok` |
| Editor acordes responde | `curl http://localhost:4322/` | HTML |
| Editor diapositivas responde | `curl http://localhost:4324/` | HTML |
| Web local sirve | `curl http://localhost:4321/` | HTML |
| Login admin funciona | Probar en navegador | Entra al panel |
| Build Astro OK | `cd web && npm run build` | `dist/` generado |

## 10.4. Posibles problemas

| Síntoma | Causa probable | Solución |
|---|---|---|
| Admin no arranca en 4323 | `PYTHONPATH` no apunta al proyecto o `.env` falta | Revisar `Environment=PYTHONPATH=%h/proyectos/CCE-M5-Web-Presentaciones` y que `.env` exista. |
| Build Astro falla | Node 24 o `package-lock.json` ausente | Usar Node 22.23.3 y `npm install`. |
| Web local no sirve | `web/dist` no existe | Ejecutar `cd web && npm run build`. |
| Login admin falla | JWT secret diferente | Sincronizar `.env` o borrar `data/.admin_jwt_secret`. |
| `src` no se encuentra | No se instaló el paquete editable | Ejecutar `.venv/bin/python -m pip install -e .` |

## 10.5. Diferencias con la configuración anterior

- Las units ya no usan rutas absolutas de `/home/pciath/`.
- El pipeline de Mission Control ha sido eliminado.
- El backup diario se ejecuta desde `scripts/systemd/cce-m5-backup-db.sh` en el repo.
- `generar_semana.py` ha sido archivado como `archive/generar_semana_legacy.py`.
