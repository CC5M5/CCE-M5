"""Utilidades de procesamiento y formato de texto para presentaciones."""

import re

PALABRAS_CORTAS = {
    "EL", "ÉL", "LA", "LAS", "LOS", "UN", "UNA", "Y", "O", "U", "NO", "SI", "ME", "SE", "TE",
    "LO", "LE", "LES", "NOS", "OS", "DEL", "AL", "CON", "POR", "PARA", "QUE", "COMO", "CUANDO",
    "MI", "SU", "SUS", "TU", "TUS", "ES", "SON", "ESTÁ", "ESTAN", "A", "EN", "DE", "DIOS",
}


ESTRIBILLO_MARCAS = {"estribillo", "estrib", "coro", "todos", "todas"}


BASURA_RE = re.compile(
    r"volver|lista de canciones|escuchar|\[\s*\]|\btone\b|tono|\^",
    re.IGNORECASE,
)


TERMINADORES = ".!?;:)"


def _es_linea_solo_acordes(linea: str) -> bool:
    """Devuelve True si la línea contiene únicamente notas musicales/acordes."""
    nota = r"(?:[A-Ga-g](?:[#b\u266d\u266f]|es|is|bemol|sostenido)?|Do|Re|Mi|Fa|Sol|La|Si|do|re|mi|fa|sol|la|si)"
    calidad = r"(?:m(?:in)?|M(?:aj)?|maj7?|7|9|6|dim|sus|add|aug|°|0|#|b|\u266d|\u266f|es|is|bemol|sostenido)"
    bajo = rf"(?:/{nota})"
    acorde_completo = rf"(?:{nota}(?:\s*{calidad})?(?:\s*{bajo})?)"
    acordes_re = re.compile(
        rf"^\s*(?:\(\s*\d*[\u00aa\u00ba°]?\s*:?\s*)?{acorde_completo}(?:\s+{acorde_completo})*\s*\)?\s*$"
    )
    return bool(acordes_re.match(linea))


def _unir_lineas(anterior: str, siguiente: str) -> str:
    """Une dos líneas de letra respetando guiones de separación silábica."""
    if anterior.endswith("-"):
        return anterior[:-1] + siguiente
    return f"{anterior} {siguiente}"


def _compactar_salmo_o_lectura(texto: str) -> str:
    """
    Compacta salmos y lecturas bíblicas.

    Respeta los párrafos/estrofas del texto original. Una estrofa nueva
    se detecta cuando una línea empieza en mayúscula y la anterior termina
    en punto fuerte. Dentro de cada estrofa se unen las frases cortas con
    punto y coma para formar un párrafo continuo.
    """
    if not texto:
        return ""

    lineas = [l.strip() for l in texto.splitlines() if l.strip()]
    if not lineas:
        return ""

    estrofas: list[list[str]] = []
    actual: list[str] = [lineas[0]]

    def _empieza_nuevo_bloque(linea: str) -> bool:
        return bool(re.match(r"^[A-ZÁÉÍÓÚÑ]", linea))

    for i in range(1, len(lineas)):
        linea = lineas[i]
        ultima = actual[-1]
        if ultima.endswith((".", "!", "?", ":")) and _empieza_nuevo_bloque(linea):
            estrofas.append(actual)
            actual = [linea]
        else:
            actual.append(linea)

    if actual:
        estrofas.append(actual)

    resultado: list[str] = []
    for estrofa in estrofas:
        unido = estrofa[0]
        for frase in estrofa[1:]:
            if unido.endswith("-"):
                unido = unido[:-1] + frase
                continue
            if unido[-1] in ",;:":
                unido = f"{unido} {frase}"
            else:
                unido = f"{unido}; {frase}"
        resultado.append(unido)

    return "\n\n".join(resultado)


def _compactar_para_slide(texto: str) -> str:
    """
    Lleva un texto plano a formato de slide compacto.

    - Líneas consecutivas no vacías se unen con \n simple (mismo verso/párrafo).
    - Líneas en blanco separan estrofas/párrafos (\n\n).
    """
    if not texto:
        return ""
    parrafos = []
    actual = []
    for linea in texto.splitlines():
        linea = linea.strip()
        if linea:
            actual.append(linea)
        else:
            if actual:
                parrafos.append("\n".join(actual))
                actual = []
    if actual:
        parrafos.append("\n".join(actual))
    return "\n\n".join(parrafos)


