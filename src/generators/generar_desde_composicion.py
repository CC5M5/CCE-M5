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
            SELECT p.*, l.celebracion, l.color_liturgico,
                   l.primera_lectura_libro, l.primera_lectura_cita, l.primera_lectura_texto,
                   l.salmo_libro, l.salmo_cita, l.salmo_antifona, l.salmo_texto,
                   l.segunda_lectura_libro, l.segunda_lectura_cita, l.segunda_lectura_texto,
                   l.evangelio_libro, l.evangelio_cita, l.evangelio_texto
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

        def _cita_con_libro(libro: str, cita: str) -> str:
            libro = (libro or "").strip()
            cita = (cita or "").strip()
            if not libro:
                return cita
            if not cita:
                return libro
            # Mapa de libros a abreviaturas comunes en citas litúrgicas
            abreviaturas = {
                "génesis": ["gn"],
                "éxodo": ["ex"],
                "levítico": ["lv"],
                "números": ["nm"],
                "deuteronomio": ["dt"],
                "josúe": ["jos"],
                "jueces": ["jue"],
                "rut": ["rut"],
                "1 samuel": ["1 s"],
                "2 samuel": ["2 s"],
                "1 reyes": ["1 r"],
                "2 reyes": ["2 r"],
                "1 crónicas": ["1 cr"],
                "2 crónicas": ["2 cr"],
                "esdras": ["esd"],
                "nehemías": ["neh"],
                "tobías": ["tb"],
                "judit": ["jdt"],
                "ester": ["est"],
                "job": ["job"],
                "salmo": ["sal"],
                "salmos": ["sal"],
                "proverbios": ["prv"],
                "eclesiastés": ["eccl"],
                "cantar de los cantares": ["cant"],
                "sabiduría": ["sab"],
                "sirácida": ["sir", "eclesiástico"],
                "isaías": ["is"],
                "jeremías": ["jer"],
                "lamentaciones": ["lam"],
                "baruc": ["bar"],
                "ezequiel": ["ez"],
                "daniel": ["dn"],
                "oseas": ["os"],
                "joel": ["jl"],
                "amos": ["am"],
                "abdías": ["abd"],
                "jonás": ["jon"],
                "miqueas": ["miq"],
                "nahúm": ["nah"],
                "habacuc": ["hab"],
                "sofonías": ["sof"],
                "ageo": ["ag"],
                "zacarías": ["zac"],
                "malaquías": ["mal"],
                "1 macabeos": ["1 mc"],
                "2 macabeos": ["2 mc"],
                "mateo": ["mt"],
                "marcos": ["mc"],
                "lucas": ["lc"],
                "juan": ["jn"],
                "hechos": ["hch"],
                "romanos": ["rom"],
                "1 corintios": ["1 cor"],
                "2 corintios": ["2 cor"],
                "gálatas": ["gal"],
                "efesios": ["ef"],
                "filipenses": ["fil"],
                "colosenses": ["col"],
                "1 tesalonicenses": ["1 tes"],
                "2 tesalonicenses": ["2 tes"],
                "1 timoteo": ["1 tm"],
                "2 timoteo": ["2 tm"],
                "tito": ["tit"],
                "filemón": ["flm"],
                "hebreos": ["heb"],
                "santiago": ["snt"],
                "1 pedro": ["1 p"],
                "2 pedro": ["2 p"],
                "1 juan": ["1 jn"],
                "2 juan": ["2 jn"],
                "3 juan": ["3 jn"],
                "judas": ["jud"],
                "apocalipsis": ["ap"],
            }
            libro_lower = libro.lower()
            # si la cita ya empieza por el libro completo, devolver cita
            if cita.lower().startswith(libro_lower):
                return cita
            # si la cita empieza por alguna abreviatura del libro, devolver cita
            abrevs = abreviaturas.get(libro_lower, [])
            cita_first = cita.split()[0].lower().rstrip(",")
            if cita_first in [a.lower().rstrip(",") for a in abrevs]:
                return cita
            if libro_lower in abreviaturas:
                for abr in abrevs:
                    if cita.lower().startswith(abr.lower()):
                        return cita
            return f"{libro} {cita}"

        def _cita_salmo(libro: str, cita: str, antifona: Optional[str]) -> str:
            cita = _cita_con_libro(libro, cita)
            if antifona:
                return f"{cita} — {antifona}"
            return cita

        lecturas_data = {
            "primera_lectura": {
                "titulo": "PRIMERA LECTURA",
                "contenido": pres.get("primera_lectura_texto") or "",
                "cita": _cita_con_libro(pres.get("primera_lectura_libro"), pres.get("primera_lectura_cita")),
            },
            "salmo": {
                "titulo": "SALMO RESPONSORIAL",
                "contenido": pres.get("salmo_texto") or "",
                "cita": _cita_salmo(pres.get("salmo_libro"), pres.get("salmo_cita"), pres.get("salmo_antifona")),
            },
            "segunda_lectura": {
                "titulo": "SEGUNDA LECTURA",
                "contenido": pres.get("segunda_lectura_texto") or "",
                "cita": _cita_con_libro(pres.get("segunda_lectura_libro"), pres.get("segunda_lectura_cita")),
            },
            "evangelio": {
                "titulo": "EVANGELIO",
                "contenido": pres.get("evangelio_texto") or "",
                "cita": _cita_con_libro(pres.get("evangelio_libro"), pres.get("evangelio_cita")),
            },
        }

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

            # Inyectar texto real de las lecturas del día
            if tipo in lecturas_data and lecturas_data[tipo]["contenido"]:
                titulo = lecturas_data[tipo]["titulo"]
                contenido = lecturas_data[tipo]["contenido"]
                cita = lecturas_data[tipo]["cita"]
                subtitulo = ""

            # Diapositivas de paso: referencia al tiempo litúrgico y cita del Evangelio
            if tipo == "paso" and "evangelio" in lecturas_data:
                subtitulo = f"{celebracion} · {lecturas_data['evangelio']['cita']}"

            # Expandir diapositivas de paso sin contenido
            if tipo == "paso":
                slides.append(
                    Slide(
                        numero=len(slides) + 1,
                        tipo=tipo,
                        titulo="",
                        contenido="",
                        cita="",
                        subtitulo=subtitulo,
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

        base_name = f"{fecha}_presentacion"
        bundle_dir = OUTPUT_DIR / base_name
        bundle_dir.mkdir(parents=True, exist_ok=True)

        # Copiar lema e ilustraciones (convertir SVG a PNG para PPTX)
        assets_dir = bundle_dir / "assets"
        assets_dir.mkdir(parents=True, exist_ok=True)
        lema_src = LEMA_DIR / "somos_uno.jpg"
        if lema_src.exists():
            shutil.copy(lema_src, assets_dir / "lema_somos_uno.jpg")

        rutas_normalizadas: Dict[str, str] = {}
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
                        rutas_normalizadas[slide.imagen] = f"assets/{png.name}"
                    break
                shutil.copy(src, assets_dir / src.name)
                rutas_normalizadas[slide.imagen] = f"assets/{src.name}"
                break

        # Normalizar todas las rutas de imagen a assets/<nombre>
        for slide in slides:
            if slide.imagen in rutas_normalizadas:
                slide.imagen = rutas_normalizadas[slide.imagen]
            elif slide.imagen:
                # Si no se pudo copiar, al menos normalizar la ruta
                slide.imagen = f"assets/{Path(slide.imagen).name}"

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
