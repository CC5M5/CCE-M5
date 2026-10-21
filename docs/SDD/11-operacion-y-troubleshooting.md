# 11. Operación y Troubleshooting

## 11.1. Comandos útiles

```bash
# Estado de servicios
systemctl --user status cce-m5-admin cce-m5-editor-diapositivas cce-m5-editor-acordes cce-m5-web

# Logs en vivo
journalctl --user -u cce-m5-admin -f
journalctl --user -u cce-m5-editor-diapositivas -f
journalctl --user -u cce-m5-editor-acordes -f

# Puertos en uso
ss -tlnp | grep -E '4321|4322|4323|4324'

# Rebuild web manual
export CCE_PROJECT_DIR=/home/pciath/proyectos/CCE-M5-Web-Presentaciones
export CCE_NODE_BIN=/home/pciath/.nvm/versions/node/v22.23.3/bin
export CCE_BASE_PATH=/
export CCE_SITE_URL=http://192.168.68.244:4321
.venv/bin/python scripts/export_data_for_web.py
cd web
npm run build
cd ..

# Generar presentación desde consola
.venv/bin/python -c "from src.generators.generar_desde_composicion import GeneradorDesdeComposicion; GeneradorDesdeComposicion().generar_desde_presentacion('YYYY-MM-DD')"

# Backup manual de la BD
CCE_PROJECT_DIR=/home/pciath/proyectos/CCE-M5-Web-Presentaciones bash scripts/systemd/cce-m5-backup-db.sh
```

## 11.2. Problemas conocidos

| Problema | Solución rápida |
|---|---|
| Acordes en líneas separadas | Revisar `letra_con_acordes`; asegurar que la línea de acordes está justo encima de la línea de letra sin líneas vacías. |
| Canción asignada no aparece en presentación | Verificar que existe slide `cancion_<id>` para el momento; si no, editar la canción para que `auto_rebuild` la cree. |
| 404 en presentación publicada | Revisar `ruta_web` relativa en BD, re-exportar JSON y rebuild. |
| Workflow no avanza | Revisar logs en `workflow_logs`; hacer rollback y retry. |
| Servicio falla con `ModuleNotFoundError: No module named 'src'` | Comprobar que `PYTHONPATH` apunta al directorio raíz del proyecto o que el paquete editable está instalado (`pip install -e .`). |

## 11.3. Backups

- Backup automático antes de regenerar una fecha existente: `backups/YYYY-MM-DD_TIMESTAMP/`.
- Backup diario de la BD: `$HOME/.config/cce-m5/backups/db/db_YYYYMMDD_HHMMSS.sqlite3.gz` (vía `cce-m5-backup-db.timer`).
- Backup manual: `bash scripts/systemd/cce-m5-backup-db.sh`.
- Backup de estado completo para auditoría: `backups/auditoria_pre_correcciones_YYYYMMDD_HHMMSS/`.

## 11.4. Mantenimiento recomendado

- Revisar logs de servicios semanalmente.
- Limpiar `backups/` antiguos mensualmente.
- Actualizar `data/schema_full.sql` tras cualquier cambio de esquema.
- Congelar `requirements.lock.txt` y `web/package-lock.json` tras instalar/actualizar dependencias.
- Verificar que no hay secretos en `data/.admin_jwt_secret`, `.env` o unidades systemd al compartir capturas de configuración.
