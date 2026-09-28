"""Motor del workflow manual de generación de presentaciones.

Cada paso es una función pura que recibe el workflow y un contexto, y
devuelve un resultado con el nuevo estado, datos y mensajes de log.
"""

from __future__ import annotations

import json
import logging
import shutil
import sys
import traceback
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

PROJECT_DIR = Path(__file__).parent.parent.parent.resolve()
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

from src.db_manager import get_connection
from src.generators.pdf_musicos import generar_hoja_musicos
from src.generators.presentacion_html import GeneradorPresentacionHTML
from src.matching_engine import MatchingEngine
from src.scrapers.koinonia_scraper import KoinoniaScraper
from src.scrapers.ciudadredonda_scraper import obtener_lecturas_ciudadredonda
from src.web_admin.config import BACKUPS_DIR, PROJECT_DIR
from src.web_admin.database import (
    add_workflow_log,
    create_backup_record,
    get_workflow_logs,
    get_workflow_run,
    next_step,
    step_index,
    update_workflow_step,
    WORKFLOW_STEPS,
)

logger = logging.getLogger(__name__)

MOMENTOS_ES = [
    "Entrada",
    "Perdón",
    "Gloria",
    "Salmo",
    "Aleluya",
    "Ofertorio",
    "Santo",
    "Padre Nuestro",
    "Paz",
    "Comunión",
    "Canto a María",
    "Despedida",
]

MOMENTOS_KEY = [
    "entrada",
    "perdon",
    "gloria",
    "salmo",
    "aleluya",
    "ofertorio",
    "santo",
    "padre_nuestro",
    "paz",
    "comunion",
    "maria",
    "despedida",
]

MOMENTO_A_KEY = dict(zip(MOMENTOS_ES, MOMENTOS_KEY))


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _backup_existing_assets(
    workflow_id: int,
    fecha_domingo: str,
    steps_data: Dict[str, Any],
) -> Tuple[List[str], Optional[str]]:
    """Guarda una copia de seguridad de los archivos existentes de una fecha."""
    paths_to_backup = []

    # Archivos de presentaciones/
    pptx = PROJECT_DIR / "presentaciones" / f"{fecha_domingo}_celebracion.pptx"
    pdf_fieles = PROJECT_DIR / "presentaciones" / f"{fecha_domingo}_fieles.pdf"
    pdf_musicos = PROJECT_DIR / "presentaciones" / f"{fecha_domingo}_hoja_musicos.pdf"
    for p in [pptx, pdf_fieles, pdf_musicos]:
        if p.exists():
            paths_to_backup.append(str(p))

    # Carpeta de presentaciones_html/
    html_dir = PROJECT_DIR / "presentaciones_html" / f"{fecha_domingo}_presentacion"
    if html_dir.exists():
        for child in html_dir.iterdir():
            paths_to_backup.append(str(child))

    # Asignación guardada
    asign_html = PROJECT_DIR / "asignaciones" / f"asignacion-{fecha_domingo}.html"
    if asign_html.exists():
        paths_to_backup.append(str(asign_html))

    if not paths_to_backup:
        return [], None

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    backup_dir = BACKUPS_DIR / f"{fecha_domingo}_{timestamp}"
    backup_dir.mkdir(parents=True, exist_ok=True)

    copied = []
    for src in paths_to_backup:
        src_path = Path(src)
        if not src_path.exists():
            continue
        if src_path.is_dir():
            dst = backup_dir / src_path.name
            shutil.copytree(src_path, dst, dirs_exist_ok=True)
        else:
            dst = backup_dir / src_path.name
            shutil.copy2(src_path, dst)
        copied.append(str(dst))

    create_backup_record(workflow_id, fecha_domingo, str(backup_dir), paths_to_backup)
    logger.info("Backup creado para %s en %s", fecha_domingo, backup_dir)
    return paths_to_backup, str(backup_dir)


