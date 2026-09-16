#!/usr/bin/env python3
"""
Editor local de acordes con commit automático.

Uso:
  python scripts/editor_acordes_server.py

Abre http://localhost:4322 en el navegador.

Funcionalidades:
- Listado de canciones del cancionero.
- Editor de texto con acordes posicionados.
- Preview visual de la canción con acordes.
- Al guardar: actualiza SQLite, regenera html_visual/estructura_json,
  y hace git commit automático.
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

from flask import Flask, abort, request

PROJECT_DIR = Path(__file__).resolve().parents[1]
DB_PATH = PROJECT_DIR / "data" / "db.sqlite3"

app = Flask(__name__)


def _get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def _regenerar_derivados(texto_con_acordes: str) -> dict:
    """Regenera html_visual, estructura_json, letra_sin_acordes y tono."""
    sys.path.insert(0, str(PROJECT_DIR / "src"))
    from parsers.acordes_parser_v3 import AcordesParser

    parser = AcordesParser()
    estructura = parser.parsear_cancion_completa(texto_con_acordes)
    html_visual = parser.generar_html_visual(estructura)
    tono = parser.detectar_tono(estructura)

    letra_limpia_lines = []
    for linea in estructura:
        if linea.tipo in ("letra", "acordes_letra"):
            letra_limpia_lines.append(linea.letra)
    letra_sin_acordes = "\n".join(letra_limpia_lines)

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

    return {
        "letra_sin_acordes": letra_sin_acordes,
        "acordes_json": "",
        "estructura_json": estructura_json,
        "html_visual": html_visual,
        "tono": tono,
    }


def _git_commit(titulo: str) -> str:
    """Hace git add + commit + push. Devuelve el hash o un mensaje de error."""
    try:
        subprocess.run(
            ["git", "add", "data/db.sqlite3"],
            cwd=PROJECT_DIR,
            check=True,
            capture_output=True,
            text=True,
        )
        result = subprocess.run(
            ["git", "commit", "-m", f"chore(acordes): editar {titulo}",
             "-m", "Actualización manual desde editor local de acordes."],
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


def _rebuild_web() -> str:
    """Reconstruye la web Astro y reinicia el servidor web principal."""
    try:
        env = os.environ.copy()
        env["BASE_PATH"] = "/"
        env["SITE_URL"] = "http://192.168.68.244:4321"
        env["PATH"] = f"/home/pciath/.nvm/versions/node/v24.18.0/bin:{env.get('PATH', '')}"

        # Build Astro
        build_result = subprocess.run(
            ["/home/pciath/.nvm/versions/node/v24.18.0/bin/npm", "run", "build"],
            cwd=PROJECT_DIR / "web",
            check=True,
            capture_output=True,
            text=True,
            env=env,
        )

        # Reiniciar servidor web principal (mata proceso http.server en 4321)
        subprocess.run(
            "ps aux | grep 'http.server 4321' | grep -v grep | awk '{print $2}' | xargs -r kill 2>/dev/null",
            shell=True,
            check=False,
            capture_output=True,
        )
        time.sleep(1)

        # Iniciar nuevo servidor
        subprocess.Popen(
            ["/usr/bin/python3", "-m", "http.server", "4321",
             "--directory", str(PROJECT_DIR / "web" / "dist"),
             "--bind", "0.0.0.0"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )

        return "rebuild OK"
    except subprocess.CalledProcessError as exc:
        return f"ERROR rebuild: {exc.stderr or exc.stdout}"
    except Exception as exc:
        return f"ERROR rebuild: {exc}"



def _slugify(titulo: str) -> str:
    import unicodedata
    t = unicodedata.normalize("NFD", titulo.lower())
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    t = re.sub(r"[^a-z0-9]+", "-", t).strip("-")
    return t


def _get_canciones():
    conn = _get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, titulo FROM canciones ORDER BY titulo")
    canciones = [{"id": r["id"], "titulo": r["titulo"], "slug": _slugify(r["titulo"])} for r in cursor.fetchall()]
    conn.close()
    return canciones


def _get_cancion_by_slug(slug: str):
    canciones = _get_canciones()
    for c in canciones:
        if c["slug"] == slug:
            conn = _get_connection()
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id, titulo, titulo_url, letra_con_acordes, html_visual, tono FROM canciones WHERE id = ?",
                (c["id"],),
            )
            row = cursor.fetchone()
            conn.close()
            if row:
                return {
                    "id": row["id"],
                    "titulo": row["titulo"],
                    "titulo_url": row["titulo_url"],
                    "slug": slug,
                    "texto": row["letra_con_acordes"] or "",
                    "preview": row["html_visual"] or "",
                    "tono": row["tono"],
                }
    return None


def _render_base(title: str, sidebar: str, content: str, mensaje: str = "", mensaje_clase: str = "") -> str:
    msg_html = f'<div class="msg {mensaje_clase}">{html_module.escape(mensaje)}</div>' if mensaje else ""
    return f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{html_module.escape(title)} - Editor Acordes CCE-M5</title>
  <style>
    :root {{ --accent: #7C3AED; --bg: #f8f9fa; --card: #fff; }}
    body {{ font-family: system-ui, sans-serif; background: var(--bg); margin: 0; padding: 20px; }}
    header {{ max-width: 1400px; margin: 0 auto 20px; }}
    h1 {{ color: var(--accent); margin: 0 0 10px; }}
    .container {{ max-width: 1400px; margin: 0 auto; display: grid; grid-template-columns: 300px 1fr; gap: 20px; }}
    aside {{ background: var(--card); border-radius: 12px; padding: 15px; box-shadow: 0 2px 8px rgba(0,0,0,0.05); max-height: 85vh; overflow: auto; }}
    aside a {{ display: block; padding: 6px 8px; color: #333; text-decoration: none; border-radius: 6px; font-size: 14px; }}
    aside a:hover {{ background: #f0f0f0; }}
    aside a.active {{ background: var(--accent); color: #fff; }}
    main {{ background: var(--card); border-radius: 12px; padding: 20px; box-shadow: 0 2px 8px rgba(0,0,0,0.05); }}
    textarea {{ width: 100%; min-height: 450px; font-family: ui-monospace, "SF Mono", "Cascadia Mono", "Segoe UI Mono", "Roboto Mono", Menlo, Consolas, "Courier New", monospace; font-size: 16px; line-height: 1.35; padding: 12px; border: 1px solid #ddd; border-radius: 8px; box-sizing: border-box; white-space: pre; overflow-wrap: normal; overflow-x: auto; }}
    button {{ background: var(--accent); color: #fff; border: none; padding: 12px 24px; border-radius: 8px; font-size: 16px; cursor: pointer; margin-top: 10px; }}
    button:hover {{ opacity: 0.9; }}
    .preview {{ padding: 15px; background: #fafafa; border-radius: 8px; border: 1px solid #eee; white-space: pre; }}
    .msg {{ padding: 12px; border-radius: 8px; margin-bottom: 15px; }}
    .msg.ok {{ background: #d1fae5; color: #065f46; }}
    .msg.err {{ background: #fee2e2; color: #991b1b; }}
    .meta {{ color: #666; font-size: 14px; margin-bottom: 15px; }}
    .two-col {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }}
    .cancion-con-acordes {{ font-family: ui-monospace, "SF Mono", "Cascadia Mono", "Segoe UI Mono", "Roboto Mono", Menlo, Consolas, "Courier New", monospace; line-height: 0.3; white-space: pre; }}
    .bloque-acordes-letra {{ margin-bottom: 0; }}
    .linea-acordes {{ color: #c0392b; font-weight: bold; height: 0.6em; }}
    .linea-letra {{ color: #2c3e50; }}
    .seccion {{ font-weight: bold; margin-top: 0.6em; color: #2980b9; }}
    .linea-acordes-suelta {{ color: #c0392b; font-weight: bold; }}
    .letra-solo {{ color: #2c3e50; }}
    .linea-vacia {{ height: 0.4em; }}
    @media (max-width: 900px) {{
      .container {{ grid-template-columns: 1fr; }}
      .two-col {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>
  <header>
    <h1>🎵 Editor de Acordes CCE-M5</h1>
    <p>Edición local con commit automático. URL de origen se mantiene como referencia.</p>
  </header>
  <div class="container">
    <aside>
      <p><strong>Canciones</strong></p>
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
    canciones = _get_canciones()
    sidebar_links = "\n".join(
        f'<a href="/cancionero/{html_module.escape(c["slug"])}">{html_module.escape(c["titulo"])}</a>'
        for c in canciones
    )
    content = "<h2>Selecciona una canción</h2><p>Elige una canción del menú lateral para editar sus acordes.</p>"
    return _render_base("Canciones", sidebar_links, content)


@app.route("/cancionero/<slug>")
def editar(slug: str):
    cancion = _get_cancion_by_slug(slug)
    if cancion is None:
        abort(404)

    canciones = _get_canciones()
    sidebar_links = "\n".join(
        f'<a href="/cancionero/{html_module.escape(c["slug"])}" class="active"' if c["slug"] == slug else f'<a href="/cancionero/{html_module.escape(c["slug"])}"'
        for c in canciones
    )
    sidebar_links = "\n".join(
        f'{link}>{html_module.escape(c["titulo"])}</a>'
        for c, link in zip(canciones, sidebar_links.split("\n"))
    )

    content = f"""<h2>{html_module.escape(cancion['titulo'])}</h2>
    <div class="meta">
      Tono: {html_module.escape(cancion['tono'] or 'No detectado')} |
      ID: {cancion['id']} |
      <a href="{html_module.escape(cancion['titulo_url'] or '')}" target="_blank">Ver origen ↗</a>
    </div>
    <div class="nota-editor" style="background:#fffbeb; border:1px solid #f59e0b; border-radius:8px; padding:10px; margin-bottom:15px; color:#92400e; font-size:14px;">
      <strong>ℹ️ Importante:</strong> El cancionero web usa fuente monoespaciada (Courier New).
      Coloca cada acorde encima de la sílaba/letra correspondiente usando espacios.
      <strong>El preview usa exactamente la misma fuente y espaciado que este editor.</strong>
      Si no coincide al guardar, pulsa Ctrl+F5 en la web.
      <br><strong>Negrita:</strong> usa <code>**texto en negrita**</code>. El estribillo se detecta automáticamente si pasa de minúsculas a MAYÚSCULAS.
    </div>
    <form method="post" action="/cancionero/{html_module.escape(slug)}/guardar">
      <div class="two-col">
        <div>
          <label><strong>Texto con acordes</strong></label>
          <textarea name="texto">{html_module.escape(cancion['texto'])}</textarea>
        </div>
        <div class="preview">
          <strong>Preview actual</strong>
          {cancion['preview']}
        </div>
      </div>
      <button type="submit">💾 Guardar y commitear</button>
    </form>"""
    return _render_base(cancion["titulo"], sidebar_links, content)


@app.route("/cancionero/<slug>/guardar", methods=["POST"])
def guardar(slug: str):
    cancion = _get_cancion_by_slug(slug)
    if cancion is None:
        abort(404)

    nuevo_texto = request.form.get("texto", "")
    derivados = _regenerar_derivados(nuevo_texto)

    conn = _get_connection()
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
        (
            nuevo_texto,
            derivados["letra_sin_acordes"],
            derivados["acordes_json"],
            derivados["estructura_json"],
            derivados["html_visual"],
            derivados["tono"],
            cancion["id"],
        ),
    )
    conn.commit()
    conn.close()

    commit_result = _git_commit(cancion["titulo"])
    rebuild_result = _rebuild_web()

    if commit_result.startswith("ERROR"):
        mensaje = f"Guardado en BD, pero falló git: {commit_result}"
        clase = "err"
    elif rebuild_result.startswith("ERROR"):
        mensaje = f"✅ Guardado y commiteado: {commit_result}. ⚠️ Pero falló rebuild web: {rebuild_result}"
        clase = "err"
    else:
        mensaje = f"✅ Guardado, commiteado ({commit_result}) y web reconstruida."
        clase = "ok"

    canciones = _get_canciones()
    sidebar_links = "\n".join(
        f'<a href="/cancionero/{html_module.escape(c["slug"])}" class="active"' if c["slug"] == slug else f'<a href="/cancionero/{html_module.escape(c["slug"])}"'
        for c in canciones
    )
    sidebar_links = "\n".join(
        f'{link}>{html_module.escape(c["titulo"])}</a>'
        for c, link in zip(canciones, sidebar_links.split("\n"))
    )

    content = f"""<h2>{html_module.escape(cancion['titulo'])}</h2>
    <div class="meta">
      Tono: {html_module.escape(derivados['tono'] or 'No detectado')} |
      ID: {cancion['id']} |
      <a href="{html_module.escape(cancion['titulo_url'] or '')}" target="_blank">Ver origen ↗</a>
    </div>
    <div class="nota-editor" style="background:#fffbeb; border:1px solid #f59e0b; border-radius:8px; padding:10px; margin-bottom:15px; color:#92400e; font-size:14px;">
      <strong>ℹ️ Importante:</strong> El cancionero web usa fuente monoespaciada (Courier New).
      Coloca cada acorde encima de la sílaba/letra correspondiente usando espacios.
      <strong>El preview usa exactamente la misma fuente y espaciado que este editor.</strong>
      Si no coincide al guardar, pulsa Ctrl+F5 en la web.
      <br><strong>Negrita:</strong> usa <code>**texto en negrita**</code>. El estribillo se detecta automáticamente si pasa de minúsculas a MAYÚSCULAS.
    </div>
    <form method="post" action="/cancionero/{html_module.escape(slug)}/guardar">
      <div class="two-col">
        <div>
          <label><strong>Texto con acordes</strong></label>
          <textarea name="texto">{html_module.escape(nuevo_texto)}</textarea>
        </div>
        <div class="preview">
          <strong>Preview actualizado</strong>
          {derivados['html_visual']}
        </div>
      </div>
      <button type="submit">💾 Guardar y commitear</button>
    </form>"""
    return _render_base(cancion["titulo"], sidebar_links, content, mensaje, clase)


def main():
    host = os.environ.get("EDITOR_HOST", "0.0.0.0")
    port = int(os.environ.get("EDITOR_PORT", "4322"))
    app.run(host=host, port=port, debug=False)


if __name__ == "__main__":
    main()
