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
import sys
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
        err = exc.stderr or exc.stdout or ""
        if "nothing to commit" in err or "working tree clean" in err or "No changes" in err:
            return "sin cambios"
        return f"ERROR: {err}"


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



# --- Momentos litúrgicos ---
MOMENTOS_LITURGICOS = [
    "entrada", "acto penitencial", "gloria", "primera_lectura", "salmo",
    "segunda_lectura", "aleluya", "evangelio", "credo", "ofertorio", "santo",
    "padre_nuestro", "paz", "comunion", "maria", "despedida", "general"
]


def _get_momentos_cancion(cancion_id: int) -> List[str]:
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT momento_liturgico FROM cancion_momentos WHERE cancion_id = ? ORDER BY momento_liturgico",
        (cancion_id,),
    )
    rows = [r["momento_liturgico"] for r in cursor.fetchall()]
    conn.close()
    return rows


def _set_momentos_cancion(cancion_id: int, momentos: List[str]) -> None:
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM cancion_momentos WHERE cancion_id = ?", (cancion_id,))
    for m in momentos:
        m = m.strip().lower()
        if m:
            cursor.execute(
                "INSERT OR IGNORE INTO cancion_momentos (cancion_id, momento_liturgico) VALUES (?, ?)",
                (cancion_id, m),
            )
    conn.commit()
    conn.close()

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


def _apply_bold_html(text: str) -> str:
    """Convierte **texto** en <strong>texto</strong>, permitiendo espacios opcionales."""
    return re.sub(r"\*\*\s*(.+?)\s*\*\*", r"<strong>\1</strong>", text)