def run_step(
    workflow_id: int,
    action: str,
    payload_data: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Ejecuta una transición de paso del workflow.

    Devuelve un dict con:
        - success: bool
        - workflow: dict actualizado
        - logs: list de logs
        - can_advance: bool
        - next_step_name: str|None
        - warning: str|None
    """
    data = payload_data if isinstance(payload_data, dict) else {}
    workflow = get_workflow_run(workflow_id)
    if not workflow:
        return {"success": False, "error": "Workflow no encontrado"}

    current_step = workflow["current_step"]
    steps_data = workflow["steps_data"]

    if action == "rollback":
        return _do_rollback(workflow)

    if action not in ("next", "retry"):
        return {"success": False, "error": f"Acción no válida: {action}"}

    handler_name = f"handle_{current_step}"
    handler = globals().get(handler_name)
    if not handler:
        return {"success": False, "error": f"No hay handler para el paso {current_step}"}

    try:
        result = handler(workflow, data)
    except Exception as exc:
        msg = f"Error en paso {current_step}: {exc}"
        logger.exception(msg)
        add_workflow_log(workflow_id, current_step, msg, level="error")
        return {"success": False, "error": msg, "traceback": traceback.format_exc()}

    if not result.get("success"):
        return result

    new_steps_data = result.get("steps_data", steps_data)
    new_step = result.get("next_step", current_step)
    status = "done" if new_step == "done" else new_step
    completed_at = _now() if new_step == "done" else None

    update_workflow_step(
        workflow_id,
        status=status,
        current_step=new_step,
        steps_data=new_steps_data,
        completed_at=completed_at,
    )

    for log_entry in result.get("logs", []):
        add_workflow_log(
            workflow_id,
            log_entry.get("step", current_step),
            log_entry["message"],
            level=log_entry.get("level", "info"),
        )

    updated = get_workflow_run(workflow_id)
    logs = get_workflow_logs(workflow_id)
    can_advance = updated["current_step"] != "done" and next_step(updated["current_step"]) is not None

    return {
        "success": True,
        "workflow": updated,
        "logs": logs,
        "can_advance": can_advance,
        "next_step_name": next_step(updated["current_step"]),
        "warning": result.get("warning"),
    }


def _do_rollback(workflow: Dict[str, Any]) -> Dict[str, Any]:
    current = workflow["current_step"]
    idx = step_index(current)
    if idx <= 0:
        return {"success": False, "error": "No se puede retroceder más"}
    prev = WORKFLOW_STEPS[idx - 1]
    update_workflow_step(
        workflow["id"],
        status=prev,
        current_step=prev,
        steps_data=workflow["steps_data"],
    )
    add_workflow_log(workflow["id"], prev, f"Retrocedido desde {current} a {prev}")
    updated = get_workflow_run(workflow["id"])
    return {
        "success": True,
        "workflow": updated,
        "logs": get_workflow_logs(workflow["id"]),
        "can_advance": True,
        "next_step_name": next_step(prev),
    }


# ---------------------------------------------------------------------------
# Handlers de cada paso
# ---------------------------------------------------------------------------


def handle_init(workflow: Dict[str, Any], data: Dict[str, Any]) -> Dict[str, Any]:
    """Paso inicial: simplemente avanza a fetch_lectures."""
    return {
        "success": True,
        "next_step": "fetch_lectures",
        "steps_data": workflow["steps_data"],
        "logs": [{"step": "init", "message": "Workflow iniciado"}],
    }


def handle_fetch_lectures(
    workflow: Dict[str, Any], data: Dict[str, Any]
) -> Dict[str, Any]:
    """Scrapea lecturas de Koinonia; si falla, usa Ciudad Redonda."""
    fecha = workflow["fecha_domingo"]
    steps_data = dict(workflow["steps_data"])

    lecturas, fuente = None, None
    errores = []
    for scraper_name, scraper_call in [
        ("koinonia", lambda f: KoinoniaScraper().obtener_lecturas(datetime.strptime(f, "%Y-%m-%d"))),
        ("ciudad_redonda", lambda f: obtener_lecturas_ciudadredonda(f)),
    ]:
        try:
            lecturas = scraper_call(fecha)
            if lecturas:
                fuente = scraper_name
                break
        except Exception as exc:
            err_msg = f"{scraper_name}: {exc}"
            errores.append(err_msg)
            logger.warning("Scraper %s falló para %s: %s", scraper_name, fecha, exc)

    warning = None
    if lecturas is None:
        warning = (
            f"No se pudieron obtener lecturas automáticamente. "
            f"Errores: {'; '.join(errores) if errores else 'sin respuesta'}. "
            f"Puedes introducirlas manualmente en el siguiente paso."
        )
        logger.warning(warning)
        lecturas = {
            "fecha": fecha,
            "domingo": "",
            "temporada": "",
            "ciclo": "",
            "color_liturgico": "verde",
            "primera_lectura_cita": "",
            "primera_lectura_texto": "",
            "salmo_cita": "",
            "salmo_antifona": "",
            "salmo_texto": "",
            "segunda_lectura_cita": "",
            "segunda_lectura_texto": "",
            "evangelio_cita": "",
            "evangelio_texto": "",
            "fuente_scraping": "manual",
        }
        fuente = "manual"

    steps_data["lecturas"] = lecturas
    steps_data["lecturas_fuente"] = fuente

    return {
        "success": True,
        "next_step": "verify_lectures",
        "steps_data": steps_data,
        "logs": [
            {
                "step": "fetch_lectures",
                "message": f"Lecturas obtenidas desde {fuente} para {fecha}" if fuente != "manual" else "Lecturas no disponibles; se habilita entrada manual",
            }
        ],
        "warning": warning,
    }


def handle_verify_lectures(
    workflow: Dict[str, Any], data: Dict[str, Any]
) -> Dict[str, Any]:
    """Permite al admin corregir lecturas manualmente."""
    steps_data = dict(workflow["steps_data"])
    lecturas = steps_data.get("lecturas", {})

    # Aplicar correcciones enviadas por el admin
    correcciones = data.get("lecturas", {})
    for key, value in correcciones.items():
        if value is not None:
            lecturas[key] = value

    steps_data["lecturas"] = lecturas
    steps_data["lecturas_verificadas"] = True

    # Guardar lecturas en la tabla principal
    try:
        _save_lecturas_to_db(workflow["fecha_domingo"], lecturas)
    except Exception as exc:
        return {"success": False, "error": f"No se pudieron guardar las lecturas: {exc}"}

    return {
        "success": True,
        "next_step": "propose_songs",
        "steps_data": steps_data,
        "logs": [
            {
                "step": "verify_lectures",
                "message": "Lecturas verificadas y guardadas",
            }
        ],
    }


def _save_lecturas_to_db(fecha: str, lecturas: Dict[str, Any]) -> None:
    """Inserta o actualiza lecturas en la tabla lecturas de db.sqlite3."""
    with get_connection() as conn:
        with conn:
            existing = conn.execute(
                "SELECT id FROM lecturas WHERE fecha = ?", (fecha,)
            ).fetchone()

            fields = {
                "domingo": lecturas.get("domingo", ""),
                "temporada": lecturas.get("temporada", ""),
                "ciclo": lecturas.get("ciclo", ""),
                "color_liturgico": lecturas.get("color_liturgico", "verde"),
                "primera_lectura_cita": lecturas.get("primera_lectura_cita", ""),
                "primera_lectura_texto": lecturas.get("primera_lectura_texto", ""),
                "salmo_cita": lecturas.get("salmo_cita", ""),
                "salmo_antifona": lecturas.get("salmo_antifona", ""),
                "salmo_texto": lecturas.get("salmo_texto", ""),
                "segunda_lectura_cita": lecturas.get("segunda_lectura_cita", ""),
                "segunda_lectura_texto": lecturas.get("segunda_lectura_texto", ""),
                "evangelio_cita": lecturas.get("evangelio_cita", ""),
                "evangelio_texto": lecturas.get("evangelio_texto", ""),
                "fuente_scraping": lecturas.get("fuente_scraping", "koinonia"),
            }

            if existing:
                set_clause = ", ".join(f"{k} = ?" for k in fields)
                values = list(fields.values()) + [fecha]
                conn.execute(
                    f"UPDATE lecturas SET {set_clause}, fecha_creacion = CURRENT_TIMESTAMP WHERE fecha = ?",
                    values,
                )
            else:
                cols = ", ".join(fields.keys())
                placeholders = ", ".join(["?"] * len(fields))
                conn.execute(
                    f"INSERT INTO lecturas (fecha, {cols}) VALUES (?, {placeholders})",
                    [fecha] + list(fields.values()),
                )


def proponer_canciones_para_dia(fecha: str) -> Dict[str, Any]:
    """Genera propuestas de canciones para cada momento litúrgico del día.

    Usa el motor de matching contra las lecturas del día y asigna la mejor
    canción disponible a cada momento, evitando duplicados si es posible.
    """
    with get_connection() as conn:
        row = conn.execute("SELECT id FROM lecturas WHERE fecha = ?", (fecha,)).fetchone()
        if not row:
            raise ValueError(f"No hay lecturas guardadas para {fecha}")
        lectura_id = row["id"]

    engine = MatchingEngine()
    matches = engine.encontrar_canciones_para_lectura(lectura_id, limite=30, score_minimo=0.0)

    # Agrupar por momento litúrgico
    por_momento: Dict[str, List[Dict[str, Any]]] = {}
    for m in matches:
        momento = m.get("momento_liturgico", "general")
        por_momento.setdefault(momento, []).append(m)

    # Orden de preferencia por momento
    propuestas = {}
    usadas = set()

    # Para cada momento del día, buscar la mejor canción del mismo momento,
    # fallback a general, y finalmente la primera disponible.
    for momento_es, momento_key in zip(MOMENTOS_ES, MOMENTOS_KEY):
        candidatas = []
        # 1. canciones cuyo momento coincide exactamente
        if momento_key in por_momento:
            candidatas.extend(por_momento[momento_key])
        # 2. canciones de momento 'general'
        if "general" in por_momento:
            candidatas.extend(por_momento["general"])
        # 3. cualquier otra candidata
        for lista in por_momento.values():
            candidatas.extend(lista)

        seleccionada = None
        for c in candidatas:
            cid = c["cancion_id"]
            if cid not in usadas:
                seleccionada = c
                usadas.add(cid)
                break
        if not seleccionada and candidatas:
            seleccionada = candidatas[0]
            usadas.add(seleccionada["cancion_id"])

        propuestas[momento_es] = seleccionada or {
            "cancion_id": None,
            "titulo": "(sin propuesta)",
            "score": 0.0,
        }

    return propuestas


def handle_propose_songs(
    workflow: Dict[str, Any], data: Dict[str, Any]
) -> Dict[str, Any]:
    """Propone canciones para los 12 momentos litúrgicos."""
    fecha = workflow["fecha_domingo"]
    steps_data = dict(workflow["steps_data"])

    try:
        propuestas = proponer_canciones_para_dia(fecha)
    except Exception as exc:
        return {"success": False, "error": f"Error al proponer canciones: {exc}"}

    steps_data["canciones_propuestas"] = propuestas

    return {
        "success": True,
        "next_step": "verify_songs",
        "steps_data": steps_data,
        "logs": [
            {
                "step": "propose_songs",
                "message": f"Propuestas generadas para {len(propuestas)} momentos",
            }
        ],
    }


def handle_verify_songs(
    workflow: Dict[str, Any], data: Dict[str, Any]
) -> Dict[str, Any]:
    """Permite al admin ajustar la asignación de canciones."""
    steps_data = dict(workflow["steps_data"])
    propuestas = steps_data.get("canciones_propuestas", {})

    ajustes = data.get("canciones", {})
    for momento, cancion_id in ajustes.items():
        if momento in propuestas:
            propuestas[momento]["cancion_id"] = cancion_id
        else:
            propuestas[momento] = {"cancion_id": cancion_id, "momento": momento}

    steps_data["canciones_propuestas"] = propuestas
    steps_data["canciones_verificadas"] = True

    # Convertir a formato canciones_json para la tabla presentaciones
    canciones_json = {}
    for momento, info in propuestas.items():
        key = MOMENTO_A_KEY.get(momento, momento.lower().replace(" ", "_").replace("á", "a").replace("é", "e").replace("í", "i").replace("ó", "o").replace("ú", "u").replace("ñ", "n"))
        canciones_json[key] = info.get("cancion_id")

    steps_data["canciones_json"] = canciones_json

    return {
        "success": True,
        "next_step": "generate_assets",
        "steps_data": steps_data,
        "logs": [
            {"step": "verify_songs", "message": "Asignación de canciones confirmada"}
        ],
    }


def handle_generate_assets(
    workflow: Dict[str, Any], data: Dict[str, Any]
) -> Dict[str, Any]:
    """Genera PPTX, PDF músicos y HTML estático."""
    fecha = workflow["fecha_domingo"]
    steps_data = dict(workflow["steps_data"])

    # Hacer backup si ya existen archivos previos
    backed_paths, backup_dir = _backup_existing_assets(
        workflow["id"], fecha, steps_data
    )
    warning = None
    if backup_dir:
        warning = f"Se ha creado backup en {backup_dir}"

    canciones_json = steps_data.get("canciones_json", {})

    # Obtener lectura_id recién guardada
    lectura_id = None
    with get_connection() as conn:
        row = conn.execute("SELECT id FROM lecturas WHERE fecha = ?", (fecha,)).fetchone()
        if row:
            lectura_id = row["id"]
    if not lectura_id:
        return {"success": False, "error": f"No se encontró lectura guardada para {fecha}"}

    try:
        gen = GeneradorPresentacionHTML()
        bundle_dir = gen.generar(
            fecha=fecha,
            lectura_id=lectura_id,
            canciones_ids=canciones_json,
        )
    except Exception as exc:
        return {"success": False, "error": f"Error generando presentación: {exc}"}

    try:
        # Generar hoja de músicos
        result_pdf = generar_hoja_musicos(
            fecha_domingo=fecha,
            canciones_por_momento=canciones_json,
        )
    except Exception as exc:
        return {"success": False, "error": f"Error generando hoja de músicos: {exc}"}

    # Copiar PPTX/PDF al directorio presentaciones/ para descarga
    presentaciones_dir = PROJECT_DIR / "presentaciones"
    presentaciones_dir.mkdir(parents=True, exist_ok=True)
    pptx_src = bundle_dir / f"{fecha}_presentacion.pptx"
    pdf_src = bundle_dir / f"{fecha}_presentacion.pdf"
    pptx_dst = presentaciones_dir / f"{fecha}_celebracion.pptx"
    pdf_fieles_dst = presentaciones_dir / f"{fecha}_fieles.pdf"

    if pptx_src.exists():
        shutil.copy2(pptx_src, pptx_dst)
    if pdf_src.exists():
        shutil.copy2(pdf_src, pdf_fieles_dst)

    steps_data["assets"] = {
        "bundle_dir": str(bundle_dir),
        "pptx": str(pptx_dst) if pptx_src.exists() else None,
        "pdf_fieles": str(pdf_fieles_dst) if pdf_src.exists() else None,
        "pdf_musicos": result_pdf if isinstance(result_pdf, str) else None,
    }

    logs = [
        {"step": "generate_assets", "message": f"Presentación generada: {bundle_dir}"}
    ]
    if backup_dir:
        logs.append(
            {
                "step": "generate_assets",
                "message": f"Backup creado en {backup_dir}",
                "level": "info",
            }
        )

    return {
        "success": True,
        "next_step": "publish",
        "steps_data": steps_data,
        "logs": logs,
        "warning": warning,
    }


def handle_publish(workflow: Dict[str, Any], data: Dict[str, Any]) -> Dict[str, Any]:
    """Publica la presentación: sync HTML a web/dist y build de Astro."""
    fecha = workflow["fecha_domingo"]
    steps_data = dict(workflow["steps_data"])

    try:
        # Ejecutar sync de HTML a web/dist
        import subprocess

        sync_script = PROJECT_DIR / "scripts" / "sync_presentaciones_html.py"
        result = subprocess.run(
            ["python3", str(sync_script)],
            cwd=PROJECT_DIR,
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode != 0:
            return {
                "success": False,
                "error": f"sync_presentaciones_html falló: {result.stderr}",
            }

        # Build de Astro (puede tardar)
        result_build = subprocess.run(
            ["npm", "run", "build"],
            cwd=PROJECT_DIR / "web",
            capture_output=True,
            text=True,
            check=False,
        )
        if result_build.returncode != 0:
            return {
                "success": False,
                "error": f"astro build falló: {result_build.stderr}",
            }

    except Exception as exc:
        return {"success": False, "error": f"Error en publicación: {exc}"}

    # Guardar en tabla presentaciones
    try:
        _save_presentacion_to_db(workflow, steps_data)
    except Exception as exc:
        return {"success": False, "error": f"Error guardando presentación en BD: {exc}"}

    steps_data["publicado"] = True
    return {
        "success": True,
        "next_step": "done",
        "steps_data": steps_data,
        "logs": [
            {"step": "publish", "message": "Web reconstruida y presentación publicada"}
        ],
    }


def _save_presentacion_to_db(
    workflow: Dict[str, Any], steps_data: Dict[str, Any]
) -> None:
    fecha = workflow["fecha_domingo"]
    lecturas = steps_data.get("lecturas", {})
    canciones_json = steps_data.get("canciones_json", {})
    assets = steps_data.get("assets", {})

    with get_connection() as conn:
        with conn:
            lectura_row = conn.execute(
                "SELECT id FROM lecturas WHERE fecha = ?", (fecha,)
            ).fetchone()
            lectura_id = lectura_row["id"] if lectura_row else None

            ruta_pptx = assets.get("pptx")
            ruta_pdf_fieles = assets.get("pdf_fieles")
            ruta_pdf_musicos = assets.get("pdf_musicos")
            ruta_web = assets.get("bundle_dir")

            existing = conn.execute(
                "SELECT id FROM presentaciones WHERE fecha_domingo = ?", (fecha,)
            ).fetchone()

            if existing:
                conn.execute(
                    """
                    UPDATE presentaciones
                    SET lectura_id = ?, canciones_json = ?, ruta_pptx = ?, ruta_pdf_fieles = ?,
                        ruta_pdf_musicos = ?, ruta_web = ?, estado = 'publicada', fecha_creacion = CURRENT_TIMESTAMP
                    WHERE fecha_domingo = ?
                    """,
                    (
                        lectura_id,
                        json.dumps(canciones_json, ensure_ascii=False),
                        ruta_pptx,
                        ruta_pdf_fieles,
                        ruta_pdf_musicos,
                        ruta_web,
                        fecha,
                    ),
                )
            else:
                conn.execute(
                    """
                    INSERT INTO presentaciones
                    (fecha_domingo, lectura_id, canciones_json, ruta_pptx, ruta_pdf_fieles, ruta_pdf_musicos, ruta_web, estado)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 'publicada')
                    """,
                    (
                        fecha,
                        lectura_id,
                        json.dumps(canciones_json, ensure_ascii=False),
                        ruta_pptx,
                        ruta_pdf_fieles,
                        ruta_pdf_musicos,
                        ruta_web,
                    ),
                )
