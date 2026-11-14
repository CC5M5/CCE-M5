"""T2/S2: tamaños de letra globales por parte (ajustes, editor, PPTX, HTML).

Cubre:
- (a) el helper de persistencia devuelve defectos y guarda/valida valores;
- (b) al cambiar p. ej. título a 24 y cuerpo a 12, el preview del editor usa
  tamaños escalonados (px = pt * 440 / 13.333 / 72) y el PPTX usa Pt(24)/Pt(12);
- (c) la portada usa el mismo tamaño global de título que el resto de slides.
"""
from __future__ import annotations

import re
import sqlite3
from pathlib import Path

import pytest
from pptx import Presentation
from pptx.util import Pt

from src import db_manager
from src.constants import TAMANO_LETRA_DEFECTO
from src.generators.presentacion import pptx_renderer


@pytest.fixture()
def db_path(tmp_path: Path) -> Path:
    """Base de datos temporal vacía para los ajustes."""
    db = tmp_path / "db.sqlite3"
    conn = db_manager.create_connection(db)
    conn.close()
    return db


# ---------------------------------------------------------------------------
# (a) Persistencia de ajustes
# ---------------------------------------------------------------------------

def test_get_ajustes_sin_filas_devuelve_defectos(db_path: Path) -> None:
    assert db_manager.get_ajustes_tamano_letra(db_path) == TAMANO_LETRA_DEFECTO


def test_guardar_persiste_y_mantiene_defecto_en_el_resto(db_path: Path) -> None:
    db_manager.guardar_ajustes_tamano_letra({"titulo": 24, "cuerpo": 12}, db_path)
    v = db_manager.get_ajustes_tamano_letra(db_path)
    assert v["titulo"] == 24
    assert v["cuerpo"] == 12
    assert v["subtitulo"] == TAMANO_LETRA_DEFECTO["subtitulo"]
    assert v["cita"] == TAMANO_LETRA_DEFECTO["cita"]


def test_guardar_acepta_extremos(db_path: Path) -> None:
    db_manager.guardar_ajustes_tamano_letra({"titulo": 8, "cuerpo": 72}, db_path)
    v = db_manager.get_ajustes_tamano_letra(db_path)
    assert v["titulo"] == 8
    assert v["cuerpo"] == 72


def test_guardar_rechaza_fuera_de_rango_y_no_modifica(db_path: Path) -> None:
    with pytest.raises(ValueError):
        db_manager.guardar_ajustes_tamano_letra({"titulo": 73}, db_path)
    assert (
        db_manager.get_ajustes_tamano_letra(db_path)["titulo"]
        == TAMANO_LETRA_DEFECTO["titulo"]
    )
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    filas = conn.execute("SELECT parte FROM ajustes_editor").fetchall()
    conn.close()
    assert [f["parte"] for f in filas] == []


def test_guardar_rechaza_parte_desconocida(db_path: Path) -> None:
    with pytest.raises(ValueError):
        db_manager.guardar_ajustes_tamano_letra({"momento": 30}, db_path)


# ---------------------------------------------------------------------------
# (b)/(c) PPTX con los tamaños guardados
# ---------------------------------------------------------------------------

def _datos(tamanos: dict[str, int] | None = None) -> dict:
    meta = {
        "fecha": "2026-01-04",
        "celebracion": "Test S2",
        "color_liturgico": "verde",
    }
    if tamanos is not None:
        meta["tamanos_fuente"] = tamanos
    return {
        "meta": meta,
        "slides": [
            {
                "numero": 1, "tipo": "portada", "titulo": "TITULO PORTADA",
                "contenido": "", "cita": "", "subtitulo": "4 E · C",
                "momento": "", "imagen": "",
            },
            {
                "numero": 2, "tipo": "evangelio", "titulo": "EVANGELIO",
                "contenido": "Texto del cuerpo.", "cita": "Jn 1,1",
                "subtitulo": "Subtítulo", "momento": "", "imagen": "",
            },
            {
                "numero": 3, "tipo": "entrada", "titulo": "ENTRADA",
                "contenido": "Letra de la canción.", "cita": "",
                "subtitulo": "", "momento": "Canción de Entrada", "imagen": "",
            },
        ],
    }


def _tamanos_por_slide(pptx_path: Path) -> list[dict[str, float]]:
    """{texto: pt} por cada slide (textos únicos en el fixture)."""
    pres = Presentation(str(pptx_path))
    resultado: list[dict[str, float]] = []
    for slide in pres.slides:
        por_texto: dict[str, float] = {}
        for shape in slide.shapes:
            if not shape.has_text_frame:
                continue
            for para in shape.text_frame.paragraphs:
                if not para.runs or not para.text.strip():
                    continue
                size = para.runs[0].font.size
                if size is not None:
                    por_texto[para.text] = pytest.approx(size.pt, abs=0.01)
        resultado.append(por_texto)
    return resultado


def _render(datos: dict, tmp_path: Path) -> Path:
    out = tmp_path / "presentacion.pptx"
    assets = tmp_path / "assets"
    assets.mkdir(exist_ok=True)
    pptx_renderer._render_pptx(datos, str(out), str(assets))
    return out