def _paginar_texto(texto: str, max_chars: int = 1100) -> list[str]:
    """Divide un texto largo en fragmentos que quepan en una slide 4:3 real."""
    if len(texto) <= max_chars:
        return [texto]

    parrafos = _compactar_salmo_o_lectura(texto).split("\n\n")
    fragmentos = []
    actual = ""
    for parrafo in parrafos:
        if len(actual) + len(parrafo) + 2 > max_chars and actual:
            fragmentos.append(actual.strip())
            actual = parrafo
        else:
            actual = f"{actual}\n\n{parrafo}" if actual else parrafo
    if actual:
        fragmentos.append(actual.strip())

    resultado = []
    for frag in fragmentos:
        if len(frag) <= max_chars:
            resultado.append(frag)
        else:
            oraciones = frag.replace(". ", ".\n").split("\n")
            actual2 = ""
            for oracion in oraciones:
                if len(actual2) + len(oracion) + 1 > max_chars and actual2:
                    resultado.append(actual2.strip())
                    actual2 = oracion
                else:
                    actual2 = f"{actual2} {oracion}".strip()
            if actual2:
                resultado.append(actual2.strip())
    return fragmentos


def _formatear_cita(libro: str, cita: str) -> str:
    """Devuelve la cita completa incluyendo el libro de la Biblia."""
    if not libro or not cita:
        return cita or ""
    libro = libro.strip()
    cita = cita.strip()
    if cita.lower().startswith(libro.lower()):
        return cita
    return f"{libro} {cita}"


def _escape_html(text: str) -> str:
    return (
        str(text)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def _apply_bold_html(text: str) -> str:
    """Convierte **texto** en <strong>texto</strong> para HTML."""
    return re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)


def _texto_cancion(cancion: dict) -> str:
    """
    Devuelve la letra de una canción limpia, compacta y lista para slide.

    - Elimina líneas de acordes musicales residuales.
    - Une frases cortadas artificialmente por saltos de línea.
    - Detecta estribillos y los marca con doble asterisco para negrita.
    """
    texto = cancion.get("letra_sin_acordes") or cancion.get("letra_con_acordes") or ""
    if not texto:
        return ""

    lineas = texto.splitlines()
    limpio: list[str] = []
    for linea in lineas:
        linea = linea.strip()
        if not linea:
            continue
        if linea in ["/", "|", "—"]:
            continue
        if BASURA_RE.search(linea):
            continue
        if _es_linea_solo_acordes(linea):
            continue
        limpio.append(linea)

    unidas: list[str] = []
    actual = ""
    for linea in limpio:
        if _es_linea_solo_acordes(linea):
            continue

        if linea.strip().upper() in ESTRIBILLO_MARCAS:
            if actual:
                unidas.append(actual)
                actual = ""
            unidas.append(linea.strip().upper())
            continue

        if not actual:
            actual = linea
            continue

        palabras_actuales = actual.split()
        if (
            all(p.upper() in PALABRAS_CORTAS for p in palabras_actuales)
            and len(palabras_actuales) <= 2
            and actual[-1] not in TERMINADORES
        ):
            actual = _unir_lineas(actual, linea)
            continue

        if actual[-1] in TERMINADORES:
            unidas.append(actual)
            actual = linea
            continue

        if re.match(r"^[a-záéíóúñ]", linea):
            actual = _unir_lineas(actual, linea)
            continue

        if actual.strip().lower() in ESTRIBILLO_MARCAS:
            unidas.append(actual)
            actual = linea
            continue

        if re.match(r"^[A-ZÁÉÍÓÚÑ¿¡]", linea):
            if len(palabras_actuales) <= 2 and actual[-1] not in TERMINADORES:
                actual = _unir_lineas(actual, linea)
            else:
                unidas.append(actual)
                actual = linea
        else:
            actual = _unir_lineas(actual, linea)

    if actual:
        unidas.append(actual)

    resultado: list[str] = []
    en_estribillo = False
    for linea in unidas:
        linea_l = linea.lower().strip("():[] ")
        if linea_l in ESTRIBILLO_MARCAS:
            en_estribillo = not en_estribillo
            continue

        if linea == linea.upper() and len(linea) > 8 and not linea.startswith("("):
            resultado.append(f"**{linea}**")
            continue

        if en_estribillo:
            resultado.append(f"**{linea}**")
        else:
            resultado.append(linea)

    return _compactar_para_slide("\n".join(resultado))