def _render_preview(slide: Dict[str, Any]) -> str:
    """Genera HTML que simula la diapositiva real 4:3, dividiendo si hay --- DIAPOSITIVA ---."""
    color = slide.get("color_liturgico") or "verde"
    color_info = COLORES_LITURGICOS.get(color, COLORES_LITURGICOS["verde"])
    tipo = slide.get("tipo", "")
    titulo = html_module.escape(slide.get("titulo") or "")
    subtitulo = html_module.escape(slide.get("subtitulo") or "")
    cita = html_module.escape(slide.get("cita") or "")
    imagen = slide.get("imagen") or ""

    if imagen and not imagen.startswith(("http://", "https://", "/")):
        imagen_url = f"/__ilustraciones/{imagen.replace('assets/', '')}"
    else:
        imagen_url = imagen or ""

    lema_url = "/__lema/lema_somos_uno.jpg" if LEMA_PATH.exists() else ""

    clase = tipo
    if tipo in ("entrada", "gloria", "aleluya", "ofertorio", "santo", "padre_nuestro", "paz", "comunion", "maria", "despedida"):
        clase += " cancion"

    # Dividir contenido por marca --- DIAPOSITIVA ---
    contenido_raw = slide.get("contenido") or ""
    partes = re.split(r"(?m)^\s*---\s*DIAPOSITIVA\s*---\s*$", contenido_raw)
    partes = [p.strip() for p in partes if p.strip()]
    if not partes:
        partes = [""]

    def _render_slide_mini(contenido_parte: str, idx: int, total: int) -> str:
        contenido = html_module.escape(contenido_parte)
        contenido = _apply_bold_html(contenido)
        contenido = contenido.replace("\n", "<br>")

        inner = ""
        if slide.get("momento"):
            inner += f'<h3>{html_module.escape(slide["momento"])}{f" ({idx}/{total})" if total > 1 else ""}</h3>\n'
        if titulo:
            inner += f'<h1>{titulo}{f" ({idx}/{total})" if total > 1 else ""}</h1>\n'
        if subtitulo:
            inner += f'<h2>{subtitulo}</h2>\n'
        if cita:
            inner += f'<div class="cita">{cita}</div>\n'
        if contenido:
            inner += f'<div class="contenido">{contenido}</div>\n'

        return f"""
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

    slides_html = "\n".join(_render_slide_mini(parte, i + 1, len(partes)) for i, parte in enumerate(partes))
    return f'<div style="display:flex;flex-direction:column;gap:12px;align-items:center;">{slides_html}</div>' if len(partes) > 1 else slides_html


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
    .miniaturas {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(120px, 1fr)); gap: 10px; max-height: 360px; overflow: auto; padding: 10px; border: 1px solid #eee; border-radius: 8px; }}
    .miniaturas label {{ display: flex; flex-direction: column; align-items: center; cursor: pointer; margin: 0; padding: 6px; border-radius: 8px; position: relative; }}
    .miniaturas label:hover {{ background: #f3f0ff; }}
    .miniaturas img {{ width: 100px; height: 100px; object-fit: contain; border-radius: 8px; border: 2px solid transparent; background: #f8f8f8; }}
    .miniaturas input {{ display: none; }}
    .miniaturas input:checked + img {{ border-color: var(--accent); background: #ede9fe; }}
    .miniaturas small {{ font-size: 10px; color: #666; text-align: center; max-width: 110px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }}
    .miniaturas label:hover small {{ white-space: normal; overflow: visible; position: absolute; bottom: 2px; left: 2px; right: 2px; background: rgba(255,255,255,0.95); padding: 3px; border-radius: 4px; z-index: 10; box-shadow: 0 2px 6px rgba(0,0,0,0.1); }}
    .filtros-imagenes {{ display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 10px; }}
    .filtros-imagenes button {{ margin: 0; padding: 6px 12px; font-size: 13px; background: #e2e8f0; color: #334155; }}
    .filtros-imagenes button.active {{ background: var(--accent); color: #fff; }}
    .buscador-imagenes {{ width: 100%; padding: 8px; border: 1px solid #ddd; border-radius: 8px; margin-bottom: 10px; font-size: 14px; }}
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
    <p>Edición local del catálogo de diapositivas y presentaciones semanales.</p>
    <nav style="margin-top:10px;display:flex;gap:12px;flex-wrap:wrap;">
      <a href="/slides/" style="text-decoration:none;background:var(--accent);color:#fff;padding:8px 14px;border-radius:8px;font-size:14px;">📑 Catálogo de diapositivas</a>
      <a href="/presentaciones/" style="text-decoration:none;background:#475569;color:#fff;padding:8px 14px;border-radius:8px;font-size:14px;">📅 Presentaciones semanales</a>
    </nav>
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
    # Agrupar por artista para los filtros
    artistas = sorted(set(Path(img).parts[0] for img in ilustraciones))
    botones_filtro = " ".join(
        f'<button type="button" class="{html_module.escape(a)}" data-filtro="{html_module.escape(a)}" onclick="filtrarImagenes(this.dataset.filtro)">{html_module.escape(a.upper())}</button>'
        for a in artistas
    )
    botones_filtro = f'<button type="button" class="active" data-filtro="todos" onclick="filtrarImagenes(this.dataset.filtro)">TODOS</button>' + botones_filtro

    def _miniatura(img: str) -> str:
        artista = html_module.escape(Path(img).parts[0])
        nombre = html_module.escape(Path(img).stem[:22])
        nombre_completo = html_module.escape(Path(img).name)
        return f"""<label data-artista="{artista}" data-nombre="{html_module.escape(Path(img).name.lower())}">
          <input type="radio" name="imagen" value="{html_module.escape(img)}" {"checked" if img == imagen_actual else ""}>
          <img src="/__ilustraciones/{html_module.escape(img)}" alt="{html_module.escape(img)}">
          <small title="{nombre_completo}">{nombre}</small>
        </label>"""

    miniaturas = "\n".join(_miniatura(img) for img in ilustraciones)

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
          <div class="filtros-imagenes">{botones_filtro}</div>
          <input type="text" class="buscador-imagenes" placeholder="Buscar ilustración..." oninput="buscarImagenes(this.value)">
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
      function filtrarImagenes(filtro) {{
        document.querySelectorAll('.filtros-imagenes button').forEach(b => b.classList.remove('active'));
        event.target.classList.add('active');
        const labels = document.querySelectorAll('.miniaturas label');
        labels.forEach(lbl => {{
          const artista = lbl.dataset.artista || '';
          lbl.style.display = (filtro === 'todos' || artista === filtro) ? 'flex' : 'none';
        }});
      }}
      function buscarImagenes(texto) {{
        const q = texto.toLowerCase();
        const labels = document.querySelectorAll('.miniaturas label');
        labels.forEach(lbl => {{
          const nombre = lbl.dataset.nombre || '';
          const artista = lbl.dataset.artista || '';
          const visible = q === '' || nombre.includes(q) || artista.toLowerCase().includes(q);
          lbl.style.display = visible ? 'flex' : 'none';
        }});
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
    from flask import send_file
    candidate = (ILUSTRACIONES_DIR / filename).resolve()
    # Prevenir path traversal fuera del directorio de ilustraciones
    if not str(candidate).startswith(str(ILUSTRACIONES_DIR.resolve())):
        abort(403)
    if candidate.exists() and candidate.is_file():
        return send_file(candidate)
    abort(404)


@app.route("/__lema/<path:filename>")
def lema(filename: str):
    if LEMA_PATH.exists():
        from flask import send_file
        return send_file(LEMA_PATH)
    abort(404)

@app.route("/presentaciones_html/<path:filename>")
def presentaciones_html_file(filename: str):
    base = PROJECT_DIR / "presentaciones_html"
    target = (base / filename).resolve()
    if not str(target).startswith(str(base)):
        abort(403)
    if target.exists() and target.is_file():
        from flask import send_file
        return send_file(target)
    abort(404)




# ------------------------------------------------------------------
# Helper para reconstruir composicion desde canciones asignadas
# ------------------------------------------------------------------

def _reconstruir_composicion_desde_canciones(fecha: str) -> str:
    """Borra la composicion guardada y la reconstruye desde canciones_json."""
    pres = _get_presentacion_por_fecha(fecha)
    if not pres:
        return f"No existe presentacion para {fecha}"
    items = _proponer_composicion(fecha)
    if not items:
        return "No se pudo proponer composicion"
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM presentacion_slides WHERE presentacion_id = ?", (pres["id"],))
    for item in items:
        slide_id = item.get("slide_id")
        if slide_id:
            cursor.execute("""
                INSERT INTO presentacion_slides
                (presentacion_id, slide_id, numero, tipo, subtipo, titulo, contenido, cita, subtitulo, imagen, momento, activo)
                SELECT ?, s.id, ?, ?, ?, s.titulo, s.contenido, s.cita, s.subtitulo, s.imagen, '', ?
                FROM slides s
                WHERE s.id = ?
            """, (pres["id"], item["numero"], item["tipo"], item["subtipo"], item["activo"], slide_id))
            if cursor.rowcount == 0:
                slide_id = None
        if not slide_id:
            cursor.execute("""
                INSERT INTO presentacion_slides
                (presentacion_id, slide_id, numero, tipo, subtipo, titulo, contenido, activo)
                VALUES (?, NULL, ?, ?, ?, ?, '', ?)
            """, (pres["id"], item["numero"], item["tipo"], item["subtipo"], item["titulo"], item["activo"]))
    conn.commit()
    conn.close()
    return f"Composicion reconstruida ({len(items)} items)"

# ------------------------------------------------------------------
# Helper para generar presentación desde composición (Fase D)
# ------------------------------------------------------------------

def _generar_presentacion(fecha: str) -> str:
    """Genera PPTX/HTML/PDF desde presentacion_slides y sincroniza con la web."""
    sys.path.insert(0, str(PROJECT_DIR / "src" / "generators"))
    try:
        from generar_desde_composicion import GeneradorDesdeComposicion
        gen = GeneradorDesdeComposicion()
        bundle = gen.generar_desde_presentacion(fecha)
        # Sincronizar a web/public/presentaciones_html/
        try:
            subprocess.run(
                [sys.executable, str(PROJECT_DIR / "scripts" / "sync_presentaciones_html.py"), "--fecha", fecha],
                cwd=PROJECT_DIR,
                check=True,
                capture_output=True,
                text=True,
            )
            sync_ok = f" | sincronizado a web/public/presentaciones_html/{fecha}_presentacion"
        except subprocess.CalledProcessError as exc:
            sync_ok = f" | ⚠️ sync falló: {exc.stderr or exc.stdout}"
        # Reconstruir cancionero web para actualizar web/dist/
        try:
            build_result = subprocess.run(
                ["npm", "run", "build"],
                cwd=str(PROJECT_DIR / "web"),
                check=True,
                capture_output=True,
                text=True,
                timeout=300,
            )
            build_ok = " | web rebuild OK"
        except subprocess.TimeoutExpired:
            build_ok = " | ⚠️ web build timeout (5min)"
        except subprocess.CalledProcessError as exc:
            build_ok = f" | ⚠️ web build falló: {exc.stderr or exc.stdout}"
        # Marcar estado como publicado
        try:
            conn = _get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "UPDATE presentaciones SET estado = 'publicado' WHERE fecha_domingo = ?",
                (fecha,),
            )
            conn.commit()
            conn.close()
            estado_ok = " | estado: publicado"
        except Exception as e:
            estado_ok = f" | ⚠️ estado falló: {e}"
        # Commit automático incluyendo bundle web
        try:
            subprocess.run(
                ["git", "add", "presentaciones_html/", "data/db.sqlite3"],
                cwd=PROJECT_DIR,
                check=True,
                capture_output=True,
                text=True,
            )
            commit_msg = f"feat(presentacion): genera bundle {fecha}"
            result = subprocess.run(
                ["git", "commit", "-m", commit_msg,
                 "-m", f"Generado desde editor local: {bundle.name}"],
                cwd=PROJECT_DIR,
                check=True,
                capture_output=True,
                text=True,
            )
            push_result = subprocess.run(
                ["git", "push", "origin", "main"],
                cwd=PROJECT_DIR,
                check=True,
                capture_output=True,
                text=True,
            )
            m = re.search(r"\[main ([a-f0-9]+)\]", result.stdout)
            commit_hash = m.group(1) if m else "commit OK"
        except subprocess.CalledProcessError as exc:
            commit_hash = f"ERROR: {exc.stderr or exc.stdout}"
        return f"✅ Presentación generada en {bundle} {sync_ok}{build_ok}{estado_ok} | {commit_hash}"
    except Exception as e:
        return f"⚠️ Error al generar: {e}"


# ------------------------------------------------------------------
# FASE C: Armado de presentación semanal desde el catálogo
# ------------------------------------------------------------------

ORDEN_MOMENTOS_C: List[tuple[str, str]] = [
    ("portada", "general"),
    ("entrada", ""),
    ("transicion_palabra", "general"),
    ("perdon", ""),
    ("paso", "neutro"),
    ("gloria", ""),
    ("primera_lectura", "general"),
    ("salmo", "general"),
    ("segunda_lectura", "general"),
    ("aleluya", ""),
    ("evangelio", "general"),
    ("transicion_eucaristia", "general"),
    ("credo", "texto_fijo"),
    ("paso", "neutro"),
    ("ofertorio", ""),
    ("paso", "neutro"),
    ("santo", ""),
    ("paso", "neutro"),
    ("padre_nuestro", ""),
    ("paso", "neutro"),
    ("paz", ""),
    ("paso", "neutro"),
    ("comunion", ""),
    ("paso", "neutro"),
    ("maria", ""),
    ("paso", "neutro"),
    ("despedida", ""),
    ("portada", "despedida"),
]

MOMENTOS_MUSICALES = ("entrada", "gloria", "aleluya", "ofertorio", "santo", "padre_nuestro", "paz", "comunion", "maria", "despedida")


def _get_presentaciones() -> List[Dict[str, Any]]:
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT p.id, p.fecha_domingo, p.estado, l.celebracion, l.color_liturgico,
               (SELECT COUNT(*) FROM presentacion_slides ps WHERE ps.presentacion_id = p.id AND ps.activo = 1) AS num_slides
        FROM presentaciones p
        LEFT JOIN lecturas l ON l.id = p.lectura_id
        ORDER BY p.fecha_domingo DESC
    """)
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows


def _get_presentacion_por_fecha(fecha: str) -> Optional[Dict[str, Any]]:
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT p.*, l.celebracion, l.color_liturgico,
               l.primera_lectura_libro, l.primera_lectura_cita, l.primera_lectura_texto,
               l.salmo_libro, l.salmo_cita, l.salmo_antifona, l.salmo_texto,
               l.segunda_lectura_libro, l.segunda_lectura_cita, l.segunda_lectura_texto,
               l.evangelio_libro, l.evangelio_cita, l.evangelio_texto
        FROM presentaciones p
        LEFT JOIN lecturas l ON l.id = p.lectura_id
        WHERE p.fecha_domingo = ?
    """, (fecha,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None


def _canciones_asignadas(canciones_json: Optional[str]) -> Dict[str, int]:
    """Devuelve {momento: cancion_id} desde el JSON de la presentación."""
    if not canciones_json:
        return {}
    try:
        data = json.loads(canciones_json)
    except Exception:
        return {}
    if isinstance(data, dict):
        # formato {momento: {"id": X}}
        resultado = {}
        for momento, info in data.items():
            if isinstance(info, dict) and "id" in info:
                resultado[momento] = int(info["id"])
            elif isinstance(info, int):
                resultado[momento] = info
        return resultado
    return {}


def _get_slide_variantes(tipo: str) -> List[Dict[str, Any]]:
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT id, subtipo, titulo, es_default
        FROM slides
        WHERE tipo = ? AND activo = 1
        ORDER BY es_default DESC, titulo
    """, (tipo,))
    rows = [{"id": r["id"], "subtipo": r["subtipo"], "titulo": r["titulo"], "es_default": r["es_default"]} for r in cursor.fetchall()]
    conn.close()
    return rows


