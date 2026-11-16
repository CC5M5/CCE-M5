#!/usr/bin/env python3
"""Limpieza de datos de prueba y normalización de títulos (S3 + S4).

S3 — Elimina de la BD viva las canciones con título EXACTO «Canción A» y
«Canción B», junto con sus datos relacionados:
  - cancion_momentos de esas canciones
  - slides auto-creadas (subtipo «cancion_<id>») y slides con título exacto
  - filas en presentacion_slides que referencian esas slides
  - referencias en presentaciones.canciones_json (incluye refs huérfanas a
    canciones que ya no existen)
No toca canciones sospechosas (p. ej. «Aleluya»): solo las reporta como
anomalía para que un humano decida.

S4 — Normaliza el prefijo «l » (minúscula L + espacio) en los títulos
guardados:
  - lecturas.celebracion y lecturas.domingo
  - presentaciones.lectura_json (clave «celebracion»)
No muta logs históricos (workflow_runs.steps_data) ni títulos con «L »
mayúscula: solo los reporta como anomalías.

Deuda de datos (L8/L9) — fase `clean_deuda` (activa por defecto; se omite
con --no-deuda). Autorizada por el usuario (L9):
  - Lote «Aleluya%»: canciones, sus cancion_momentos, sus slides (título
    «Aleluya%» o subtipo «cancion_<id>» del lote), sus presentacion_slides y
    sus referencias en presentaciones.canciones_json.
  - Slides huérfanas: subtipo «cancion_<id>» cuyo id no existe en canciones
    (recontadas tras el lote anterior).
  - workflow_runs.steps_data: quita el prefijo «l » (guard de numerales
    romanos `^l [IVXLCDM]+[ .,]`) recursivamente, incluidos los JSON
    anidados tipo «lectura_json»; solo se reescriben las filas que cambian;
    los valores no JSON se dejan intactos.
  - Slides con título «l »/«L » (guard de numerales romanos).
  - T9: la presentación «generado» de 2026-11-16, sus presentacion_slides y
    su bundle presentaciones_html/2026-11-16_presentacion/ (las «borrador» del
    mismo día no se tocan).

Además:
  - Crea un backup consistente ANTES de mutar:
      <bd>.bak-deuda-<YYYYMMDD-HHMMSS> (o .bak-limpieza-… con --no-deuda)
  - Limpia quirúrgicamente data/schema.sql a nivel de sentencias SQL (no de
    líneas, porque el dump concatena sentencias) para que una instalación
    nueva no resucite los datos de prueba ni el prefijo «l ».
  - Regenera web/data/canciones.json (misma semántica que
    scripts/export_data_for_web.py, solo ese archivo).

Idempotente: una segunda ejecución no cambia nada e imprime conteos en cero.

Uso:
    .venv/bin/python scripts/limpieza_datos.py [--dry-run] [--no-schema]
    .venv/bin/python scripts/limpieza_datos.py --no-export-web
    .venv/bin/python scripts/limpieza_datos.py --no-deuda  # solo S3+S4
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sqlite3
import tempfile
from datetime import datetime
from pathlib import Path

CANCIONES_PRUEBA = ("Canción A", "Canción B")
PREFIJO_L = "l "
FECHA_PRESENTACION_16N = "2026-11-16"
# Guard de numerales romanos: solo se quita «l »/«L » si va seguido de un
# numeral romano (y espacio/punto/coma), para no tocar «Lunes», «l Aleluya»…
RE_L_ROMANO = re.compile(r"^l [IVXLCDM]+[ .,]")
RE_L_ROMANO_MAYUSCULA = re.compile(r"^L [IVXLCDM]+[ .,]")

RAIZ_PROYECTO = Path(__file__).resolve().parents[1]


# ---------------------------------------------------------------------------
# Utilidades
# ---------------------------------------------------------------------------


def normalizar_titulo(texto):
    """Quita el prefijo «l » (minúscula L + espacio) si existe.

    Devuelve (texto_resultante, cambiado).
    """
    if not isinstance(texto, str) or not texto.startswith(PREFIJO_L):
        return texto, False
    return texto[len(PREFIJO_L):].lstrip(), True


def _normalizar_lectura_json(valor):
    """Normaliza la clave «celebracion» dentro de un JSON de lectura.

    Devuelve (nuevo_valor, cambiado).
    """
    if not isinstance(valor, str):
        return valor, False
    try:
        obj = json.loads(valor)
    except (ValueError, TypeError):
        return valor, False
    if not isinstance(obj, dict):
        return valor, False
    celebracion, cambio = normalizar_titulo(obj.get("celebracion"))
    if not cambio:
        return valor, False
    obj["celebracion"] = celebracion
    return json.dumps(obj, ensure_ascii=False), True


def _normalizar_json_l(valor):
    """Recursivo: quita el prefijo «l » (guard de numerales romanos).

    Sobre un valor JSON ya parseado: en cadenas quita el prefijo «l » solo si
    encaja el guard; en cadenas que son JSON anidado (p. ej. la clave
    «lectura_json») parsea y recursa. Devuelve (nuevo_valor, cambiado).
    """
    if isinstance(valor, dict):
        nuevo = {}
        cambio = False
        for clave, v in valor.items():
            nv, c = _normalizar_json_l(v)
            cambio = cambio or c
            nuevo[clave] = nv
        return nuevo, cambio
    if isinstance(valor, list):
        salida = []
        cambio = False
        for v in valor:
            nv, c = _normalizar_json_l(v)
            cambio = cambio or c
            salida.append(nv)
        return salida, cambio
    if isinstance(valor, str):
        if valor.startswith(PREFIJO_L) and RE_L_ROMANO.match(valor):
            return valor[len(PREFIJO_L):].lstrip(), True
        try:
            anidado = json.loads(valor)
        except (ValueError, TypeError):
            return valor, False
        if isinstance(anidado, (dict, list)):
            nuevo, cambio = _normalizar_json_l(anidado)
            if not cambio:
                return valor, False
            return json.dumps(nuevo, ensure_ascii=False), True
        return valor, False
    return valor, False


def _normalizar_steps_data(valor):
    """Normaliza workflow_runs.steps_data (JSON textual).

    Solo devuelve el valor reescrito cuando cambió; los valores no JSON se
    devuelven intactos. Devuelve (nuevo_valor, cambiado).
    """
    if not isinstance(valor, str):
        return valor, False
    try:
        obj = json.loads(valor)
    except (ValueError, TypeError):
        return valor, False
    if not isinstance(obj, (dict, list)):
        return valor, False
    nuevo, cambio = _normalizar_json_l(obj)
    if not cambio:
        return valor, False
    return json.dumps(nuevo, ensure_ascii=False), True


def _purgar_canciones_json(valor, ids_vivos, ids_prueba):
    """Depura presentaciones.canciones_json.

    Elimina referencias a canciones de prueba (ids_prueba) y referencias
    huérfanas (ids que no existen en `ids_vivos`). Devuelve
    (nuevo_valor, refs_prueba_eliminadas, refs_hueras_eliminadas).
    Si no queda ninguna referencia, el valor resultante es None
    (convención «sin canciones»).
    """
    if valor is None:
        return None, 0, 0
    if isinstance(valor, str):
        try:
            data = json.loads(valor)
        except (ValueError, TypeError):
            return valor, 0, 0
    else:
        data = valor
    if not isinstance(data, dict):
        return valor, 0, 0

    limpio = {}
    refs_prueba = 0
    refs_hueras = 0
    for clave, ref in data.items():
        raw_id = ref.get("id") if isinstance(ref, dict) else ref
        try:
            cancion_id = int(raw_id)
        except (TypeError, ValueError):
            continue
        if cancion_id in ids_prueba:
            refs_prueba += 1
        elif cancion_id not in ids_vivos:
            refs_hueras += 1
        else:
            limpio[clave] = ref
    nuevo = json.dumps(limpio, ensure_ascii=False) if limpio else None
    return nuevo, refs_prueba, refs_hueras


def _canciones_prueba_ids(conn: sqlite3.Connection) -> list[int]:
    cur = conn.execute(
        "SELECT id FROM canciones WHERE titulo = ? OR titulo = ? ORDER BY id",
        CANCIONES_PRUEBA,
    )
    return [row[0] for row in cur.fetchall()]


def _slides_prueba_ids(conn: sqlite3.Connection, cancion_ids: list[int]) -> list[int]:
    """Slides con título exacto o subtipo «cancion_<id>» de esas canciones."""
    sql = "SELECT id FROM slides WHERE titulo IN (?, ?) "
    params: list = list(CANCIONES_PRUEBA)
    subtipos = [f"cancion_{i}" for i in cancion_ids]
    if subtipos:
        sql += "OR subtipo IN (" + ",".join("?" for _ in subtipos) + ") "
        params.extend(subtipos)
    sql += "ORDER BY id"
    return [row[0] for row in conn.execute(sql, params).fetchall()]


# ---------------------------------------------------------------------------
# BD viva
# ---------------------------------------------------------------------------


def clean_db(conn: sqlite3.Connection, aplicar: bool = True) -> dict:
    """Aplica la limpieza S3+S4 a la BD abierta. Devuelve los conteos."""
    conn.execute("PRAGMA foreign_keys=ON")

    ids_prueba = _canciones_prueba_ids(conn)
    ids_prueba_set = set(ids_prueba)
    slide_ids = _slides_prueba_ids(conn, ids_prueba)
    slide_ids_set = set(slide_ids)
    ids_vivos = {row[0] for row in conn.execute("SELECT id FROM canciones")}

    # Anomalías: solo se reportan, nunca se mutan aquí.
    aleluya_canciones = [
        row[0]
        for row in conn.execute(
            "SELECT id FROM canciones WHERE titulo LIKE 'Aleluya%' ORDER BY id"
        )
    ]
    aleluya_slides = conn.execute(
        "SELECT COUNT(*) FROM slides WHERE titulo LIKE 'Aleluya%'"
    ).fetchone()[0]
    workflow_l = 0
    try:
        workflow_l = conn.execute(
            "SELECT COUNT(*) FROM workflow_runs WHERE steps_data LIKE '%l %'"
        ).fetchone()[0]
    except sqlite3.OperationalError:
        pass  # tabla de runtime ausente (p. ej. en un seed)
    slides_L_mayuscula = [
        row[0]
        for row in conn.execute(
            "SELECT id FROM slides WHERE titulo LIKE 'L %' ORDER BY id"
        )
    ]

    # Plan de actualizaciones (cálculo siempre; escritura solo si aplicar).
    momentos_a_borrar = 0
    pres_slides_a_borrar = 0
    if ids_prueba:
        ph = ",".join("?" for _ in ids_prueba)
        momentos_a_borrar = conn.execute(
            f"SELECT COUNT(*) FROM cancion_momentos WHERE cancion_id IN ({ph})",
            ids_prueba,
        ).fetchone()[0]
    if slide_ids:
        ph = ",".join("?" for _ in slide_ids)
        pres_slides_a_borrar = conn.execute(
            f"SELECT COUNT(*) FROM presentacion_slides WHERE slide_id IN ({ph})",
            slide_ids,
        ).fetchone()[0]

    presentaciones_tocar = []
    for pid, cj, lj in conn.execute(
        "SELECT id, canciones_json, lectura_json FROM presentaciones "
        "WHERE canciones_json IS NOT NULL OR lectura_json IS NOT NULL"
    ):
        nuevo_cj, refs_p, refs_h = _purgar_canciones_json(
            cj, ids_vivos - ids_prueba_set, ids_prueba_set
        )
        nuevo_lj, cambio_lj = _normalizar_lectura_json(lj)
        if nuevo_cj != cj or cambio_lj:
            presentaciones_tocar.append((pid, nuevo_cj, nuevo_lj, refs_p, refs_h))

    lecturas_tocar = []
    for lid, domingo, celebracion in conn.execute(
        "SELECT id, domingo, celebracion FROM lecturas"
    ):
        nuevo_domingo, c1 = normalizar_titulo(domingo)
        nuevo_celebracion, c2 = normalizar_titulo(celebracion)
        if c1 or c2:
            lecturas_tocar.append((lid, nuevo_domingo, nuevo_celebracion))

    if aplicar:
        with conn:
            if slide_ids:
                ph = ",".join("?" for _ in slide_ids)
                conn.execute(
                    f"DELETE FROM presentacion_slides WHERE slide_id IN ({ph})",
                    slide_ids,
                )
                conn.execute(f"DELETE FROM slides WHERE id IN ({ph})", slide_ids)
            if ids_prueba:
                ph = ",".join("?" for _ in ids_prueba)
                conn.execute(
                    f"DELETE FROM cancion_momentos WHERE cancion_id IN ({ph})",
                    ids_prueba,
                )
                conn.execute(f"DELETE FROM canciones WHERE id IN ({ph})", ids_prueba)
            for pid, nuevo_cj, nuevo_lj, _rp, _rh in presentaciones_tocar:
                conn.execute(
                    "UPDATE presentaciones SET canciones_json=?, lectura_json=? "
                    "WHERE id=?",
                    (nuevo_cj, nuevo_lj, pid),
                )
            for lid, nuevo_domingo, nuevo_celebracion in lecturas_tocar:
                conn.execute(
                    "UPDATE lecturas SET domingo=?, celebracion=? WHERE id=?",
                    (nuevo_domingo, nuevo_celebracion, lid),
                )

    return {
        "canciones": ids_prueba,
        "cancion_momentos": momentos_a_borrar,
        "slides": slide_ids,
        "presentacion_slides": pres_slides_a_borrar,
        "presentaciones": [p[0] for p in presentaciones_tocar],
        "lecturas": [l[0] for l in lecturas_tocar],
        "refs_prueba_eliminadas": sum(p[3] for p in presentaciones_tocar),
        "refs_hueras_eliminadas": sum(p[4] for p in presentaciones_tocar),
        "anomalias": {
            "aleluya": {"canciones": aleluya_canciones, "slides": aleluya_slides},
            "workflow_l": workflow_l,
            "slides_titulo_L_mayuscula": slides_L_mayuscula,
        },
    }


def clean_deuda(
    conn: sqlite3.Connection,
    aplicar: bool = True,
    raiz: Path = RAIZ_PROYECTO,
) -> dict:
    """Fase de deuda de datos (L8/L9). Devuelve los conteos del plan/aplicado.

    1. Lote «Aleluya%»: canciones + cancion_momentos + slides (título
       «Aleluya%» o subtipo «cancion_<id>» del lote) + presentacion_slides +
       refs en presentaciones.canciones_json (vía _purgar_canciones_json).
    2. Slides huérfanas: subtipo «cancion_<id>» sin canción (recontadas
       tras el paso 1; incluye «cancion_…» sin id resolvable).
    3. workflow_runs.steps_data: prefijo «l » con guard de numerales romanos
       (recursivo; JSON anidado tipo «lectura_json»; solo filas que cambian).
    4. Slides con título «l »/«L » (guard de numerales romanos).
    5. T9: presentación «generado» de FECHA_PRESENTACION_16N + sus
       presentacion_slides + su bundle en presentaciones_html/ (las
       «borrador» del mismo día no se tocan).
    """
    conn.execute("PRAGMA foreign_keys=ON")

    # 1. Lote «Aleluya%».
    aleluya_ids = [
        row[0]
        for row in conn.execute(
            "SELECT id FROM canciones WHERE titulo LIKE 'Aleluya%' ORDER BY id"
        )
    ]
    aleluya_set = set(aleluya_ids)
    ids_vivos = {row[0] for row in conn.execute("SELECT id FROM canciones")}

    sql = "SELECT id FROM slides WHERE titulo LIKE 'Aleluya%'"
    params: list = []
    if aleluya_ids:
        sql += " OR subtipo IN (" + ",".join("?" for _ in aleluya_ids) + ")"
        params = list(aleluya_ids)
    aleluya_slide_ids = [row[0] for row in conn.execute(sql, params)]
    aleluya_slide_set = set(aleluya_slide_ids)

    # 2. Slides huérfanas (recontadas tras el paso 1).
    slides_hueras: list[int] = []
    for sid, subtipo in conn.execute(
        "SELECT id, subtipo FROM slides WHERE subtipo LIKE 'cancion_%'"
    ):
        if sid in aleluya_slide_set:
            continue
        m = re.fullmatch(r"cancion_(\d+)", subtipo or "")
        if m and int(m.group(1)) in ids_vivos:
            continue  # slide de una canción viva
        slides_hueras.append(sid)

    todas_slides = sorted(aleluya_slide_set | set(slides_hueras))

    # Conteos (cálculo siempre; escritura solo si aplicar).
    momentos_a_borrar = 0
    pres_slides_a_borrar = 0
    if aleluya_ids:
        ph = ",".join("?" for _ in aleluya_ids)
        momentos_a_borrar = conn.execute(
            f"SELECT COUNT(*) FROM cancion_momentos WHERE cancion_id IN ({ph})",
            aleluya_ids,
        ).fetchone()[0]
    if todas_slides:
        ph = ",".join("?" for _ in todas_slides)
        pres_slides_a_borrar = conn.execute(
            f"SELECT COUNT(*) FROM presentacion_slides WHERE slide_id IN ({ph})",
            todas_slides,
        ).fetchone()[0]

    # Refs en presentaciones.canciones_json (reutiliza _purgar_canciones_json:
    # refs del lote + refs huérfanas a canciones inexistentes).
    presentaciones_tocar: list[tuple[int, object, int]] = []
    for pid, cj in conn.execute(
        "SELECT id, canciones_json FROM presentaciones WHERE canciones_json IS NOT NULL"
    ):
        nuevo_cj, refs_p, refs_h = _purgar_canciones_json(
            cj, ids_vivos - aleluya_set, aleluya_set
        )
        if nuevo_cj != cj:
            presentaciones_tocar.append((pid, nuevo_cj, refs_p + refs_h))

    # 3. workflow_runs.steps_data (tabla de runtime: puede no existir).
    workflow_tocar: list[tuple[int, str]] = []
    try:
        for rid, steps_data in conn.execute("SELECT id, steps_data FROM workflow_runs"):
            nuevo, cambio = _normalizar_steps_data(steps_data)
            if cambio:
                workflow_tocar.append((rid, nuevo))
    except sqlite3.OperationalError:
        pass

    # 4. Slides con título «l »/«L » (LIKE ASCII es insensible a mayúsculas).
    slides_prefijo: list[tuple[int, str]] = []
    for sid, titulo in conn.execute(
        "SELECT id, titulo FROM slides WHERE titulo LIKE 'l %' OR titulo LIKE 'L %'"
    ):
        if RE_L_ROMANO.match(titulo) or RE_L_ROMANO_MAYUSCULA.match(titulo):
            nuevo = titulo[2:].lstrip()
            if nuevo != titulo:
                slides_prefijo.append((sid, nuevo))

    # 5. T9: 16-N «generado».
    pres_16n = [
        row[0]
        for row in conn.execute(
            "SELECT id FROM presentaciones "
            "WHERE fecha_domingo = ? AND estado = 'generado' ORDER BY id",
            (FECHA_PRESENTACION_16N,),
        )
    ]
    pres_slides_16n = 0
    if pres_16n:
        ph = ",".join("?" for _ in pres_16n)
        pres_slides_16n = conn.execute(
            f"SELECT COUNT(*) FROM presentacion_slides WHERE presentacion_id IN ({ph})",
            pres_16n,
        ).fetchone()[0]
    bundle_dir = raiz / "presentaciones_html" / f"{FECHA_PRESENTACION_16N}_presentacion"
    bundle_16n = str(bundle_dir) if bundle_dir.is_dir() else None
    bundle_eliminado = False
    if aplicar and pres_16n and bundle_16n:
        shutil.rmtree(bundle_dir)
        bundle_eliminado = True

    if aplicar:
        with conn:
            if todas_slides:
                ph = ",".join("?" for _ in todas_slides)
                conn.execute(
                    f"DELETE FROM presentacion_slides WHERE slide_id IN ({ph})",
                    todas_slides,
                )
                conn.execute(f"DELETE FROM slides WHERE id IN ({ph})", todas_slides)
            if aleluya_ids:
                ph = ",".join("?" for _ in aleluya_ids)
                conn.execute(
                    f"DELETE FROM cancion_momentos WHERE cancion_id IN ({ph})",
                    aleluya_ids,
                )
                conn.execute(f"DELETE FROM canciones WHERE id IN ({ph})", aleluya_ids)
            if pres_16n:
                ph = ",".join("?" for _ in pres_16n)
                conn.execute(
                    f"DELETE FROM presentacion_slides WHERE presentacion_id IN ({ph})",
                    pres_16n,
                )
                conn.execute(f"DELETE FROM presentaciones WHERE id IN ({ph})", pres_16n)
            for pid, nuevo_cj, _refs in presentaciones_tocar:
                conn.execute(
                    "UPDATE presentaciones SET canciones_json=? WHERE id=?",
                    (nuevo_cj, pid),
                )
            for sid, nuevo_titulo in slides_prefijo:
                conn.execute("UPDATE slides SET titulo=? WHERE id=?", (nuevo_titulo, sid))
            for rid, nuevo in workflow_tocar:
                conn.execute(
                    "UPDATE workflow_runs SET steps_data=? WHERE id=?", (nuevo, rid)
                )

    return {
        "aleluya_canciones": aleluya_ids,
        "aleluya_cancion_momentos": momentos_a_borrar,
        "aleluya_slides": sorted(aleluya_slide_ids),
        "slides_hueras": sorted(slides_hueras),
        "slides": todas_slides,
        "presentacion_slides": pres_slides_a_borrar,
        "presentaciones": [p[0] for p in presentaciones_tocar],
        "refs_eliminadas": sum(p[2] for p in presentaciones_tocar),
        "workflow_runs": [r[0] for r in workflow_tocar],
        "slides_prefijo_l": [s[0] for s in slides_prefijo],
        "presentaciones_16n": pres_16n,
        "presentacion_slides_16n": pres_slides_16n,
        "bundle_16n": bundle_16n,
        "bundle_eliminado": bundle_eliminado,
    }


def backup_database(db_path: Path, backup_path: Path) -> Path:
    """Copia consistente de la BD (API de backup de SQLite)."""
    origen = sqlite3.connect(str(db_path))
    try:
        destino = sqlite3.connect(str(backup_path))
        try:
            origen.backup(destino)
        finally:
            destino.close()
    finally:
        origen.close()
    return backup_path


# ---------------------------------------------------------------------------
# data/schema.sql (a nivel de sentencias)
# ---------------------------------------------------------------------------


def _split_statements(texto: str) -> tuple[list[tuple[int, int]], str]:
    """Divide el dump en sentencias completas.

    Devuelve (spans, cola) donde cada span (inicio, fin) incluye el ';'
    final de la sentencia; `cola` es el texto residual tras la última
    sentencia completa.

    Un ';' dentro de un literal de cadena (p. ej. entidades HTML como
    "&amp;" en la letra de las canciones) no completa la sentencia: se
    sigue probando con el siguiente ';' manteniendo el mismo inicio.
    """
    spans = []
    start = 0
    pos = 0
    n = len(texto)
    while pos < n:
        i = texto.find(";", pos)
        if i == -1:
            break
        candidata = texto[start : i + 1]
        if candidata.strip() and sqlite3.complete_statement(candidata):
            spans.append((start, i + 1))
            start = i + 1
        pos = i + 1
    return spans, texto[start:]


def _valor_sql(v) -> str:
    """Literal SQL en el mismo estilo que el dump original."""
    if v is None:
        return "NULL"
    if isinstance(v, (int, float)):
        return str(v)
    return "'" + str(v).replace("'", "''") + "'"


def _reemitir(
    stmt_original: str,
    tabla: str,
    fila: dict,
    ids_vivos: set | None = None,
    ids_prueba: set | None = None,
) -> tuple[str, bool]:
    """Reemite un INSERT transformando las columnas de título/JSON.

    Devuelve (nueva_sentencia, cambio).
    """
    if tabla not in ("presentaciones", "lecturas"):
        return stmt_original, False
    fila = dict(fila)
    if tabla == "presentaciones":
        nuevo_cj, _, _ = _purgar_canciones_json(
            fila.get("canciones_json"), ids_vivos or set(), ids_prueba or set()
        )
        nuevo_lj, _ = _normalizar_lectura_json(fila.get("lectura_json"))
        fila["canciones_json"] = nuevo_cj
        fila["lectura_json"] = nuevo_lj
    else:
        fila["domingo"], _ = normalizar_titulo(fila.get("domingo"))
        fila["celebracion"], _ = normalizar_titulo(fila.get("celebracion"))
    stmt = (
        f'INSERT INTO "{tabla}" VALUES('
        + ",".join(_valor_sql(v) for v in fila.values())
        + ");"
    )
    return stmt, stmt != stmt_original


def clean_schema_sql(schema_path: Path, aplicar: bool = True) -> dict:
    """Limpia el dump SQL de forma quirúrgica (sentencia a sentencia).

    Se verifica el resultado en una BD temporal antes de sobrescribir el
    archivo. Devuelve los conteos.
    """
    texto = schema_path.read_text(encoding="utf-8")

    with tempfile.TemporaryDirectory(prefix="cce-limpieza-") as tmpdir:
        origen_path = Path(tmpdir) / "origen.sqlite3"
        conn = sqlite3.connect(str(origen_path))
        try:
            conn.executescript(texto)
            conn.commit()

            ids_prueba = _canciones_prueba_ids(conn)
            ids_prueba_set = set(ids_prueba)
            slide_ids = _slides_prueba_ids(conn, ids_prueba)
            slide_ids_set = set(slide_ids)
            ids_vivos = {row[0] for row in conn.execute("SELECT id FROM canciones")}
            ids_vivos_set = set(ids_vivos)

            conteos = {
                "canciones": [],
                "cancion_momentos": 0,
                "slides": [],
                "presentacion_slides": 0,
                "presentaciones": 0,
                "lecturas": 0,
                "refs_prueba_eliminadas": 0,
                "refs_hueras_eliminadas": 0,
            }
            totales_origen = {}
            for tabla in (
                "canciones",
                "cancion_momentos",
                "slides",
                "presentacion_slides",
                "presentaciones",
                "lecturas",
            ):
                try:
                    totales_origen[tabla] = conn.execute(
                        f"SELECT COUNT(*) FROM {tabla}"
                    ).fetchone()[0]
                except sqlite3.OperationalError:
                    totales_origen[tabla] = None

            # BD scratch con solo DDL para extraer los valores de cada INSERT.
            spans, cola = _split_statements(texto)
            ddl_stmts = [
                texto[a:b]
                for a, b in spans
                if texto[a:b].lstrip().upper().startswith(("CREATE ", "PRAGMA"))
            ]
            scratch = sqlite3.connect(":memory:")
            scratch.executescript("\n".join(ddl_stmts))

            output = []
            for a, b in spans:
                stmt = texto[a:b]
                cab = stmt.lstrip().upper()
                if cab.startswith(("CREATE ", "PRAGMA", "BEGIN", "COMMIT", "DELETE")):
                    output.append(stmt)
                    continue
                m = re.match(r'INSERT INTO "(\w+)"', stmt.lstrip())
                if not m:
                    output.append(stmt)
                    continue
                tabla = m.group(1)
                if tabla == "sqlite_sequence":
                    # Tabla interna: nunca se modifica, se conserva tal cual.
                    output.append(stmt)
                    continue

                scratch.execute(stmt)
                cur = scratch.execute(f"SELECT * FROM {tabla} ORDER BY rowid DESC LIMIT 1")
                desc = [d[0] for d in cur.description]
                fila = dict(zip(desc, cur.fetchone()))
                scratch.execute(
                    f"DELETE FROM {tabla} WHERE rowid = (SELECT MAX(rowid) FROM {tabla})"
                )

                if tabla == "canciones" and fila.get("id") in ids_prueba_set:
                    conteos["canciones"].append(fila["id"])
                    continue
                if tabla == "cancion_momentos" and fila.get("cancion_id") in ids_prueba_set:
                    conteos["cancion_momentos"] += 1
                    continue
                if tabla == "slides" and fila.get("id") in slide_ids_set:
                    conteos["slides"].append(fila["id"])
                    continue
                if tabla == "presentacion_slides" and fila.get("slide_id") in slide_ids_set:
                    conteos["presentacion_slides"] += 1
                    continue
                if tabla == "presentaciones":
                    nuevo_stmt, cambio = _reemitir(
                        stmt, tabla, fila, ids_vivos_set - ids_prueba_set, ids_prueba_set
                    )
                    if cambio:
                        conteos["presentaciones"] += 1
                    output.append(nuevo_stmt)
                    continue
                if tabla == "lecturas":
                    nuevo_stmt, cambio = _reemitir(stmt, tabla, fila)
                    if cambio:
                        conteos["lecturas"] += 1
                    output.append(nuevo_stmt)
                    continue
                output.append(stmt)
            scratch.close()

            nuevo_texto = "".join(output) + cola

            # Verificación: el dump resultante debe cargar y estar limpio.
            verif = sqlite3.connect(":memory:")
            try:
                verif.executescript(nuevo_texto)
                verif.commit()

                def _c(q, p=()):
                    return verif.execute(q, p).fetchone()[0]

                assert _c("SELECT COUNT(*) FROM canciones WHERE titulo IN (?,?)", CANCIONES_PRUEBA) == 0
                assert _c("SELECT COUNT(*) FROM slides WHERE titulo IN (?,?)", CANCIONES_PRUEBA) == 0
                assert _c(
                    "SELECT COUNT(*) FROM lecturas "
                    "WHERE celebracion LIKE 'l %' OR domingo LIKE 'l %'"
                ) == 0
                # Conteo de refs huérfanas/prueba en el resultado (Python, sin JSON1):
                refs_badas = 0
                for cj in verif.execute(
                    "SELECT canciones_json FROM presentaciones WHERE canciones_json IS NOT NULL"
                ):
                    _nuevo, _rp, _rh = _purgar_canciones_json(
                        cj[0], ids_vivos_set, set()
                    )
                    refs_badas += _rp + _rh
                assert refs_badas == 0

                for tabla, total in totales_origen.items():
                    if total is None:
                        continue
                    delta = {
                        "canciones": len(conteos["canciones"]),
                        "cancion_momentos": conteos["cancion_momentos"],
                        "slides": len(conteos["slides"]),
                        "presentacion_slides": conteos["presentacion_slides"],
                    }.get(tabla, 0)
                    assert _c(f"SELECT COUNT(*) FROM {tabla}") == total - delta, tabla
            finally:
                verif.close()
        finally:
            conn.close()

    cambio = any(
        conteos[k]
        for k in (
            "canciones",
            "cancion_momentos",
            "slides",
            "presentacion_slides",
            "presentaciones",
            "lecturas",
        )
    )
    if aplicar and cambio:
        schema_path.write_text(nuevo_texto, encoding="utf-8")

    conteos["cambios"] = cambio
    conteos["escrito"] = bool(aplicar and cambio)
    return conteos


# ---------------------------------------------------------------------------
# Export web (solo canciones.json)
# ---------------------------------------------------------------------------


def export_canciones_web(db_path: Path, out_path: Path) -> Path:
    """Regenera web/data/canciones.json (misma semántica que export_data_for_web)."""
    conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute("SELECT * FROM canciones ORDER BY id").fetchall()
    finally:
        conn.close()
    data = [dict(r) for r in rows]
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return out_path


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _default_db_path() -> Path:
    try:
        from src.config import settings

        return Path(settings.db_path)
    except Exception:
        return RAIZ_PROYECTO / "data" / "db.sqlite3"


def _imprimir_bd(res: dict) -> None:
    print("Limpieza BD viva:")
    print(f"  canciones eliminadas: {len(res['canciones'])} {res['canciones']}")
    print(f"  cancion_momentos eliminados: {res['cancion_momentos']}")
    print(f"  slides eliminadas: {len(res['slides'])} {res['slides']}")
    print(f"  presentacion_slides eliminadas: {res['presentacion_slides']}")
    print(f"  presentaciones actualizadas: {len(res['presentaciones'])} {res['presentaciones']}")
    print(f"  refs a canciones de prueba eliminadas: {res['refs_prueba_eliminadas']}")
    print(f"  refs huérfanas eliminadas: {res['refs_hueras_eliminadas']}")
    print(f"  lecturas normalizadas: {len(res['lecturas'])} {res['lecturas']}")
    a = res["anomalias"]
    print("Anomalías (NO mutadas, para revisión humana):")
    print(f"  canciones «Aleluya%»: {a['aleluya']['canciones']}")
    print(f"  slides «Aleluya%»: {a['aleluya']['slides']}")
    print(f"  workflow_runs.steps_data con «l »: {a['workflow_l']}")
    print(f"  slides con «L » mayúscula: {a['slides_titulo_L_mayuscula']}")


def _imprimir_deuda(res: dict, dry_run: bool) -> None:
    verbo = "se eliminarían" if dry_run else "eliminadas"
    print(f"Fase deuda (L8/L9)" + (" [dry-run: nada mutado]" if dry_run else ""))
    print(f"  canciones «Aleluya%» {verbo}: {len(res['aleluya_canciones'])} {res['aleluya_canciones']}")
    print(f"  cancion_momentos {verbo}: {res['aleluya_cancion_momentos']}")
    print(f"  slides del lote «Aleluya%» {verbo}: {len(res['aleluya_slides'])} {res['aleluya_slides']}")
    print(f"  slides huérfanas {verbo}: {len(res['slides_hueras'])}")
    print(f"  presentacion_slides {verbo}: {res['presentacion_slides']}")
    print(f"  presentaciones purgadas (canciones_json): {len(res['presentaciones'])} {res['presentaciones']}")
    print(f"  refs en canciones_json eliminadas: {res['refs_eliminadas']}")
    print(f"  workflow_runs.steps_data normalizados: {len(res['workflow_runs'])} {res['workflow_runs']}")
    print(f"  slides «l »/«L » normalizadas: {len(res['slides_prefijo_l'])} {res['slides_prefijo_l']}")
    print(f"  presentaciones 16-N «generado» {verbo}: {len(res['presentaciones_16n'])} {res['presentaciones_16n']}")
    print(f"  presentacion_slides 16-N {verbo}: {res['presentacion_slides_16n']}")
    if res["bundle_16n"]:
        if res["bundle_eliminado"]:
            print(f"  bundle 16-N eliminado: {res['bundle_16n']}")
        else:
            print(f"  bundle 16-N que se eliminaría: {res['bundle_16n']}")


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description="Limpia datos de prueba (Canción A/B), normaliza el prefijo «l » "
        "y limpia la deuda de datos L8/L9 (lote «Aleluya%», huérfanas, workflow_runs, «L », 16-N)."
    )
    parser.add_argument("--db", type=Path, default=None, help="BD a limpiar")
    parser.add_argument("--schema", type=Path, default=None, help="schema.sql a limpiar")
    parser.add_argument("--no-schema", action="store_true", help="No tocar data/schema.sql")
    parser.add_argument(
        "--no-deuda", action="store_true",
        help="No ejecutar la fase de deuda de datos (L8/L9)",
    )
    parser.add_argument(
        "--no-export-web", action="store_true", help="No regenerar web/data/canciones.json"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Solo informa; no muta ni crea backup"
    )
    parser.add_argument(
        "--skip-backup", action="store_true", help="No crear backup antes de mutar"
    )
    args = parser.parse_args(argv)

    db_path = args.db or _default_db_path()
    schema_path = args.schema if args.schema is not None else RAIZ_PROYECTO / "data" / "schema.sql"

    print(f"BD: {db_path}")
    print(f"Schema: {schema_path}" + (" (omitido)" if args.no_schema else ""))
    if args.dry_run:
        print("MODO DRY-RUN: no se mutará nada ni se creará backup.")

    if not args.dry_run and not args.skip_backup:
        prefijo_bak = "deuda" if not args.no_deuda else "limpieza"
        backup_path = db_path.with_name(
            f"{db_path.name}.bak-{prefijo_bak}-{datetime.now():%Y%m%d-%H%M%S}"
        )
        backup_database(db_path, backup_path)
        print(f"Backup creado: {backup_path}")

    conn = sqlite3.connect(str(db_path))
    res_deuda = None
    try:
        res = clean_db(conn, aplicar=not args.dry_run)
        if not args.no_deuda:
            res_deuda = clean_deuda(conn, aplicar=not args.dry_run)
    finally:
        conn.close()
    _imprimir_bd(res)
    if res_deuda is not None:
        _imprimir_deuda(res_deuda, dry_run=args.dry_run)

    if not args.no_schema:
        if schema_path.exists():
            res_schema = clean_schema_sql(schema_path, aplicar=not args.dry_run)
            print("Limpieza data/schema.sql:")
            print(f"  canciones eliminadas: {len(res_schema['canciones'])}")
            print(f"  cancion_momentos eliminados: {res_schema['cancion_momentos']}")
            print(f"  slides eliminadas: {len(res_schema['slides'])}")
            print(f"  presentacion_slides eliminadas: {res_schema['presentacion_slides']}")
            print(f"  presentaciones reescritas: {res_schema['presentaciones']}")
            print(f"  lecturas reescritas: {res_schema['lecturas']}")
            print(f"  refs a canciones de prueba eliminadas: {res_schema['refs_prueba_eliminadas']}")
            print(f"  refs huérfanas eliminadas: {res_schema['refs_hueras_eliminadas']}")
            print(f"  archivo escrito: {res_schema['escrito']}")
        else:
            print(f"Schema no encontrado: {schema_path} (omitido)")

    if not args.no_export_web:
        if args.dry_run:
            print("Export web omitido (dry-run).")
        else:
            out = RAIZ_PROYECTO / "web" / "data" / "canciones.json"
            export_canciones_web(db_path, out)
            print(f"Exportado: {out}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
