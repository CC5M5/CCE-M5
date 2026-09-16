#!/usr/bin/env python3
"""
Corrección de acordes desde la web de origen.

Uso:
  python scripts/corregir_acordes_desde_origen.py --report --output informe.html
  python scripts/corregir_acordes_desde_origen.py --apply --ids 2,3,8

Modo --report (default): descarga el HTML original de cada canción, extrae
el texto con acordes posicionados (conservando espacios y saltos de línea)
y genera un informe HTML comparativo con la versión almacenada en la BD.

Modo --apply: aplica las correcciones a la base de datos SQLite. Regenera
estructura_json, html_visual, letra_sin_acordes y tono con acordes_parser_v3.
"""

from __future__ import annotations

import argparse
import html as html_module
import re
import sqlite3
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional

import requests
from bs4 import BeautifulSoup

PROJECT_DIR = Path(__file__).resolve().parents[1]
DB_PATH = PROJECT_DIR / "data" / "db.sqlite3"
OUTPUT_DIR = PROJECT_DIR / "docs" / "correcciones_acordes"

# Líneas de metadatos del blogspot (insensibles a mayúsculas).
_METADATA_RES = [
    re.compile(r"^\s*escuchar\s*$", re.IGNORECASE),
    re.compile(r"^\s*volver\s+a\s+lista\s+de\s+canciones\s*$", re.IGNORECASE),
    re.compile(r"^\s*volver\s+a\s+lista\s*$", re.IGNORECASE),
    re.compile(r"^\s*volver\s+lista\s+de\s+canciones\s*$", re.IGNORECASE),
    re.compile(r"^\s*volver\s+lista\s*$", re.IGNORECASE),
    re.compile(r"^\s*version\s+en\s+\w+\s*$", re.IGNORECASE),
    re.compile(r"^\s*version\s+en\s*$", re.IGNORECASE),
    re.compile(r"^\s*/+\s*$"),
]


def _get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def fetch_original_html(url: str, timeout: int = 15) -> Optional[str]:
    """Descarga el HTML original de una canción."""
    try:
        resp = requests.get(url, timeout=timeout)
        resp.raise_for_status()
        return resp.text
    except Exception:
        return None


def _is_metadata_line(line: str) -> bool:
    return any(r.fullmatch(line) for r in _METADATA_RES)


def extract_text_from_post_body(soup: BeautifulSoup) -> str:
    """
    Extrae el texto del cuerpo del post conservando espacios de posicionamiento.

    Usa '\n' como separador entre elementos de bloque. Mantiene NBSP y espacios
    múltiples que sirven para alinear acordes sobre la letra.
    """
    body = soup.find("div", class_="post-body")
    if body is None:
        # Fallback: buscar el contenido principal del artículo
        body = soup.find("article") or soup.find("main") or soup.find("body")

    if body is None:
        return ""

    # El separador '\n' respeta los <br>, <div>, <p> como saltos de línea.
    text = body.get_text("\n", strip=False)

    # Eliminar líneas vacías repetidas y líneas de metadatos.
    cleaned_lines: List[str] = []
    prev_empty = False
    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        if not line:
            if not prev_empty:
                cleaned_lines.append("")
            prev_empty = True
            continue
        prev_empty = False

        if _is_metadata_line(line):
            continue

        # Quitar posibles etiquetas HTML residuales (no debería haberlas,
        # pero BeautifulSoup puede dejar comentarios o scripts).
        cleaned_lines.append(line)

    # Eliminar líneas vacías al inicio y final.
    while cleaned_lines and not cleaned_lines[0]:
        cleaned_lines.pop(0)
    while cleaned_lines and not cleaned_lines[-1]:
        cleaned_lines.pop()

    return "\n".join(cleaned_lines)


def compare_texts(actual: str, original: str) -> Dict:
    """Calcula métricas simples de diferencia entre dos textos."""
    actual_lines = actual.splitlines()
    original_lines = original.splitlines()

    common = 0
    diff_indices: List[int] = []
    max_len = max(len(actual_lines), len(original_lines))
    for i in range(max_len):
        a = actual_lines[i] if i < len(actual_lines) else None
        o = original_lines[i] if i < len(original_lines) else None
        if a == o:
            common += 1
        else:
            diff_indices.append(i)

    return {
        "actual_lines": len(actual_lines),
        "original_lines": len(original_lines),
        "common_lines": common,
        "diff_line_count": len(diff_indices),
        "diff_indices": diff_indices[:20],  # limitar para el informe
    }