def _slide_para_momento(tipo: str, subtipo_sugerido: str) -> Optional[Dict[str, Any]]:
    """Busca la mejor slide del catálogo para un momento dado."""
    conn = _get_connection()
    cursor = conn.cursor()
    # 1. subtipo exacto y default
    cursor.execute("""
        SELECT * FROM slides
        WHERE tipo = ? AND subtipo = ? AND activo = 1
        ORDER BY es_default DESC, id
        LIMIT 1
    """, (tipo, subtipo_sugerido))
    row = cursor.fetchone()
    if not row:
        # 2. cualquier subtipo default
        cursor.execute("""
            SELECT * FROM slides
            WHERE tipo = ? AND es_default = 1 AND activo = 1
            ORDER BY id
            LIMIT 1
        """, (tipo,))
        row = cursor.fetchone()
    if not row:
        # 3. cualquier slide activa del tipo
        cursor.execute("""
            SELECT * FROM slides
            WHERE tipo = ? AND activo = 1
            ORDER BY id
            LIMIT 1
        """, (tipo,))
        row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None




def _formatear_fecha_preview(fecha: str) -> str:
    try:
        from datetime import datetime
        dt = datetime.strptime(fecha, "%Y-%m-%d")
        meses = ["enero", "febrero", "marzo", "abril", "mayo", "junio",
                 "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
        return f"{dt.day} de {meses[dt.month - 1]} de {dt.year}"
    except Exception:
        return fecha


def _proponer_composicion(fecha: str) -> List[Dict[str, Any]]:
    """Genera la lista de items propuestos para una fecha."""
    pres = _get_presentacion_por_fecha(fecha)
    if not pres:
        return []
    canciones = _canciones_asignadas(pres.get("canciones_json"))
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT c.id, c.titulo, GROUP_CONCAT(cm.momento_liturgico, ',') as momentos
        FROM canciones c
        LEFT JOIN cancion_momentos cm ON cm.cancion_id = c.id
        GROUP BY c.id
    """)
    canciones_info = {
        r["id"]: {"titulo": r["titulo"], "momento": r["momentos"].split(",")[0] if r["momentos"] else r["momento_liturgico"]}
        for r in cursor.fetchall()
    }
    conn.close()

    items: List[Dict[str, Any]] = []
    numero = 1
    for tipo, subtipo_default in ORDEN_MOMENTOS_C:
        if tipo == "paso":
            items.append({
                "numero": numero,
                "tipo": "paso",
                "subtipo": f"paso_{subtipo_default}",
                "titulo": "",
                "slide_id": None,
                "activo": 1,
                "_es_paso": True,
            })
            numero += 1
            continue

        subtipo = subtipo_default
        if tipo in MOMENTOS_MUSICALES and tipo in canciones:
            cancion_id = canciones[tipo]
            # Si existe variante específica de esa canción, preferirla
            slide_pref = _slide_para_momento(tipo, f"cancion_{cancion_id}")
            if slide_pref:
                subtipo = f"cancion_{cancion_id}"
            else:
                slide_pref = _slide_para_momento(tipo, subtipo_default)
        else:
            slide_pref = _slide_para_momento(tipo, subtipo_default)

        if not slide_pref:
            items.append({
                "numero": numero,
                "tipo": tipo,
                "subtipo": subtipo,
                "titulo": f"[FALTA: {tipo}]",
                "slide_id": None,
                "activo": 1,
                "_es_paso": False,
            })
        else:
            items.append({
                "numero": numero,
                "tipo": tipo,
                "subtipo": slide_pref["subtipo"],
                "titulo": slide_pref["titulo"],
                "slide_id": slide_pref["id"],
                "activo": 1,
                "_es_paso": False,
            })
        numero += 1
    return items


def _get_composicion_guardada(fecha: str) -> List[Dict[str, Any]]:
    pres = _get_presentacion_por_fecha(fecha)
    if not pres:
        return []
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT ps.*, s.contenido AS slide_contenido, s.imagen AS slide_imagen, s.color_liturgico AS slide_color
        FROM presentacion_slides ps
        LEFT JOIN slides s ON s.id = ps.slide_id
        WHERE ps.presentacion_id = ? AND ps.activo = 1
        ORDER BY ps.numero
    """, (pres["id"],))
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows


