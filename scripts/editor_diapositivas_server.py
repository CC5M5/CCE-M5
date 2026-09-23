#!/usr/bin/env python3
"""
Editor local de diapositivas CCE-M5.

Uso:
  python3 scripts/editor_diapositivas_server.py

Abre http://localhost:4323 en el navegador.

Funcionalidades:
- Listado de diapositivas del catálogo por tipo.
- Editor de diapositiva con previsualización 4:3 a la derecha.
- Botón "Dividir aquí" inserta la marca --- DIAPOSITIVA ---.
- Selector de imagen e ilustración.
- Selector de color litúrgico.
- Duplicar diapositiva.
- Al guardar: actualiza SQLite y hace git commit automático.
"""

from __future__ import annotations

import html as html_module
import json
import os
import re
import sqlite3
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from flask import Flask, abort, request

PROJECT_DIR = Path(__file__).resolve().parents[1]
DB_PATH = PROJECT_DIR / "data" / "db.sqlite3"
ILUSTRACIONES_DIR = PROJECT_DIR / "data" / "ilustraciones"
CATALOGO_PATH = ILUSTRACIONES_DIR / "catalogo.json"
LEMA_PATH = PROJECT_DIR / "data" / "lemas" / "somos_uno.jpg"

app = Flask(__name__)

COLORES_LITURGICOS = {
    "verde": {"from": "#e8f5e9", "to": "#c8e6c9", "acento": "#2e7d32"},
    "blanco": {"from": "#fffdf5", "to": "#f5f5f5", "acento": "#5d4037"},
    "rojo": {"from": "#ffebee", "to": "#ffcdd2", "acento": "#c62828"},
    "morado": {"from": "#f3e5f5", "to": "#e1bee7", "acento": "#6a1b9a"},
    "rosa": {"from": "#fce4ec", "to": "#f8bbd0", "acento": "#ad1457"},
    "negro": {"from": "#eeeeee", "to": "#bdbdbd", "acento": "#212121"},
}


def _get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _git_commit(mensaje: str) -> str:
    try:
        subprocess.run(
            ["git", "add", "data/db.sqlite3"],
            cwd=PROJECT_DIR,
            check=True,
            capture_output=True,
            text=True,
        )
        result = subprocess.run(
            ["git", "commit", "-m", f"chore(slides): {mensaje}",
             "-m", "Actualización manual desde editor local de diapositivas."],
            cwd=PROJECT_DIR,
            check=True,
            capture_output=True,
            text=True,
        )
        subprocess.run(
            ["git", "push", "origin", "main"],
            cwd=PROJECT_DIR,
            check=True,
            capture_output=True,
            text=True,
        )
        m = re.search(r"\[main ([a-f0-9]+)\]", result.stdout)
        return m.group(1) if m else "commit OK"
    except subprocess.CalledProcessError as exc:
        return f"ERROR: {exc.stderr or exc.stdout}"