def generate_report(results: List[Dict], songs: Dict[int, Dict]) -> str:
    """Genera informe HTML de comparación."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    rows: List[str] = []
    for r in results:
        song = songs[r["id"]]
        title = html_module.escape(song["titulo"])
        url = html_module.escape(song["titulo_url"] or "")
        actual_escaped = html_module.escape(r["actual"])
        original_escaped = html_module.escape(r["original"])
        metrics = r["metrics"]

        diff_lines = ",".join(str(i + 1) for i in metrics["diff_indices"])

        rows.append(f"""
        <tr>
          <td style="vertical-align:top; padding:10px; border-bottom:1px solid #ddd;">
            <strong>{title}</strong><br>
            <small><a href="{url}" target="_blank">{url}</a></small><br>
            <small>
              Líneas actual: {metrics['actual_lines']} ·
              Líneas origen: {metrics['original_lines']} ·
              Iguales: {metrics['common_lines']} ·
              Diferentes: {metrics['diff_line_count']}<br>
              Líneas con diff: {diff_lines}
            </small>
          </td>
          <td style="vertical-align:top; padding:10px; border-bottom:1px solid #ddd;">
            <pre style="font-family:monospace; white-space:pre-wrap; background:#f8f8f8; padding:8px; border-radius:4px; max-height:400px; overflow:auto;">{actual_escaped}</pre>
          </td>
          <td style="vertical-align:top; padding:10px; border-bottom:1px solid #ddd;">
            <pre style="font-family:monospace; white-space:pre-wrap; background:#f0fff4; padding:8px; border-radius:4px; max-height:400px; overflow:auto;">{original_escaped}</pre>
          </td>
        </tr>
        """)

    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<title>Informe de corrección de acordes</title>
<style>
  body {{ font-family: sans-serif; margin: 20px; }}
  h1 {{ color: #2c3e50; }}
  table {{ width: 100%; border-collapse: collapse; }}
  th {{ text-align: left; padding: 10px; background: #eee; }}
  td {{ width: 33%; }}
</style>
</head>
<body>
<h1>Informe de corrección de acordes desde web de origen</h1>
<p>Total de canciones analizadas: {len(results)}</p>
<table>
  <thead>
    <tr>
      <th>Canción</th>
      <th>Actual en BD</th>
      <th>Desde origen</th>
    </tr>
  </thead>
  <tbody>
    {''.join(rows)}
  </tbody>
</table>
</body>
</html>
"""
    return html


def apply_correction(cancion_id: int, nuevo_texto: str, conn: sqlite3.Connection) -> None:
    """Aplica la corrección a la BD regenerando los campos derivados."""
    sys.path.insert(0, str(PROJECT_DIR / "src"))
    from parsers.acordes_parser_v3 import AcordesParser

    parser = AcordesParser()
    estructura = parser.parsear_cancion_completa(nuevo_texto)
    html_visual = parser.generar_html_visual(estructura)
    tono = parser.detectar_tono(estructura)

    # Letra sin acordes: concatenar solo las líneas de letra.
    letra_limpia_lines: List[str] = []
    for linea in estructura:
        if linea.tipo == "letra":
            letra_limpia_lines.append(linea.letra)
        elif linea.tipo == "acordes_letra":
            letra_limpia_lines.append(linea.letra)
    letra_sin_acordes = "\n".join(letra_limpia_lines)

    import json
    estructura_json = json.dumps(
        [
            {
                "tipo": linea.tipo,
                "acordes": [{"acorde": a.acorde, "posicion": a.posicion} for a in linea.acordes],
                "letra": linea.letra,
                "texto": linea.texto,
            }
            for linea in estructura
        ],
        ensure_ascii=False,
    )

    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE canciones
        SET letra_con_acordes = ?,
            letra_sin_acordes = ?,
            acordes_json = ?,
            estructura_json = ?,
            html_visual = ?,
            tono = ?
        WHERE id = ?
        """,
        (nuevo_texto, letra_sin_acordes, "", estructura_json, html_visual, tono, cancion_id),
    )
    conn.commit()


def main() -> int:
    parser = argparse.ArgumentParser(description="Corrección de acordes desde web de origen")
    parser.add_argument("--report", action="store_true", help="Generar informe comparativo")
    parser.add_argument("--apply", action="store_true", help="Aplicar correcciones a la BD")
    parser.add_argument("--ids", type=str, help="IDs de canciones separados por comas")
    parser.add_argument("--output", type=str, default=str(OUTPUT_DIR / "informe_acordes.html"),
                        help="Ruta del informe HTML")
    parser.add_argument("--delay", type=float, default=1.0, help="Segundos entre requests")
    args = parser.parse_args()

    if not args.report and not args.apply:
        args.report = True

    conn = _get_connection()
    cursor = conn.cursor()

    if args.ids:
        ids = [int(x.strip()) for x in args.ids.split(",") if x.strip()]
        placeholders = ",".join("?" * len(ids))
        cursor.execute(
            f"SELECT id, titulo, titulo_url, letra_con_acordes FROM canciones WHERE id IN ({placeholders})",
            ids,
        )
    else:
        cursor.execute(
            "SELECT id, titulo, titulo_url, letra_con_acordes FROM canciones "
            "WHERE titulo_url IS NOT NULL AND titulo_url != ''"
        )

    songs = {row["id"]: dict(row) for row in cursor.fetchall()}
    conn.close()

    if not songs:
        print("No hay canciones con URL original para procesar.")
        return 0

    results: List[Dict] = []
    apply_count = 0

    for cancion_id, song in songs.items():
        url = song["titulo_url"]
        if not url:
            continue

        print(f"Procesando {cancion_id}: {song['titulo']} ...")
        html = fetch_original_html(url)
        if not html:
            print(f"  ⚠️ No se pudo descargar {url}")
            continue

        soup = BeautifulSoup(html, "html.parser")
        original_text = extract_text_from_post_body(soup)
        actual_text = song["letra_con_acordes"] or ""

        result = {
            "id": cancion_id,
            "actual": actual_text,
            "original": original_text,
            "metrics": compare_texts(actual_text, original_text),
        }
        results.append(result)

        if args.apply and original_text.strip() and original_text != actual_text:
            conn = _get_connection()
            apply_correction(cancion_id, original_text, conn)
            conn.close()
            apply_count += 1
            print(f"  ✅ Aplicada corrección a canción {cancion_id}")

        time.sleep(args.delay)

    if args.report and results:
        html_report = generate_report(results, songs)
        output_path = Path(args.output)
        output_path.write_text(html_report, encoding="utf-8")
        print(f"\nInforme generado: {output_path}")
        print(f"Abre: file://{output_path.resolve()}")

    if args.apply:
        print(f"\nTotal de correcciones aplicadas: {apply_count}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
