# 11. Operación y Troubleshooting

## 11.1. Comandos útiles

```bash
# Estado de servicios
systemctl --user status cce-m5-admin cce-m5-editor-diapositivas cce-m5-web

# Logs
journalctl --user -u cce-m5-admin -f
journalctl --user -u cce-m5-editor-diapositivas -f

# Puertos en uso
ss -tlnp | grep -E '4321|4322|4323|4324'

# Rebuild web manual
cd /home/pciath/proyectos/CCE-M5-Web-Presentaciones
.venv/bin/python scripts/export_data_for_web.py
cd web
BASE_PATH=/ SITE_URL=http://192.168.68.244:4321 npm run build

# Generar presentación desde consola
.venv/bin/python -c "from src.generators.generar_desde_composicion import GeneradorDesdeComposicion; GeneradorDesdeComposicion().generar_desde_presentacion('YYYY-MM-DD')"
```

## 11.2. Problemas conocidos

| Problema | Solución rápida |
|---|---|
| Acordes en líneas separadas | Revisar `letra_con_acordes`; asegurar que la línea de acordes está justo encima de la línea de letra sin líneas vacías. |
| Canción asignada no aparece en presentación | Verificar que existe slide `cancion_<id>` para el momento; si no, editar la canción para que `auto_rebuild` la cree. |
| 404 en presentación publicada | Revisar `ruta_web` relativa en BD, re-exportar JSON y rebuild. |
| Workflow no avanza | Revisar logs en `workflow_logs`; hacer rollback y retry. |

## 11.3. Backups

- Backup automático antes de regenerar una fecha existente: `backups/YYYY-MM-DD_TIMESTAMP/`.
- Backup manual de la BD: copiar `data/db.sqlite3`.
- Backup de estado completo para auditoría: `backups/auditoria_pre_correcciones_YYYYMMDD_HHMMSS/`.

## 11.4. Mantenimiento recomendado

- Revisar logs de servicios semanalmente.
- Limpiar `backups/` antiguos mensualmente.
- Actualizar `schema_full.sql` tras cualquier cambio de esquema.
- Congelar `requirements.lock.txt` tras instalar nuevas dependencias.

