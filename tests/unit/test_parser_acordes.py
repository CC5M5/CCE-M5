"""Tests para src/parsers/acordes_parser_v3.py."""

from src.parsers.acordes_parser_v3 import AcordesParser


def _crear_parser() -> AcordesParser:
    return AcordesParser()


def test_letra_simple_sin_acordes():
    """Una canción solo con letra debe generar líneas de tipo 'letra'."""
    texto = "Amén, amén, amén\nAleluya, aleluya"
    parser = _crear_parser()
    estructura = parser.parsear_cancion_completa(texto)

    assert len(estructura) == 2
    assert all(linea.tipo == "letra" for linea in estructura)
    assert estructura[0].letra == "Amén, amén, amén"
    assert estructura[1].letra == "Aleluya, aleluya"
    assert parser.detectar_tono(estructura) == "No detectado"


def test_acordes_sobre_letra():
    """Empareja una línea de acordes con la siguiente línea de letra."""
    texto = "SOL   Lam        Sim                 DO          RE7\nPREPARAD EL CAMINO AL SEÑOR"
    parser = _crear_parser()
    estructura = parser.parsear_cancion_completa(texto)

    assert len(estructura) == 1
    linea = estructura[0]
    assert linea.tipo == "acordes_letra"
    assert linea.letra == "PREPARAD EL CAMINO AL SEÑOR"
    nombres = [a.acorde for a in linea.acordes]
    assert nombres == ["SOL", "Lam", "Sim", "DO", "RE7"]
    # El primer acorde debe anclarse a la posición 0.
    assert linea.acordes[0].posicion == 0
    # Posiciones no negativas y monótonas.
    assert all(a.posicion >= 0 for a in linea.acordes)
    assert linea.acordes[1].posicion > linea.acordes[0].posicion


def test_secciones_intro_estrofa_puente():
    """Detecta secciones entre corchetes y etiquetas de sección con ':'."""
    # Se añade una línea vacía entre [Intro] y sus acordes para que el parser
    # no interprete la sección siguiente como letra emparejada a esos acordes.
    texto = (
        "[Intro]\n"
        "Do Fa Sol Do\n"
        "\n"
        "[Estrofa]\n"
        "Do Sol\nVenimos a tu mesa\n"
        "[Puente]\n"
        "La7 Re7\n"
        "Quebranta el pan\n"
        "Puente 2: La7 Re7\n"
        "Quebranta el pan"
    )
    parser = _crear_parser()
    estructura = parser.parsear_cancion_completa(texto)

    tipos = [l.tipo for l in estructura]
    assert "sección" in tipos
    textos_seccion = [l.texto for l in estructura if l.tipo == "sección"]
    assert "[Intro]" in textos_seccion
    assert "[Estrofa]" in textos_seccion
    assert "[Puente]" in textos_seccion
    assert "Puente 2" in textos_seccion

    # La línea con etiqueta 'Puente:' debe emparejar acordes + letra.
    bloque_puente = next(
        (l for l in estructura if l.tipo == "acordes_letra" and "Re7" in [a.acorde for a in l.acordes]),
        None,
    )
    assert bloque_puente is not None
    assert bloque_puente.letra == "Quebranta el pan"


def test_repeticiones_x2():
    """Líneas de acordes con indicadores de repetición deben seguir reconociéndose."""
    texto = "Do Sol Lam Fa (x2)\nVenid fieles todos"
    parser = _crear_parser()
    estructura = parser.parsear_cancion_completa(texto)

    assert any(l.tipo == "acordes_letra" for l in estructura)
    linea = next(l for l in estructura if l.tipo == "acordes_letra")
    nombres = [a.acorde for a in linea.acordes]
    assert "Do" in nombres
    assert "Fa" in nombres
    assert "(x2)" not in nombres


def test_notas_al_pie():
    """Notas tipo 'Nota: ...' deben conservarse como líneas de letra."""
    texto = "Nota: tocar despacio la primera vez\nDo Sol\nAlaba a Dios"
    parser = _crear_parser()
    estructura = parser.parsear_cancion_completa(texto)

    lineas_letra = [l for l in estructura if l.tipo == "letra"]
    assert any("Nota:" in l.letra for l in lineas_letra)


def test_conversion_html_visual():
    """generar_html_visual produce la estructura esperada con acordes posicionados."""
    texto = "Do        Sol\nBendito sea el Señor"
    parser = _crear_parser()
    estructura = parser.parsear_cancion_completa(texto)
    html = parser.generar_html_visual(estructura)

    assert '<div class="cancion-con-acordes">' in html
    assert '<span class="acorde"' in html
    assert "Bendito sea el Señor" in html


def test_deteccion_tono():
    """detectar_tono elige el acorde más frecuente."""
    texto = (
        "Sol Re7 Do\nSanto, santo, santo\n"
        "Sol Re7 Do\nSanto, santo, santo\n"
        "Mim Lam Re7 Sol\nEl cielo y la tierra"
    )
    parser = _crear_parser()
    estructura = parser.parsear_cancion_completa(texto)
    tono = parser.detectar_tono(estructura)
    assert tono == "Sol"


def test_html_limpia_etiquetas_de_entrada():
    """El HTML resultante no incluye etiquetas HTML del texto de entrada."""
    texto = "SOL\n<strong>Todo es tuyo</strong>"
    parser = _crear_parser()
    estructura = parser.parsear_cancion_completa(texto)
    html = parser.generar_html_visual(estructura)

    assert "<strong>" not in html
    assert "Todo es tuyo" in html