@app.route("/presentaciones/")
def listar_presentaciones():
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

    pres = _get_presentaciones()
    def _badge_estado(estado):
        color = {"borrador": "#f59e0b", "generado": "#10b981", "publicado": "#7c3aed"}.get(estado, "#64748b")
        label = {"borrador": "🟡 Borrador", "generado": "🟢 Generado", "publicado": "🟣 Publicado"}.get(estado, estado)
        return f'<span style="display:inline-block;padding:3px 8px;border-radius:6px;background:{color};color:#fff;font-size:12px;font-weight:600;">{label}</span>'
    filas = "\n".join(
        f'<tr><td><a href="/presentacion/{p["fecha_domingo"]}/armar">{p["fecha_domingo"]}</a></td><td>{html_module.escape(p["celebracion"] or "-")}</td><td>{html_module.escape(p["color_liturgico"] or "-")}</td><td>{p["num_slides"]}</td><td>{_badge_estado(p["estado"] or "borrador")}</td></tr>'
        for p in pres
    )
    content = f"""<h2>Presentaciones semanales</h2>
    <p>Selecciona una fecha para armar la composición de diapositivas desde el catálogo.</p>
    <table style="width:100%;border-collapse:collapse">
      <thead>
        <tr style="text-align:left;border-bottom:2px solid #ddd"><th>Fecha</th><th>Celebración</th><th>Color</th><th>Slides</th><th>Estado</th></tr>
      </thead>
      <tbody>{filas}</tbody>
    </table>"""
    return _render_base("Presentaciones", sidebar, content)