def test_pptx_usa_tamanos_guardados(db_path: Path, tmp_path: Path) -> None:
    tamanos = {"titulo": 24, "subtitulo": 18, "cita": 14, "cuerpo": 12}
    slides = _tamanos_por_slide(_render(_datos(tamanos), tmp_path))

    portada, evangelio, entrada = slides
    # Título y cada parte usan el valor guardado...
    assert portada["TITULO PORTADA"] == pytest.approx(24.0)
    assert evangelio["EVANGELIO"] == pytest.approx(24.0)
    assert evangelio["Subtítulo"] == pytest.approx(18.0)
    assert evangelio["Jn 1,1"] == pytest.approx(14.0)
    assert evangelio["Texto del cuerpo."] == pytest.approx(12.0)
    # ...el momento se mantiene fijo (15 pt) y el cuerpo de canciòn usa el global.
    assert entrada["CANCIÓN DE ENTRADA"] == pytest.approx(15.0)
    assert entrada["ENTRADA"] == pytest.approx(24.0)
    assert entrada["Letra de la canción."] == pytest.approx(12.0)
    # (c) la portada usa el mismo título global que cualquier otro slide.
    assert portada["TITULO PORTADA"] == evangelio["EVANGELIO"]


def test_pptx_sin_tamanos_usa_defectos(db_path: Path, tmp_path: Path) -> None:
    slides = _tamanos_por_slide(_render(_datos(), tmp_path))
    portada, evangelio, entrada = slides
    assert portada["TITULO PORTADA"] == pytest.approx(
        TAMANO_LETRA_DEFECTO["titulo"]
    )
    assert evangelio["EVANGELIO"] == pytest.approx(TAMANO_LETRA_DEFECTO["titulo"])
    assert evangelio["Subtítulo"] == pytest.approx(TAMANO_LETRA_DEFECTO["subtitulo"])
    assert evangelio["Jn 1,1"] == pytest.approx(TAMANO_LETRA_DEFECTO["cita"])
    assert evangelio["Texto del cuerpo."] == pytest.approx(TAMANO_LETRA_DEFECTO["cuerpo"])
    assert entrada["CANCIÓN DE ENTRADA"] == pytest.approx(15.0)
    assert entrada["Letra de la canción."] == pytest.approx(TAMANO_LETRA_DEFECTO["cuerpo"])


def test_html_usa_tamanos_guardados(db_path: Path) -> None:
    """El HTML/Reveal escala los pt guardados al lienzo de 1280 px."""
    import src.generators.presentacion.html_renderer as html_renderer

    html = html_renderer._render_html(
        _datos({"titulo": 24, "cuerpo": 12}),
        {"from": "#e8f5e9", "to": "#c8e6c9", "acento": "#2e7d32"},
    )
    factor = html_renderer.REVEAL_PT_A_PX
    assert _var_fuente(html, "titulo") == pytest.approx(24 * factor, abs=0.01)
    assert _var_fuente(html, "cuerpo") == pytest.approx(12 * factor, abs=0.01)
    # La parte sin valor guardado conserva su defecto.
    assert _var_fuente(html, "cita") == pytest.approx(
        TAMANO_LETRA_DEFECTO["cita"] * factor, abs=0.01
    )


# ---------------------------------------------------------------------------
# (b) Preview del editor con tamaños escalonados
# ---------------------------------------------------------------------------

def _var_fuente(html: str, parte: str) -> float:
    m = re.search(rf"--fuente-{parte}:([\d.]+)px", html)
    assert m, f"variable --fuente-{parte} no encontrada en: {html[:500]}"
    return float(m.group(1))


def test_preview_editor_escala_pt_a_px(db_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import scripts.editor_diapositivas_server as eds

    monkeypatch.setattr(eds, "DB_PATH", str(db_path))
    db_manager.guardar_ajustes_tamano_letra({"titulo": 24, "cuerpo": 12}, db_path)

    slide = {
        "numero": 1, "tipo": "portada", "titulo": "T", "contenido": "c",
        "cita": "", "subtitulo": "", "momento": "", "imagen": "",
    }
    html = eds._render_preview(slide)
    factor = eds.PREVIEW_W_PX / eds.SLIDE_WIDTH_INCHES / 72
    assert _var_fuente(html, "titulo") == pytest.approx(24 * factor, abs=0.01)
    assert _var_fuente(html, "cuerpo") == pytest.approx(12 * factor, abs=0.01)
    # El resto de partes siguen en sus defectos.
    assert _var_fuente(html, "subtitulo") == pytest.approx(
        TAMANO_LETRA_DEFECTO["subtitulo"] * factor, abs=0.01
    )


def test_preview_css_usa_variables_y_momento_fijo(db_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    import scripts.editor_diapositivas_server as eds

    monkeypatch.setattr(eds, "DB_PATH", str(db_path))
    base = eds._render_base("t")
    assert "var(--fuente-titulo" in base
    assert "var(--fuente-subtitulo" in base
    assert "var(--fuente-cita" in base
    assert "var(--fuente-cuerpo" in base
    # El label "momento" (h3) conserva su tamaño fijo.
    assert "h3 { font-size: 10px" in base
