"""
Generador de presentaciones litúrgicas desde la composición guardada en presentacion_slides.

Reutiliza los métodos de renderizado de presentacion_html.py para producir
JSON + HTML + PPTX + PDF idénticos en contenido.
"""

import json
import os
import shutil
import sqlite3
import sys
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

PROJECT_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_DIR / "data"
DB_PATH = DATA_DIR / "db.sqlite3"
LEMA_DIR = DATA_DIR / "lemas"
ILUSTRACIONES_DIR = DATA_DIR / "ilustraciones"
OUTPUT_DIR = PROJECT_DIR / "presentaciones_html"

sys.path.insert(0, str(PROJECT_DIR / "src" / "generators"))
from presentacion_html import GeneradorPresentacionHTML, Slide  # noqa: E402


def _get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def _convertir_svg_a_png(src: Path, dst_dir: Path) -> Optional[Path]:
    """Convierte un SVG a PNG usando inkscape si está disponible."""
    import subprocess
    if not shutil.which("inkscape"):
        return None
    dst = dst_dir / f"{src.stem}.png"
    try:
        subprocess.run(
            ["inkscape", str(src), "--export-filename", str(dst), "--export-dpi", "150"],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return dst
    except Exception:
        return None


class GeneradorDesdeComposicion(GeneradorPresentacionHTML):
    """Genera presentación a partir de la composición guardada en presentacion_slides."""

    def generar_desde_presentacion(self, fecha: str) -> Path:
        conn = _get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT p.*, l.celebracion, l.color_liturgico
            FROM presentaciones p
            LEFT JOIN lecturas l ON l.id = p.lectura_id
            WHERE p.fecha_domingo = ?
        """, (fecha,))
        pres = cursor.fetchone()
        if not pres:
            raise ValueError(f"No existe presentación para {fecha}")
        pres = dict(pres)

        cursor.execute("""
            SELECT ps.*, s.contenido AS slide_contenido, s.imagen AS slide_imagen
            FROM presentacion_slides ps
            LEFT JOIN slides s ON s.id = ps.slide_id
            WHERE ps.presentacion_id = ? AND ps.activo = 1
            ORDER BY ps.numero
        """, (pres["id"],))
        items = [dict(r) for r in cursor.fetchall()]
        conn.close()

        if not items:
            raise ValueError(f"La presentación {fecha} no tiene composición guardada")

        color = (pres.get("color_liturgico") or "verde").lower()
        color_info = self._color_info(color)
        celebracion = pres.get("celebracion") or self._celebracion_from_fecha(fecha)

        fecha_formateada = self._formatear_fecha(fecha)
        slides: List[Slide] = []
        primera_portada = True
        for item in items:
            contenido = item.get("contenido") or item.get("slide_contenido") or ""
            imagen = item.get("imagen") or item.get("slide_imagen") or ""
            tipo = item["tipo"]
            titulo = item.get("titulo") or ""
            cita = item.get("cita") or ""
            subtitulo = item.get("subtitulo") or ""
            momento = item.get("momento") or ""

            # Inyectar título y fecha reales en portadas
            if tipo == "portada":
                if primera_portada:
                    titulo = celebracion
                    subtitulo = fecha_formateada
                    primera_portada = False
                else:
                    subtitulo = f"Somos uno · {fecha_formateada}" if subtitulo.lower().startswith("somos uno") else subtitulo

            # Expandir diapositivas de paso sin contenido
            if tipo == "paso":
                slides.append(
                    Slide(
                        numero=len(slides) + 1,
                        tipo=tipo,
                        titulo="",
                        contenido="",
                        cita="",
                        subtitulo="",
                        momento="",
                        imagen=imagen or self._ilustracion_para(tipo),
                    )
                )
                continue

            # Expandir --- DIAPOSITIVA ---
            partes = self._split_contenido(contenido)
            for idx, parte in enumerate(partes):
                sufijo = f" ({idx + 1}/{len(partes)})" if len(partes) > 1 else ""
                slides.append(
                    Slide(
                        numero=len(slides) + 1,
                        tipo=tipo,
                        titulo=f"{titulo}{sufijo}",
                        contenido=parte,
                        cita=cita,
                        subtitulo=subtitulo,
                        momento=momento,
                        imagen=imagen or self._ilustracion_para(tipo),
                    )
                )

        # Renumerar
        for i, s in enumerate(slides, 1):
            s.numero = i

        data: Dict[str, Any] = {
            "meta": {
                "fecha": fecha,
                "celebracion": celebracion,
                "color_liturgico": color,
                "lema": "Somos uno",
                "lema_imagen": "assets/lema_somos_uno.jpg",
                "generado": datetime.now().isoformat(),
            },
            "slides": [asdict(s) for s in slides],
        }

        base_name = f"{fecha}_presentacion"
        bundle_dir = OUTPUT_DIR / base_name
        bundle_dir.mkdir(parents=True, exist_ok=True)

        # Copiar lema e ilustraciones (convertir SVG a PNG para PPTX)
        assets_dir = bundle_dir / "assets"
        assets_dir.mkdir(parents=True, exist_ok=True)
        lema_src = LEMA_DIR / "somos_uno.jpg"
        if lema_src.exists():
            shutil.copy(lema_src, assets_dir / "lema_somos_uno.jpg")

        svg_convertidos: Dict[str, str] = {}
        for slide in slides:
            if not slide.imagen:
                continue
            img_name = Path(slide.imagen).name
            src_candidates = list(ILUSTRACIONES_DIR.rglob(img_name))
            if not src_candidates:
                stem = Path(img_name).stem
                for ext in (".jpg", ".jpeg", ".png", ".svg", ".webp"):
                    src_candidates.extend(ILUSTRACIONES_DIR.rglob(f"{stem}{ext}"))
            for src in src_candidates:
                if not src.exists():
                    continue
                if src.suffix.lower() == ".svg":
                    png = _convertir_svg_a_png(src, assets_dir)
                    if png:
                        svg_convertidos[slide.imagen] = f"assets/{png.name}"
                    break
                shutil.copy(src, assets_dir / src.name)
                break

        # Reemplazar rutas SVG por PNG convertido donde aplique
        for slide in slides:
            if slide.imagen in svg_convertidos:
                slide.imagen = svg_convertidos[slide.imagen]

        json_path = bundle_dir / f"{base_name}.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        html_path = bundle_dir / "index.html"
        html = self._render_html(data, color_info)
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html)

        pptx_path = bundle_dir / f"{base_name}.pptx"
        self._render_pptx(data, pptx_path, assets_dir)


        pdf_path = bundle_dir / f"{base_name}.pdf"
        self._render_pdf(html_path, pdf_path)

        # Actualizar BD con rutas
        conn = _get_connection()
        cursor = conn.cursor()
        ruta_base = str(bundle_dir.relative_to(PROJECT_DIR))
        cursor.execute("""
            UPDATE presentaciones
            SET estado = 'generado',
                ruta_web = ?,
                ruta_pptx = ?,
                ruta_pdf_fieles = ?
            WHERE id = ?
        """, (
            f"{ruta_base}/index.html",
            f"{ruta_base}/{base_name}.pptx",
            f"{ruta_base}/{base_name}.pdf",
            pres["id"],
        ))
        conn.commit()
        conn.close()

        return bundle_dir

    def _color_info(self, color: str) -> Dict[str, str]:
        from presentacion_html import COLORES_LITURGICOS
        return COLORES_LITURGICOS.get(color, COLORES_LITURGICOS["verde"])

    def _split_contenido(self, contenido: str) -> List[str]:
        import re
        partes = re.split(r"(?m)^\s*---\s*DIAPOSITIVA\s*---\s*$", contenido)
        partes = [p.strip() for p in partes if p.strip()]
        return partes or [""]


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Generar presentación desde composición guardada")
    parser.add_argument("--fecha", required=True, help="YYYY-MM-DD del domingo")
    args = parser.parse_args()
    gen = GeneradorDesdeComposicion()
    bundle = gen.generar_desde_presentacion(args.fecha)
    print(f"Generado: {bundle}")


if __name__ == "__main__":
    main()