@app.route("/presentacion/<fecha>/armar")
def armar_presentacion(fecha: str):
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", fecha):
        abort(400)

    pres = _get_presentacion_por_fecha(fecha)
    if not pres:
        abort(404)

    # Preferir composición guardada; si no, proponer
    composicion = _get_composicion_guardada(fecha)
    if not composicion:
        composicion = _proponer_composicion(fecha)

    # Cargar variantes para cada tipo usado
    variantes_cache: Dict[str, List[Dict[str, Any]]] = {}
    def variantes_para(tipo: str) -> List[Dict[str, Any]]:
        if tipo not in variantes_cache:
            variantes_cache[tipo] = _get_slide_variantes(tipo)
        return variantes_cache[tipo]

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
        sidebar_parts.append(f'<details><summary>{html_module.escape(t["nombre"])} ({len(slides)})</summary>{links}</details>')
    sidebar = "\n".join(sidebar_parts)

    filas = []
    for item in composicion:
        variantes = variantes_para(item["tipo"])
        opts = "\n".join(
            f'<option value="{html_module.escape(v["subtipo"])}" {"selected" if v["subtipo"] == item["subtipo"] else ""}>'
            f'{html_module.escape(v["titulo"])} ({html_module.escape(v["subtipo"])}{" ★" if v["es_default"] else ""})</option>'
            for v in variantes
        )
        filas.append(f"""
        <tr data-idx="{item["numero"]}">
          <td>{item["numero"]}</td>
          <td>{html_module.escape(item["tipo"])}</td>
          <td>
            <input type="hidden" name="tipos" value="{html_module.escape(item["tipo"])}">
            <input type="hidden" name="nums" value="{item["numero"]}">
            <select name="subtipos">{opts}</select>
          </td>
          <td>{html_module.escape(item["titulo"])}</td>
          <td><input type="checkbox" name="activos" value="{item["numero"]}" {"checked" if item["activo"] else ""}></td>
        </tr>
        """)

    estado = pres.get("estado") or "borrador"
    estado_label = {"borrador": "🟡 Borrador", "generado": "🟢 Generado", "publicado": "🟣 Publicado"}.get(estado, f"⚪ {estado}")
    gen_label = "🔄 Regenerar y publicar" if estado in ("generado", "publicado") else "⚡ Generar y publicar"
    content = f"""<h2>Armar presentación {fecha}</h2>
    <p><strong>{html_module.escape(pres.get("celebracion") or "")}</strong> | Color: {html_module.escape(pres.get("color_liturgico") or "-")} | <span style="font-weight:600;">{estado_label}</span></p>
    <p><a href="/presentaciones_html/{fecha}_presentacion/index.html" target="_blank">🔍 Previsualizar presentación</a> |
    <a href="/presentacion/{fecha}/preview" target="_blank">📋 Storyboard</a> |
    <a href="/presentacion/{fecha}/generar">{gen_label} PPTX/HTML/PDF</a> |
    <a href="/presentacion/{fecha}/reconstruir" style="color:#b91c1c;font-weight:600;">🔄 Reconstruir desde canciones asignadas</a></p>
    <form method="post" action="/presentacion/{fecha}/guardar">
      <table style="width:100%;border-collapse:collapse;margin-bottom:15px">
        <thead>
          <tr style="text-align:left;border-bottom:2px solid #ddd"><th>Nº</th><th>Tipo</th><th>Variante</th><th>Título</th><th>Activo</th></tr>
        </thead>
        <tbody>{"\n".join(filas)}</tbody>
      </table>
      <button type="submit">💾 Guardar composición y commitear</button>
    </form>
    <p><small>Consejo: para añadir o quitar diapositivas de paso, edita la secuencia desde el catálogo.</small></p>"""
    return _render_base(f"Armar {fecha}", sidebar, content)