def _listar_ilustraciones() -> List[str]:
    """Devuelve la lista plana de rutas de ilustraciones del catálogo."""
    if not CATALOGO_PATH.exists():
        return []
    with open(CATALOGO_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    imagenes = data.get("imagenes", {})
    resultado: List[str] = []
    for tipo, rutas in imagenes.items():
        if isinstance(rutas, list):
            resultado.extend(rutas)
    return resultado


def _tipos() -> List[Dict[str, Any]]:
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, nombre, descripcion, orden FROM slides_tipos ORDER BY orden")
    tipos = [{"id": r["id"], "nombre": r["nombre"], "descripcion": r["descripcion"], "orden": r["orden"]} for r in cursor.fetchall()]
    conn.close()
    return tipos


def _get_slides(tipo: Optional[str] = None) -> List[Dict[str, Any]]:
    conn = _get_connection()
    cursor = conn.cursor()
    if tipo:
        cursor.execute(
            "SELECT id, tipo, subtipo, titulo, es_default, activo FROM slides WHERE tipo = ? ORDER BY subtipo, titulo",
            (tipo,),
        )
    else:
        cursor.execute("SELECT id, tipo, subtipo, titulo, es_default, activo FROM slides ORDER BY tipo, subtipo, titulo")
    slides = [{"id": r["id"], "tipo": r["tipo"], "subtipo": r["subtipo"], "titulo": r["titulo"], "es_default": r["es_default"], "activo": r["activo"]} for r in cursor.fetchall()]
    conn.close()
    return slides


def _get_slide(id: int) -> Optional[Dict[str, Any]]:
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM slides WHERE id = ?", (id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        return None
    return dict(row)


def _render_preview(slide: Dict[str, Any]) -> str:
    """Genera un HTML que simula la diapositiva real 4:3."""
    color = slide.get("color_liturgico") or "verde"
    color_info = COLORES_LITURGICOS.get(color, COLORES_LITURGICOS["verde"])
    tipo = slide.get("tipo", "")
    titulo = html_module.escape(slide.get("titulo") or "")
    contenido_raw = slide.get("contenido") or ""
    contenido = html_module.escape(contenido_raw)
    contenido = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", contenido)
    contenido = contenido.replace("\n", "<br>")
    cita = html_module.escape(slide.get("cita") or "")
    subtitulo = html_module.escape(slide.get("subtitulo") or "")
    imagen = slide.get("imagen") or ""

    if imagen and not imagen.startswith(("http://", "https://", "/")):
        imagen_url = f"/__ilustraciones/{imagen.replace('assets/', '')}"
    else:
        imagen_url = imagen or ""

    lema_url = "/__lema/lema_somos_uno.jpg" if LEMA_PATH.exists() else ""

    inner = ""
    if slide.get("momento"):
        inner += f'<h3>{html_module.escape(slide["momento"])}</h3>\n'
    if titulo:
        inner += f'<h1>{titulo}</h1>\n'
    if subtitulo:
        inner += f'<h2>{subtitulo}</h2>\n'
    if cita:
        inner += f'<div class="cita">{cita}</div>\n'
    if contenido:
        inner += f'<div class="contenido">{contenido}</div>\n'

    clase = tipo
    if tipo in ("entrada", "gloria", "aleluya", "ofertorio", "santo", "padre_nuestro", "paz", "comunion", "maria", "despedida"):
        clase += " cancion"

    html = f"""
    <div class="preview-frame {clase}" style="--liturgia-from:{color_info['from']};--liturgia-to:{color_info['to']};--liturgia-acento:{color_info['acento']};">
      <div class="slide-wrapper">
        {f'<img class="ilustracion" src="{imagen_url}" alt="ilustración">' if imagen_url else ''}
        <div class="tarjeta">
          {inner}
        </div>
        {f'<img class="logo-lema" src="{lema_url}" alt="Somos uno">' if lema_url else ''}
      </div>
    </div>
    """
    return html


def _render_base(title: str, sidebar: str, content: str, mensaje: str = "", mensaje_clase: str = "") -> str:
    msg_html = f'<div class="msg {mensaje_clase}">{html_module.escape(mensaje)}</div>' if mensaje else ""
    ilustraciones = _listar_ilustraciones()
    return f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{html_module.escape(title)} - Editor Diapositivas CCE-M5</title>
  <style>
    :root {{ --accent: #7C3AED; --bg: #f8f9fa; --card: #fff; }}
    body {{ font-family: system-ui, sans-serif; background: var(--bg); margin: 0; padding: 20px; }}
    header {{ max-width: 1600px; margin: 0 auto 20px; }}
    h1 {{ color: var(--accent); margin: 0 0 10px; }}
    .container {{ max-width: 1600px; margin: 0 auto; display: grid; grid-template-columns: 280px 1fr; gap: 20px; }}
    aside {{ background: var(--card); border-radius: 12px; padding: 15px; box-shadow: 0 2px 8px rgba(0,0,0,0.05); max-height: 85vh; overflow: auto; }}
    aside details {{ margin-bottom: 10px; }}
    aside summary {{ cursor: pointer; font-weight: 600; color: #333; padding: 6px; border-radius: 6px; }}
    aside summary:hover {{ background: #f0f0f0; }}
    aside a {{ display: block; padding: 5px 8px; color: #444; text-decoration: none; border-radius: 6px; font-size: 13px; }}
    aside a:hover {{ background: #f0f0f0; }}
    aside a.active {{ background: var(--accent); color: #fff; }}
    main {{ background: var(--card); border-radius: 12px; padding: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.05); }}
    label {{ display: block; margin: 12px 0 4px; font-weight: 600; font-size: 14px; color: #555; }}
    input[type="text"], textarea, select {{ width: 100%; padding: 10px; border: 1px solid #ddd; border-radius: 8px; font-size: 15px; box-sizing: border-box; }}
    textarea {{ min-height: 320px; font-family: system-ui, sans-serif; line-height: 1.35; }}
    .two-col {{ display: grid; grid-template-columns: 1fr 480px; gap: 20px; }}
    .preview {{ background: #111; border-radius: 12px; padding: 15px; display: flex; align-items: center; justify-content: center; min-height: 420px; }}
    .preview-frame {{ width: 440px; height: 330px; background: linear-gradient(135deg, var(--liturgia-from) 0%, var(--liturgia-to) 100%); border-radius: 12px; overflow: hidden; position: relative; box-shadow: 0 12px 40px rgba(0,0,0,0.25); }}
    .preview-frame .slide-wrapper {{ width: 100%; height: 100%; display: flex; flex-direction: column; justify-content: center; align-items: flex-start; position: relative; padding: 18px; box-sizing: border-box; }}
    .preview-frame.portada .slide-wrapper {{ justify-content: center; align-items: center; text-align: center; background: linear-gradient(135deg, var(--liturgia-acento) 0%, #6D28D9 100%); }}
    .preview-frame.portada .tarjeta {{ text-align: center; }}
    .preview-frame.portada h1 {{ text-align: center; color: var(--liturgia-acento); }}
    .preview-frame h1 {{ font-size: 16px; color: var(--liturgia-acento); text-transform: uppercase; margin: 0 0 6px; }}
    .preview-frame h2 {{ font-size: 12px; color: #555; margin: 0 0 6px; font-weight: 400; }}
    .preview-frame h3 {{ font-size: 10px; text-transform: uppercase; letter-spacing: 0.08em; color: #777; margin: 0 0 4px; }}
    .preview-frame .cita {{ font-size: 10px; font-weight: 700; background: linear-gradient(90deg, var(--liturgia-acento), #A16207); color: white; padding: 2px 6px; border-radius: 4px; display: inline-block; margin-bottom: 6px; }}
    .preview-frame .contenido {{ font-size: 11px; line-height: 1.25; color: #2c3e50; white-space: pre-wrap; }}
    .preview-frame .contenido br {{ display: block; content: ""; margin-bottom: 0.05em; }}
    .preview-frame.cancion .contenido {{ line-height: 1.22; }}
    .preview-frame.cancion .contenido br {{ margin-bottom: 0; }}
    .preview-frame .tarjeta {{ background: rgba(255,255,255,0.94); border-radius: 12px; padding: 14px 18px; box-shadow: 0 8px 24px rgba(124,58,237,0.12); max-height: 86%; overflow: auto; z-index: 5; }}
    .preview-frame .ilustracion {{ position: absolute; bottom: 50px; right: 18px; max-width: 110px; max-height: 110px; opacity: 0.98; z-index: 6; border-radius: 8px; object-fit: contain; }}
    .preview-frame .logo-lema {{ position: absolute; bottom: 10px; right: 14px; height: 22px; width: auto; z-index: 10; }}
    .preview-frame:has(.ilustracion) .tarjeta {{ margin-right: 110px; }}
    button {{ background: var(--accent); color: #fff; border: none; padding: 12px 22px; border-radius: 8px; font-size: 15px; cursor: pointer; margin-top: 12px; margin-right: 8px; }}
    button:hover {{ opacity: 0.9; }}
    button.secondary {{ background: #64748b; }}
    .msg {{ padding: 12px; border-radius: 8px; margin-bottom: 15px; }}
    .msg.ok {{ background: #d1fae5; color: #065f46; }}
    .msg.err {{ background: #fee2e2; color: #991b1b; }}
    .miniaturas {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(90px, 1fr)); gap: 8px; max-height: 200px; overflow: auto; padding: 8px; border: 1px solid #eee; border-radius: 8px; }}
    .miniaturas label {{ display: flex; flex-direction: column; align-items: center; cursor: pointer; margin: 0; }}
    .miniaturas img {{ width: 70px; height: 70px; object-fit: contain; border-radius: 6px; border: 2px solid transparent; }}
    .miniaturas input {{ display: none; }}
    .miniaturas input:checked + img {{ border-color: var(--accent); }}
    .toolbar {{ display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 12px; }}
    @media (max-width: 1100px) {{
      .container {{ grid-template-columns: 1fr; }}
      .two-col {{ grid-template-columns: 1fr; }}
      .preview-frame {{ width: 100%; height: auto; aspect-ratio: 4/3; }}
    }}
  </style>
</head>
<body>
  <header>
    <h1>🖼️ Editor de Diapositivas CCE-M5</h1>
    <p>Edición local del catálogo de diapositivas. Preview 4:3 a la derecha.</p>
  </header>
  <div class="container">
    <aside>
      <p><strong>Catálogo</strong></p>
      {sidebar}
    </aside>
    <main>
      {msg_html}
      {content}
    </main>
  </div>
</body>
</html>"""


@app.route("/")
def index():
    tipos = _tipos()
    sidebar_parts = []
    for t in tipos:
        slides = _get_slides(t["id"])
        if not slides:
            continue
        links = "\n".join(
            f'<a href="/slides/{s["id"]}">{html_module.escape(s["titulo"] or "(sin título)")} <small>({html_module.escape(s["subtipo"])}{" ★" if s["es_default"] else ""})</small></a>'
            for s in slides
        )
        sidebar_parts.append(f'<details open><summary>{html_module.escape(t["nombre"])} ({len(slides)})</summary>{links}</details>')
    sidebar = "\n".join(sidebar_parts)
    content = "<h2>Selecciona una diapositiva</h2><p>Elige una diapositiva del menú lateral para editarla.</p>"
    return _render_base("Diapositivas", sidebar, content)


@app.route("/slides/<int:id>")
def editar(id: int):
    slide = _get_slide(id)
    if slide is None:
        abort(404)

    tipos = _tipos()
    sidebar_parts = []
    for t in tipos:
        slides = _get_slides(t["id"])
        if not slides:
            continue
        def _link_for(s):
            active = ' class="active"' if s["id"] == id else ""
            return f'<a href="/slides/{s["id"]}"{active}>{html_module.escape(s["titulo"] or "(sin título)")} <small>({html_module.escape(s["subtipo"])}{" ★" if s["es_default"] else ""})</small></a>'
        links = "\n".join(_link_for(s) for s in slides)
        sidebar_parts.append(f'<details open><summary>{html_module.escape(t["nombre"])}</summary>{links}</details>')
    sidebar = "\n".join(sidebar_parts)

    tipo_options = "\n".join(
        f'<option value="{html_module.escape(t["id"])}" {"selected" if t["id"] == slide["tipo"] else ""}>{html_module.escape(t["nombre"])}</option>'
        for t in tipos
    )
    color_options = "\n".join(
        f'<option value="{c}" {"selected" if c == (slide.get("color_liturgico") or "verde") else ""}>{c.capitalize()}</option>'
        for c in COLORES_LITURGICOS.keys()
    )

    ilustraciones = _listar_ilustraciones()
    imagen_actual = slide.get("imagen") or ""
    miniaturas = "\n".join(
        f"""<label>
          <input type="radio" name="imagen" value="{html_module.escape(img)}" {"checked" if img == imagen_actual else ""}>
          <img src="/__ilustraciones/{html_module.escape(img)}" alt="{html_module.escape(img)}">
          <small>{html_module.escape(Path(img).stem[:18])}</small>
        </label>"""
        for img in ilustraciones[:60]
    )

    preview = _render_preview(slide)

    content = f"""<h2>Editar diapositiva #{slide['id']}</h2>
    <form method="post" action="/slides/{slide['id']}/guardar" id="editor-form">
      <div class="two-col">
        <div>
          <label>Tipo</label>
          <select name="tipo">{tipo_options}</select>

          <label>Subtipo / variante</label>
          <input type="text" name="subtipo" value="{html_module.escape(slide.get('subtipo') or 'general')}">

          <label><input type="checkbox" name="es_default" value="1" {"checked" if slide.get('es_default') else ""}> Es la variante por defecto</label>

          <label>Título</label>
          <input type="text" name="titulo" value="{html_module.escape(slide.get('titulo') or '')}">

          <label>Subtítulo</label>
          <input type="text" name="subtitulo" value="{html_module.escape(slide.get('subtitulo') or '')}">

          <label>Cita</label>
          <input type="text" name="cita" value="{html_module.escape(slide.get('cita') or '')}">

          <label>Color litúrgico (para preview)</label>
          <select name="color_liturgico">{color_options}</select>

          <label>Contenido</label>
          <textarea name="contenido" id="contenido">{html_module.escape(slide.get('contenido') or '')}</textarea>

          <div class="toolbar">
            <button type="button" onclick="insertarSplit()">➗ Dividir aquí</button>
          </div>

          <label>Imagen</label>
          <div class="miniaturas">{miniaturas}</div>

          <label>Notas internas</label>
          <textarea name="notas" style="min-height:80px">{html_module.escape(slide.get('notas') or '')}</textarea>

          <div class="toolbar">
            <button type="submit">💾 Guardar y commitear</button>
            <button type="submit" formaction="/slides/{slide['id']}/duplicar" class="secondary">📄 Duplicar</button>
          </div>
        </div>
        <div>
          <label>Preview 4:3</label>
          <div class="preview">
            {preview}
          </div>
        </div>
      </div>
    </form>
    <script>
      function insertarSplit() {{
        const ta = document.getElementById('contenido');
        const start = ta.selectionStart;
        const end = ta.selectionEnd;
        const text = ta.value;
        ta.value = text.substring(0, start) + '--- DIAPOSITIVA ---' + text.substring(end);
        ta.focus();
        ta.setSelectionRange(start + '--- DIAPOSITIVA ---'.length, start + '--- DIAPOSITIVA ---'.length);
      }}
    </script>"""
    return _render_base(slide.get("titulo") or "Diapositiva", sidebar, content)


@app.route("/slides/<int:id>/guardar", methods=["POST"])
def guardar(id: int):
    slide = _get_slide(id)
    if slide is None:
        abort(404)

    campos = {
        "tipo": request.form.get("tipo", slide["tipo"]),
        "subtipo": request.form.get("subtipo", slide.get("subtipo") or "general"),
        "titulo": request.form.get("titulo", ""),
        "subtitulo": request.form.get("subtitulo", ""),
        "contenido": request.form.get("contenido", ""),
        "cita": request.form.get("cita", ""),
        "imagen": request.form.get("imagen", ""),
        "color_liturgico": request.form.get("color_liturgico", "verde"),
        "notas": request.form.get("notas", ""),
        "es_default": 1 if request.form.get("es_default") else 0,
        "activo": 1,
    }

    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE slides
        SET tipo = ?, subtipo = ?, titulo = ?, subtitulo = ?, contenido = ?, cita = ?,
            imagen = ?, color_liturgico = ?, notas = ?, es_default = ?, activo = ?,
            fecha_modificacion = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (campos["tipo"], campos["subtipo"], campos["titulo"], campos["subtitulo"],
         campos["contenido"], campos["cita"], campos["imagen"], campos["color_liturgico"],
         campos["notas"], campos["es_default"], campos["activo"], id),
    )
    conn.commit()
    conn.close()

    commit_result = _git_commit(f"editar diapositiva {id} - {campos['titulo']}")
    mensaje = f"✅ Guardado y commiteado ({commit_result})." if not commit_result.startswith("ERROR") else f"⚠️ Guardado en BD, falló git: {commit_result}"
    clase = "ok" if not commit_result.startswith("ERROR") else "err"

    return editar_con_mensaje(id, mensaje, clase)


@app.route("/slides/<int:id>/duplicar", methods=["POST"])
def duplicar(id: int):
    slide = _get_slide(id)
    if slide is None:
        abort(404)

    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO slides (tipo, subtipo, titulo, subtitulo, contenido, cita, imagen,
                            color_liturgico, notas, es_default, activo)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0, 1)
        """,
        (slide["tipo"], f"{slide['subtipo']}_copia", slide["titulo"], slide["subtitulo"],
         slide["contenido"], slide["cita"], slide["imagen"], slide.get("color_liturgico", "verde"),
         slide.get("notas", "")),
    )
    nuevo_id = cursor.lastrowid
    conn.commit()
    conn.close()

    commit_result = _git_commit(f"duplicar diapositiva {id} -> {nuevo_id}")
    mensaje = f"✅ Duplicada como #{nuevo_id} y commiteado ({commit_result})." if not commit_result.startswith("ERROR") else f"⚠️ Duplicada, falló git: {commit_result}"
    return editar_con_mensaje(nuevo_id, mensaje, "ok" if not commit_result.startswith("ERROR") else "err")


def editar_con_mensaje(id: int, mensaje: str, clase: str):
    """Re-renderiza la vista de edición con un mensaje."""
    html = editar(id)
    if isinstance(html, tuple):
        body, status = html
        body = body.replace("<main>", f'<main>\n<div class="msg {clase}">{html_module.escape(mensaje)}</div>')
        return body, status
    html = html.replace("<main>", f'<main>\n<div class="msg {clase}">{html_module.escape(mensaje)}</div>')
    return html


@app.route("/__ilustraciones/<path:filename>")
def ilustracion(filename: str):
    safe = Path(filename).name
    candidate = ILUSTRACIONES_DIR / filename
    if candidate.exists() and candidate.is_file():
        from flask import send_file
        return send_file(candidate)
    abort(404)


@app.route("/__lema/<path:filename>")
def lema(filename: str):
    if LEMA_PATH.exists():
        from flask import send_file
        return send_file(LEMA_PATH)
    abort(404)


def main():
    host = os.environ.get("EDITOR_HOST", "0.0.0.0")
    port = int(os.environ.get("EDITOR_PORT", "4323"))
    app.run(host=host, port=port, debug=False)


if __name__ == "__main__":
    main()
