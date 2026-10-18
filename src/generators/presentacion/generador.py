"""
Generador de presentaciones litúrgicas en formato JSON + HTML + PPTX + PDF.

Este módulo mantiene la API pública de GeneradorPresentacionHTML delegando
en submódulos especializados.
"""

from pathlib import Path
from typing import Any

from src.constants import DB_PATH
from src.constants import OUTPUT_DIR_HTML as OUTPUT_DIR
from src.generators.presentacion.builder import (
    _add_cancion_slide,
    _cargar_catalogo,
    _celebracion_from_fecha,
    _construir_slides,
    _extraer_frase_evangelio,
    _formatear_fecha,
    _get_canciones,
    _get_lectura,
    _ilustracion_para,
    _texto_cancion,
)
from src.generators.presentacion.builder import generar as _generar_presentacion
from src.generators.presentacion.html_renderer import _render_html, _slide_to_html
from src.generators.presentacion.pdf_renderer import _render_pdf
from src.generators.presentacion.pptx_renderer import _add_formatted_run, _hex_to_rgb, _render_pptx
from src.generators.presentacion.slide import Slide
from src.generators.presentacion.text_utils import (
    _apply_bold_html,
    _compactar_para_slide,
    _compactar_salmo_o_lectura,
    _es_linea_solo_acordes,
    _escape_html,
    _formatear_cita,
    _paginar_texto,
    _unir_lineas,
)


class GeneradorPresentacionHTML:
    """Genera presentación litúrgica en JSON + HTML + PPTX + PDF."""

    def __init__(self, db_path: str | None = None, output_dir: str | None = None):
        self.db_path = Path(db_path) if db_path else DB_PATH
        self.output_dir = Path(output_dir) if output_dir else OUTPUT_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.lema_path = None  # mantenido por compatibilidad
        self.lema_web = "/presentaciones_assets/lema_somos_uno.jpg"
        self.catalogo = _cargar_catalogo()

    def generar(
        self,
        fecha: str,
        lectura_id: int,
        canciones_ids: dict[str, int],
        incluir_bendicion_agua: bool = False,
        frase_evangelio: str = "",
    ) -> Path:
        """Genera JSON, HTML, PPTX y PDF para la fecha indicada."""
        return _generar_presentacion(
            db_path=str(self.db_path),
            output_dir=str(self.output_dir),
            fecha=fecha,
            lectura_id=lectura_id,
            canciones_ids=canciones_ids,
            incluir_bendicion_agua=incluir_bendicion_agua,
            frase_evangelio=frase_evangelio,
        )

    # Exponer métodos/funciones privados originales para compatibilidad
    def _get_lectura(self, lectura_id: int) -> Any | None:
        return _get_lectura(lectura_id)

    def _get_canciones(self, canciones_ids: dict[str, int]) -> dict[str, dict[str, Any]]:
        return _get_canciones(canciones_ids)

    def _celebracion_from_fecha(self, fecha: str) -> str:
        return _celebracion_from_fecha(fecha)

    def _ilustracion_para(self, tipo: str) -> str:
        return _ilustracion_para(tipo, self.catalogo)

    def _extraer_frase_evangelio(self, lectura: Any) -> str:
        return _extraer_frase_evangelio(lectura)

    def _texto_cancion(self, cancion: dict[str, Any]) -> str:
        return _texto_cancion(cancion)

    def _es_linea_solo_acordes(self, linea: str) -> bool:
        return _es_linea_solo_acordes(linea)

    def _unir_lineas(self, anterior: str, siguiente: str) -> str:
        return _unir_lineas(anterior, siguiente)

    def _compactar_salmo_o_lectura(self, texto: str) -> str:
        return _compactar_salmo_o_lectura(texto)

    def _compactar_para_slide(self, texto: str) -> str:
        return _compactar_para_slide(texto)

    def _formatear_cita(self, libro: str, cita: str) -> str:
        return _formatear_cita(libro, cita)

    def _paginar_texto(self, texto: str, max_chars: int = 1100) -> list[str]:
        return _paginar_texto(texto, max_chars)

    def _add_cancion_slide(
        self,
        add,
        canciones: dict[str, dict[str, Any]],
        key: str,
        tipo: str,
        momento: str,
        titulo_fallback: str,
    ):
        return _add_cancion_slide(add, canciones, key, tipo, momento, titulo_fallback)

    def _construir_slides(
        self,
        fecha: str,
        lectura: Any,
        celebracion: str,
        canciones: dict[str, dict[str, Any]],
        color_info: dict[str, str],
        incluir_bendicion_agua: bool = False,
        frase_evangelio: str = "",
    ) -> list[Slide]:
        return _construir_slides(
            fecha,
            lectura,
            celebracion,
            canciones,
            color_info,
            incluir_bendicion_agua=incluir_bendicion_agua,
            frase_evangelio=frase_evangelio,
            catalogo=self.catalogo,
        )

    def _formatear_fecha(self, fecha: str) -> str:
        return _formatear_fecha(fecha)

    def _render_html(self, data: dict[str, Any], color_info: dict[str, str]) -> str:
        return _render_html(data, color_info)

    def _slide_to_html(self, slide: dict[str, Any], color_info: dict[str, str]) -> str:
        return _slide_to_html(slide, color_info)

    def _escape_html(self, text: str) -> str:
        return _escape_html(text)

    def _apply_bold_html(self, text: str) -> str:
        return _apply_bold_html(text)

    def _render_pptx(self, data: dict[str, Any], pptx_path: Path, assets_dir: Path):
        return _render_pptx(data, pptx_path, assets_dir)

    def _add_formatted_run(
        self,
        p,
        para_text: str,
        is_cancion: bool,
        is_portada: bool,
        para_index: int,
        slide_data: dict[str, Any],
        primary_rgb: tuple,
    ):
        return _add_formatted_run(p, para_text, is_cancion, is_portada, para_index, slide_data, primary_rgb)

    def _hex_to_rgb(self, hex_color: str) -> tuple:
        return _hex_to_rgb(hex_color)

    def _render_pdf(self, html_path: Path, pdf_path: Path):
        return _render_pdf(html_path, pdf_path)