@app.route("/presentacion/<fecha>/guardar", methods=["POST"])
def guardar_presentacion(fecha: str):
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", fecha):
        abort(400)
    pres = _get_presentacion_por_fecha(fecha)
    if not pres:
        abort(404)

    tipos = request.form.getlist("tipos")
    nums = request.form.getlist("nums")
    subtipos = request.form.getlist("subtipos")
    activos_raw = set(int(x) for x in request.form.getlist("activos"))

    # Construir items en orden recibido
    items: List[Dict[str, Any]] = []
    for i, tipo in enumerate(tipos):
        numero = int(nums[i]) if i < len(nums) else i + 1
        subtipo = subtipos[i] if i < len(subtipos) else "general"
        activo = 1 if numero in activos_raw else 0
        slide = _slide_para_momento(tipo, subtipo)
        items.append({
            "numero": i + 1,
            "tipo": tipo,
            "subtipo": subtipo,
            "titulo": slide["titulo"] if slide else f"[FALTA: {tipo}]",
            "slide_id": slide["id"] if slide else None,
            "activo": activo,
        })

    conn = _get_connection()
    cursor = conn.cursor()
    # Borrar composición anterior
    cursor.execute("DELETE FROM presentacion_slides WHERE presentacion_id = ?", (pres["id"],))
    # Insertar nueva
    for item in items:
        cursor.execute("""
            INSERT INTO presentacion_slides (presentacion_id, slide_id, numero, tipo, subtipo, titulo, contenido, cita, subtitulo, imagen, momento, activo)
            SELECT ?, s.id, ?, ?, ?, s.titulo, s.contenido, s.cita, s.subtitulo, s.imagen, '', ?
            FROM slides s
            WHERE s.id = ?
        """, (pres["id"], item["numero"], item["tipo"], item["subtipo"], item["activo"], item["slide_id"]))
        if cursor.rowcount == 0:
            # Slide no encontrada: insertar item sin slide_id
            cursor.execute("""
                INSERT INTO presentacion_slides (presentacion_id, slide_id, numero, tipo, subtipo, titulo, contenido, activo)
                VALUES (?, NULL, ?, ?, ?, ?, '', ?)
            """, (pres["id"], item["numero"], item["tipo"], item["subtipo"], item["titulo"], item["activo"]))
    conn.commit()
    conn.close()

    commit_result = _git_commit(f"composición presentación {fecha}")
    mensaje_comp = f"Composición guardada y commiteada ({commit_result})." if not commit_result.startswith("ERROR") else f"Composición guardada, falló git: {commit_result}"

    # Regenerar automáticamente la presentación para actualizar previsualización
    # _generar_presentacion ya hace commit+push del bundle, no es necesario otro commit
    gen_msg = _generar_presentacion(fecha)

    mensaje = f"✅ {mensaje_comp} {gen_msg}"
    clase = "ok" if not commit_result.startswith("ERROR") and "✅" in gen_msg else "err"

    response = armar_presentacion(fecha)
    if isinstance(response, tuple):
        body, status = response
    else:
        body, status = response, 200
    body = body.replace("<main>", f'<main>\n<div class="msg {clase}">{html_module.escape(mensaje)}</div>')
    return body, status


@app.route("/presentacion/<fecha>/reconstruir")
def reconstruir_presentacion(fecha: str):
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", fecha):
        abort(400)
    if not _get_presentacion_por_fecha(fecha):
        abort(404)
    msg = _reconstruir_composicion_desde_canciones(fecha)
    commit_result = _git_commit(f"reconstruir composicion {fecha}")
    if commit_result.startswith("ERROR"):
        msg += f" (git falló: {commit_result})"
    gen_msg = _generar_presentacion(fecha)
    commit_result2 = _git_commit(f"generar presentacion {fecha}")
    if commit_result2.startswith("ERROR"):
        gen_msg += f" (git falló: {commit_result2})"
    clase = "ok" if "✅" in gen_msg else "err"
    mensaje = f"{msg} | {gen_msg}"
    response = armar_presentacion(fecha)
    if isinstance(response, tuple):
        body, status = response
    else:
        body, status = response, 200
    body = body.replace("<main>", f'<main>\n<div class="msg {clase}">{html_module.escape(mensaje)}</div>')
    return body, status


@app.route("/presentacion/<fecha>/generar")
def generar_presentacion(fecha: str):
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", fecha):
        abort(400)
    if not _get_presentacion_por_fecha(fecha):
        abort(404)
    gen_msg = _generar_presentacion(fecha)
    commit_result = _git_commit(f"generar presentación {fecha}")
    if commit_result.startswith("ERROR"):
        gen_msg += f" (git falló: {commit_result})"
    clase = "ok" if "✅" in gen_msg else "err"
    msg_html = f'<div class="msg {clase}">{html_module.escape(gen_msg)} | {html_module.escape(commit_result)}</div>'
    response = armar_presentacion(fecha)
    if isinstance(response, tuple):
        body, status = response
    else:
        body, status = response, 200
    body = body.replace("<main>", f'<main>\n{msg_html}')
    return body, status


@app.route("/presentaciones_html/<path:subpath>")
def servir_presentacion_html(subpath: str):
    """Sirve archivos estáticos generados (HTML, PDF, PPTX, imágenes, etc.)."""
    from flask import send_from_directory
    base = PROJECT_DIR / "presentaciones_html"
    file_path = base / subpath
    if not file_path.resolve().is_relative_to(base.resolve()):
        abort(403)
    if not file_path.exists():
        abort(404)
    if file_path.is_dir():
        # Si es directorio sin index.html, servir index.html
        idx = file_path / "index.html"
        if idx.exists():
            return send_from_directory(str(file_path), "index.html")
        abort(404)
    return send_from_directory(str(file_path.parent), file_path.name)


