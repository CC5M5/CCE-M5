"""Renderizado de presentaciones a PDF.

Por defecto usa WeasyPrint (puro Python, sin navegador). Si `WEASYPRINT_DISABLE`
 está en el entorno, intenta Playwright como fallback. El fallback es opcional
y requiere que playwright esté instalado.
"""

from __future__ import annotations

import os
from pathlib import Path


def _render_pdf_weasyprint(html_path: Path, pdf_path: Path) -> None:
    from weasyprint import HTML

    HTML(filename=str(html_path)).write_pdf(str(pdf_path))


def _render_pdf_playwright(html_path: Path, pdf_path: Path) -> None:
    from playwright.sync_api import sync_playwright

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": 1024, "height": 768})
        page.goto(f"file://{html_path}")
        page.wait_for_timeout(1000)
        page.pdf(path=str(pdf_path), width="10in", height="7.5in", print_background=True)
        browser.close()


def _render_pdf(html_path: Path, pdf_path: Path) -> None:
    try:
        if os.environ.get("WEASYPRINT_DISABLE"):
            raise RuntimeError("WeasyPrint deshabilitado por entorno")
        _render_pdf_weasyprint(html_path, pdf_path)
    except Exception as exc:
        # Fallback a Playwright solo si está disponible.
        try:
            _render_pdf_playwright(html_path, pdf_path)
        except Exception as fallback_exc:
            print(f"PDF no generado automáticamente: {exc} / fallback: {fallback_exc}")
