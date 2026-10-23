"""Tests para src/generators/presentacion/text_utils.py."""

from __future__ import annotations

from src.generators.presentacion import text_utils as tu


class TestLineaSoloAcordes:
    def test_solo_acordes(self) -> None:
        assert tu._es_linea_solo_acordes("Sol   Lam        Sol7")
        assert tu._es_linea_solo_acordes("G Am C D")

    def test_no_acordes(self) -> None:
        assert not tu._es_linea_solo_acordes("PREPARAD EL CAMINO AL SEÑOR")
        assert not tu._es_linea_solo_acordes("")


class TestUnirLineas:
    def test_guion(self) -> None:
        assert tu._unir_lineas("cami-", "no") == "camino"

    def test_espacio(self) -> None:
        assert tu._unir_lineas("camin", "no") == "camin no"


class TestCompactar:
    def test_compactar_salmo(self) -> None:
        texto = "Bendice alma mía al Señor\nBendice alma mía al Señor\ncontinúa la frase."
        resultado = tu._compactar_salmo_o_lectura(texto)
        assert "Bendice alma mía al Señor" in resultado
        assert ";" in resultado

    def test_compactar_slide(self) -> None:
        texto = "Línea 1\nLínea 2\n\nLínea 3"
        resultado = tu._compactar_para_slide(texto)
        assert resultado == "Línea 1\nLínea 2\n\nLínea 3"


class TestPaginar:
    def test_corto_devuelve_unico(self) -> None:
        assert tu._paginar_texto("corto") == ["corto"]

    def test_largo_se_fragmenta(self) -> None:
        largo = "Párrafo. " * 200
        fragmentos = tu._paginar_texto(largo, max_chars=500)
        assert len(fragmentos) > 1
        assert all(len(f) <= 500 for f in fragmentos)


class TestFormatear:
    def test_formatear_cita(self) -> None:
        assert tu._formatear_cita("Salmo", "118") == "Salmo 118"
        assert tu._formatear_cita("Salmo", "Salmo 118") == "Salmo 118"
        assert tu._formatear_cita("", "118") == "118"

    def test_escape_html(self) -> None:
        assert tu._escape_html("a < b > c & d") == "a &lt; b &gt; c &amp; d"

    def test_apply_bold_html(self) -> None:
        assert tu._apply_bold_html("**negrita**") == "<strong>negrita</strong>"


class TestTextoCancion:
    def test_elimina_acordes(self) -> None:
        cancion = {"letra_sin_acordes": "Sol\nPREPARAD EL CAMINO\nLam\nAL SEÑOR"}
        texto = tu._texto_cancion(cancion)
        assert "Sol" not in texto
        assert "Lam" not in texto
        assert "PREPARAD EL CAMINO" in texto

    def test_detecta_estribillo(self) -> None:
        cancion = {"letra_sin_acordes": "ESTRIBILLO\nAleluya, aleluya\nAleluya\nVerso\nAleluya, aleluya"}
        texto = tu._texto_cancion(cancion)
        assert "**" in texto
        assert "Aleluya, aleluya" in texto

    def test_basura(self) -> None:
        cancion = {"letra_sin_acordes": "volver a lista de canciones\nPREPARAD EL CAMINO"}
        texto = tu._texto_cancion(cancion)
        assert "volver a lista" not in texto.lower()
        assert "PREPARAD EL CAMINO" in texto
