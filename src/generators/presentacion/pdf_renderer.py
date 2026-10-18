"""Renderizado de presentaciones a PDF vía Playwright."""

from pathlib import Path


def _render_pdf(html_path: Path, pdf_path: Path):
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch()
            page = browser.new_page(viewport={"width": 1024, "height": 768})
            page.goto(f"file://{html_path}")
            page.wait_for_timeout(1000)
            page.pdf(path=str(pdf_path), width="10in", height="7.5in", print_background=True)
            browser.close()
    except Exception as exc:
        print(f"PDF no generado automáticamente: {exc}")
