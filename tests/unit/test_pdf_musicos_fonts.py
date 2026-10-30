"""Tests para la resolución de fuentes de src/generators/pdf_musicos.py."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.generators import pdf_musicos
from src.generators.pdf_musicos import (
    FuenteNoDisponibleError,
    _find_font_path,
    _find_monospace_pair,
    _registrar_fuentes,
)

COURIER_ALIASES = ["Courier New", "TeX Gyre Cursor", "Courier"]


def _index_sin_courier() -> dict[tuple[str, str], Path]:
    """Índice con una monoespaciada genérica pero sin la familia preferida."""
    book = Path("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf")
    bold = Path("/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf")
    return {
        ("dejavu sans mono", "book"): book,
        ("dejavu sans mono", ""): book,
        ("dejavu sans mono", "bold"): bold,
    }


def test_find_font_path_aun_lanza_sin_courier() -> None:
    # Comportamiento existente: el helper de búsqueda por alias no se ve
    # afectado por el respaldo monoespaciado.
    with pytest.raises(FuenteNoDisponibleError):
        _find_font_path(COURIER_ALIASES, ["Regular", ""], _index_sin_courier())


def test_find_monospace_pair_usa_alias_de_fontconfig(monkeypatch: pytest.MonkeyPatch) -> None:
    book = Path("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf")
    bold = Path("/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf")
    monkeypatch.setattr(
        pdf_musicos, "_fc_match_family_file", lambda spec: ("dejavu sans mono", book)
    )
    assert _find_monospace_pair(_index_sin_courier()) == (book, bold)


def test_find_monospace_pair_familia_conocida_del_indice(monkeypatch: pytest.MonkeyPatch) -> None:
    book = Path("/usr/share/fonts/liberation/LiberationMono-Regular.ttf")
    bold = Path("/usr/share/fonts/liberation/LiberationMono-Bold.ttf")
    monkeypatch.setattr(pdf_musicos, "_fc_match_family_file", lambda spec: None)
    index = {
        ("liberation mono", "regular"): book,
        ("liberation mono", ""): book,
        ("liberation mono", "bold"): bold,
    }
    assert _find_monospace_pair(index) == (book, bold)


def test_find_monospace_pair_reutiliza_regular_sin_bold(monkeypatch: pytest.MonkeyPatch) -> None:
    book = Path("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf")
    monkeypatch.setattr(pdf_musicos, "_fc_match_family_file", lambda spec: None)
    index = {
        ("dejavu sans mono", "book"): book,
        ("dejavu sans mono", ""): book,
    }
    assert _find_monospace_pair(index) == (book, book)


def test_find_monospace_pair_lanza_si_no_hay_monoespaciada(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(pdf_musicos, "_fc_match_family_file", lambda spec: None)
    with pytest.raises(FuenteNoDisponibleError):
        _find_monospace_pair({})


class _PdfFake:
    """Doble mínimo: _registrar_fuentes solo usa .fonts y .add_font."""

    def __init__(self) -> None:
        self.fonts: dict[str, object] = {}
        self.added: list[tuple[str, str, str]] = []

    def add_font(self, fam: str, style: str, fname: str) -> None:
        self.added.append((fam, style, fname))
        self.fonts[f"{fam}-{style}"] = object()


def test_registrar_fuentes_respalda_con_monoespaciada(monkeypatch: pytest.MonkeyPatch) -> None:
    # El error original: sin Courier en el sistema, _registrar_fuentes lanzaba
    # FuenteNoDisponibleError y rompía el paso generate_assets.
    index = _index_sin_courier()
    monkeypatch.setattr(pdf_musicos, "_build_font_index", lambda: index)
    monkeypatch.setattr(pdf_musicos, "_fc_match_family_file", lambda spec: None)
    pdf = _PdfFake()
    _registrar_fuentes(pdf)  # type: ignore[arg-type]
    regular = str(index[("dejavu sans mono", "")])
    bold = str(index[("dejavu sans mono", "bold")])
    assert ("CourierNew", "", regular) in pdf.added
    assert ("CourierNew", "B", bold) in pdf.added
