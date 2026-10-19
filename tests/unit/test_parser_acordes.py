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

    tipos = [item.tipo for item in estructura]
    assert "sección" in tipos
    textos_seccion = [item.texto for item in estructura if item.tipo == "sección"]
    assert "[Intro]" in textos_seccion
    assert "[Estrofa]" in textos_seccion
    assert "[Puente]" in textos_seccion
    assert "Puente 2" in textos_seccion

    # La línea con etiqueta 'Puente:' debe emparejar acordes + letra.
    bloque_puente = next(
        (
            item
            for item in estructura
            if item.tipo == "acordes_letra" and "Re7" in [a.acorde for a in item.acordes]
        ),
        None,
    )
    assert bloque_puente is not None
    assert bloque_puente.letra == "Quebranta el pan"


def test_repeticiones_x2():
    """Líneas de acordes con indicadores de repetición deben seguir reconociéndose."""
    texto = "Do Sol Lam Fa (x2)\nVenid fieles todos"
    parser = _crear_parser()
    estructura = parser.parsear_cancion_completa(texto)

    assert any(item.tipo == "acordes_letra" for item in estructura)
    linea = next(item for item in estructura if item.tipo == "acordes_letra")
    nombres = [a.acorde for a in linea.acordes]
    assert "Do" in nombres
    assert "Fa" in nombres
    assert "(x2)" not in nombres


def test_notas_al_pie():
    """Notas tipo 'Nota: ...' deben conservarse como líneas de letra."""
    texto = "Nota: tocar despacio la primera vez\nDo Sol\nAlaba a Dios"
    parser = _crear_parser()
    estructura = parser.parsear_cancion_completa(texto)

    lineas_letra = [item for item in estructura if item.tipo == "letra"]
    assert any("Nota:" in item.letra for item in lineas_letra)


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


def test_limpiar_texto_cancion():
    """Elimina metadatos del blogspot."""
    from src.parsers.acordes_parser_v3 import limpiar_texto_cancion

    texto = "escuchar\nDo Re Mi\nvolver a lista de canciones\n/version/"
    limpio = limpiar_texto_cancion(texto)
    assert "Do Re Mi" in limpio
    assert "escuchar" not in limpio
    assert "volver" not in limpio


def test_limpiar_texto_preservando_espacios():
    from src.parsers.acordes_parser_v3 import limpiar_texto_preservando_espacios

    texto = "escuchar\nDo   Re   Mi\nLínea de letra"
    limpio = limpiar_texto_preservando_espacios(texto)
    assert "Do   Re   Mi" in limpio
    assert "escuchar" not in limpio


def test_acorde_posicionado_negativo():
    from src.parsers.acordes_parser_v3 import AcordePosicionado

    try:
        AcordePosicionado("Do", -1)
        raise AssertionError("Debería lanzar ValueError")
    except ValueError as exc:
        assert "negativa" in str(exc)


def test_es_linea_de_acordes_varios():
    """Reconoce líneas de acordes puras y rechaza líneas de letra."""
    parser = _crear_parser()
    assert parser.es_linea_de_acordes("Do Re Mi") is True
    assert parser.es_linea_de_acordes("Do Re Mi.") is False
    assert parser.es_linea_de_acordes("Esta es una línea de letra") is False
    assert parser.es_linea_de_acordes("[Intro] Do Re Mi") is True
    assert parser.es_linea_de_acordes("Intro: Do Re Mi") is True


def test_parsear_acordes_con_slash():
    """Soporta slash chords."""
    texto = "Do/Sol   Re/La\nLínea de letra"
    parser = _crear_parser()
    estructura = parser.parsear_cancion_completa(texto)
    assert len(estructura) == 1
    assert estructura[0].tipo == "acordes_letra"
    acordes = [a.acorde for a in estructura[0].acordes]
    assert "Do/Sol" in acordes
    assert "Re/La" in acordes






def test_detectar_tono_con_acordes():
    """Detecta el tono más frecuente."""
    texto = "Do Re Do\nLínea uno\nDo Mi Do"
    parser = _crear_parser()
    estructura = parser.parsear_cancion_completa(texto)
    assert parser.detectar_tono(estructura) == "Do"


def test_detectar_tono_sin_acordes():
    """Sin acordes no detecta tono."""
    texto = "Solo letra\nMás letra"
    parser = _crear_parser()
    estructura = parser.parsear_cancion_completa(texto)
    assert parser.detectar_tono(estructura) == "No detectado"
