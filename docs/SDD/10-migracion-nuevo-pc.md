# 10. Migración a Nuevo PC

## 10.1. Requisitos del PC destino

- Linux (preferiblemente Debian/Ubuntu).
- Python 3.13.
- Node.js 22.23.3 (gestionar con nvm).
- `git`, `npm`, `sqlite3`.
- Usuario sin privilegios para ejecutar los servicios.

## 10.2. Checklist de migración

### En el PC origen

1. Hacer backup de `data/db.sqlite3`, `data/db.sqlite3-wal`, `data/db.sqlite3-shm`.
2. Generar `requirements.lock.txt` con `pip freeze`.
3. Verificar que `data/schema_full.sql` está actualizado.
4. Copiar las units systemd corregidas.
5. Copiar `.env` de forma segura (no por git).

### En el PC destino

1. Clonar el repositorio.
2. Crear virtualenv e instalar dependencias:
   ```bash
   python3 -m venv .venv
   .venv/bin/python -m pip install -r requirements.lock.txt
   ```
3. Instalar Node 22.23.3:
   ```bash
   nvm install 22.23.3
   nvm use 22.23.3
   cd web && npm install
   ```
4. Restaurar `data/db.sqlite3` desde backup.
5. Copiar `.env` al proyecto.
6. Instalar units systemd en `~/.config/systemd/user/`:
   - `cce-m5-admin.service`
   - `cce-m5-editor-diapositivas.service`
   - `cce-m5-web.service`
7. Ejecutar:
   ```bash
   systemctl --user daemon-reload
   systemctl --user enable cce-m5-admin cce-m5-editor-diapositivas cce-m5-web
   systemctl --user start cce-m5-admin cce-m5-editor-diapositivas cce-m5-web
   ```
8. Verificar puertos:
   ```bash
   ss -tlnp | grep -E '4321|4322|4323|4324'
   ```
9. Probar un workflow de prueba con una fecha pasada en modo borrador antes de tocar datos reales.

## 10.3. Posibles problemas

| Síntoma | Causa probable | Solución |
|---|---|---|
| Admin no arranca en 4323 | Puerto ocupado por proceso manual | Matar proceso antiguo o reiniciar. |
| Build Astro falla | Node 24 o `package-lock.json` ausente | Usar Node 22.23.3 y `npm install`. |
| Web local no sirve | `web/dist` no existe | Ejecutar `npm run build` localmente. |
| Login admin falla | JWT secret diferente | Sincronizar `.env` o borrar `data/.admin_jwt_secret`. |