@app.route("/presentacion/<fecha>/preview")
def preview_presentacion(fecha: str):
    if not re.match(r"^\d{4}-\d{2}-\d{2}$", fecha):
        abort(400)
    pres = _get_presentacion_por_fecha(fecha)
    if not pres:
        abort(404)
    color = pres.get("color_liturgico") or "verde"

    items = _get_composicion_guardada(fecha)
    if not items:
        items = _proponer_composicion(fecha)

    previews = []
    numero_real = 1
    for item in items:
        if not item.get("activo"):
            continue
        subtitulo = item.get("subtitulo") or ""
        if item["tipo"] == "portada":
            subtitulo = _formatear_fecha_preview(fecha)
        slide_data = {
            "tipo": item["tipo"],
            "subtipo": item["subtipo"],
            "titulo": item.get("titulo") or "",
            "contenido": item.get("contenido") or item.get("slide_contenido") or "",
            "cita": item.get("cita") or "",
            "subtitulo": subtitulo,
            "momento": item.get("momento") or "",
            "imagen": item.get("imagen") or item.get("slide_imagen") or "",
            "color_liturgico": color,
        }
        # Expandir divisiones
        partes = re.split(r"(?m)^\s*---\s*DIAPOSITIVA\s*---\s*$", slide_data["contenido"])
        partes = [p.strip() for p in partes if p.strip()] or [""]
        for idx, parte in enumerate(partes):
            sd = dict(slide_data)
            sd["contenido"] = parte
            if len(partes) > 1:
                sd["titulo"] = f"{sd['titulo']} ({idx + 1}/{len(partes)})"
            previews.append(f'<div style="color:#aaa;font-size:12px;margin:8px 0 4px">Slide {numero_real}</div>{_render_preview(sd)}')
            numero_real += 1

    html = f"""<!DOCTYPE html>
<html lang="es"><head><meta charset="UTF-8"><title>Preview {fecha}</title>
    <style>
      body {{ background:#111; color:#fff; font-family:system-ui; padding:20px; }}
      .preview {{ display:flex; flex-direction:column; align-items:center; gap:10px; }}
      .preview-frame {{ width:640px; height:480px; }}
    </style>
    </head><body>
    <h1>Preview {fecha}</h1>
    <p>{html_module.escape(pres.get("celebracion") or "")} | Color: {html_module.escape(color)}</p>
    <div class="preview">{"\n".join(previews)}</div>
    </body></html>"""
    return html






# ------------------------------------------------------------------
# Edición de momentos litúrgicos de canciones
# ------------------------------------------------------------------

@app.route("/cancion/<int:cancion_id>/momentos")
def editar_momentos_cancion(cancion_id: int):
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, titulo FROM canciones WHERE id = ?", (cancion_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        abort(404)

    momentos_actuales = _get_momentos_cancion(cancion_id)
    checkboxes = "\n".join(
        f'<label style="display:inline-block;margin-right:12px;margin-bottom:6px;"><input type="checkbox" name="momentos" value="{html_module.escape(m)}" {"checked" if m in momentos_actuales else ""}> {html_module.escape(m.replace("_", " ").title())}</label>'
        for m in MOMENTOS_LITURGICOS
    )

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
        sidebar_parts.append(f'<details><summary>{html_module.escape(t["nombre"])} ({len(slides)})</summary>{links}</details>')
    sidebar = "\n".join(sidebar_parts)

    content = f"""<h2>Momentos litúrgicos: {html_module.escape(row["titulo"])}</h2>
    <p>Momentos actuales: <strong>{html_module.escape(", ".join(momentos_actuales).title() or "(ninguno)")}</strong></p>
    <form method="post" action="/cancion/{cancion_id}/momentos/guardar">
      <div style="margin-bottom:15px;">
        {checkboxes}
      </div>
      <button type="submit">💾 Guardar momentos</button>
    </form>
    <p><a href="/">← Volver al listado de slides</a></p>
    """
    return _render_base(f"Momentos - {row['titulo']}", sidebar, content)


@app.route("/cancion/<int:cancion_id>/momentos/guardar", methods=["POST"])
def guardar_momentos_cancion(cancion_id: int):
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, titulo FROM canciones WHERE id = ?", (cancion_id,))
    row = cursor.fetchone()
    conn.close()
    if not row:
        abort(404)

    nuevos_momentos = request.form.getlist("momentos")
    _set_momentos_cancion(cancion_id, nuevos_momentos)

    # Actualizar campo legacy
    momento_legacy = nuevos_momentos[0] if nuevos_momentos else ""
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute("UPDATE canciones SET momento_liturgico = ? WHERE id = ?", (momento_legacy, cancion_id))
    conn.commit()
    conn.close()

    commit_result = _git_commit(f"momentos litúrgicos {row['titulo']}")
    clase = "ok" if not commit_result.startswith("ERROR") else "err"
    mensaje = f"Momentos guardados y commiteados ({commit_result})." if not commit_result.startswith("ERROR") else f"Guardado, falló git: {commit_result}"

    response = editar_momentos_cancion(cancion_id)
    if isinstance(response, tuple):
        body, status = response
    else:
        body, status = response, 200
    body = body.replace("<main>", f'<main>\n<div class="msg {clase}">{html_module.escape(mensaje)}</div>')
    return body, status

def main():
    host = os.environ.get("EDITOR_HOST", "0.0.0.0")
    port = int(os.environ.get("EDITOR_PORT", "4323"))
    app.run(host=host, port=port, debug=False)


if __name__ == "__main__":
    main()
