#!/usr/bin/env python3
"""
Parser de acordes con posicionamiento exacto para el Cancionero Escolapio.

Modelo de datos:
- El cancionero representa los acordes en una línea superior y la letra en
  una línea inferior, alineadas por caracteres.
- Cada acorde se ancla a una posición (índice de carácter) dentro de la
  línea de letra asociada.

El parser recorre el texto identificando:
- Líneas de acordes (contienen únicamente tokens reconocidos como acordes).
- Líneas de letra (cualquier otro texto).
- Cuando una línea de acordes va seguida de una línea de letra, se emparejan
  y se calculan las posiciones exactas de cada acorde sobre la letra.
"""

from __future__ import annotations

import html
import json
import re
from dataclasses import dataclass, field
from typing import Iterator, List, Optional


# ---------------------------------------------------------------------------
# Modelo de datos
# ---------------------------------------------------------------------------

@dataclass
class AcordePosicionado:
    """Un acorde con su posición de inicio (índice de carácter)."""
    acorde: str
    posicion: int

    def __post_init__(self):
        if self.posicion < 0:
            raise ValueError("La posición de un acorde no puede ser negativa")


@dataclass
class LineaCancion:
    """Bloque de canción: opcionalmente una línea de acordes y su letra."""
    tipo: str  # 'acordes_letra', 'letra', 'acordes', 'vacía', 'sección'
    acordes: List[AcordePosicionado] = field(default_factory=list)
    letra: str = ""
    texto: str = ""  # Para líneas de metadatos/sección


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

class AcordesParser:
    """
    Parser robusto de líneas de acordes para cancioneros.

    Características:
    - Soporta notación española (Do, Re, Mi, Fa, Sol, La, Si) e inglesa (C, D, E, F, G, A, B).
    - Soporta sostenidos (#), bemoles (b) y dobles alteraciones.
    - Soporta extensiones: m, 7, m7, M, maj7, sus4, sus2, dim, aug, add9, 9, 11, 13.
    - Soporta slash chords (Do/Sol, C/E).
    - Evita falsos positivos con palabras comunes como "LA", "MI", "UN", etc.
    - Empareja líneas de acordes con la siguiente línea de letra.
    - Preserva el texto de la letra sin modificarlo.
    """

    # Patrón de acordes compilado una sola vez por clase.
    # El grupo de captura principal es el acorde completo.
    _PATRON_ACORDES: Optional[re.Pattern[str]] = None

    # Notas base reconocidas.
    NOTAS_ESPANOLAS = ("Do", "Re", "Mi", "Fa", "Sol", "La", "Si")
    NOTAS_INGLESAS = ("C", "D", "E", "F", "G", "A", "B")

    # Extensiones permitidas, ordenadas de más específicas a menos para evitar
    # que "m7" se consuma como "m" + "7".
    EXTENSIONES = (
        r"maj7", r"maj9", r"maj11", r"maj13",
        r"m7", r"m9", r"m11", r"m13",
        r"add9", r"add11", r"add13",
        r"sus4", r"sus2",
        r"dim", r"aug",
        r"7", r"9", r"11", r"13",
        r"m", r"M",
    )

    @classmethod
    def _compilar_patron(cls) -> re.Pattern[str]:
        if cls._PATRON_ACORDES is not None:
            return cls._PATRON_ACORDES

        # Notas base: Sol debe ir antes de Do/Re/... para no matchear 'Sol' como 'Sol' (bien),
        # pero 'Sol' contiene 'So' que no es nota. No hay problema con Do/Re... salvo 'La'.
        # Ordenamos por longitud descendente para evitar que 'La' mateche antes que nada.
        notas = sorted(cls.NOTAS_ESPANOLAS + cls.NOTAS_INGLESAS, key=len, reverse=True)
        notas_patron = "|".join(re.escape(n) for n in notas)
        extensiones_patron = "|".join(re.escape(e) for e in cls.EXTENSIONES)

        # Alteraciones opcionales: ## y bb DEBEN ir antes que # y b para que
        # el motor regex las consuma como unidad y no deje colgado un #/b.
        # Slash chord opcional: / + nota base (con alteraciones opcionales).
        alteracion = r"(?:##|#|bb|b)?"
        slash_nota = rf"(?:{notas_patron}){alteracion}"

        # Fronteras:
        # - (?<![A-Za-z]) : no precedido por una letra (evita 'PalAB' matchee 'AB').
        # - (?![A-Za-z])  : no seguido por una letra (permite #, /, números, etc.).
        # Esto es más robusto que \b porque # y / no son caracteres de palabra.
        patron = rf"(?<![A-Za-z])((?:{notas_patron}){alteracion}(?:{extensiones_patron})?(?:/{slash_nota})?)(?![A-Za-z])"
        cls._PATRON_ACORDES = re.compile(patron, re.IGNORECASE)
        return cls._PATRON_ACORDES

    def __init__(self, umbral_palabra: int = 3):
        self.umbral_palabra = umbral_palabra
        self._patron = self._compilar_patron()

    # ------------------------------------------------------------------
    # Utilidades
    # ------------------------------------------------------------------

    def es_linea_de_acordes(self, linea: str) -> bool:
        """
        Decide si una línea es puramente una línea de acordes.

        Criterios:
        - No está vacía.
        - Cada token no vacío coincide con un acorde válido.
        - No contiene signos de puntuación que indiquen letra (como ?, !, .).
        """
        if not linea or not linea.strip():
            return False

        # Descartar líneas con signos de puntuación típicos de letra.
        if re.search(r"[.!?;:,]", linea):
            return False

        tokens = linea.split()
        if not tokens:
            return False

        for token in tokens:
            # Los paréntesis de repetición (Bis) no son acordes.
            token_limpio = token.strip("()[]")
            if not token_limpio:
                continue
            if not self._patron.fullmatch(token_limpio):
                return False

        return True

    def extraer_acordes_de_linea(self, linea: str) -> List[AcordePosicionado]:
        """Extrae acordes de una línea junto con su posición de inicio."""
        acordes: List[AcordePosicionado] = []
        for match in self._patron.finditer(linea):
            acordes.append(AcordePosicionado(
                acorde=match.group(1),
                posicion=match.start(1),
            ))
        return acordes

    def normalizar_acorde(self, acorde: str) -> str:
        """Normaliza la capitalización del acorde ( primera letra mayúscula )."""
        if not acorde:
            return acorde
        return acorde[0].upper() + acorde[1:].lower()

    # ------------------------------------------------------------------
    # Parseo principal
    # ------------------------------------------------------------------

    def parsear_cancion_completa(self, texto: str) -> List[LineaCancion]:
        """
        Parsea el texto completo de una canción.

        Empareja líneas de acordes con la siguiente línea de letra.
        Si una línea de acordes no va seguida de letra, se emite como línea
        de acordes suelta.
        """
        lineas = texto.splitlines()
        resultado: List[LineaCancion] = []
        i = 0
        n = len(lineas)

        while i < n:
            linea = lineas[i]

            if not linea.strip():
                resultado.append(LineaCancion(tipo="vacía"))
                i += 1
                continue

            # Secciones como [Estribillo]
            if linea.strip().startswith("[") and linea.strip().endswith("]"):
                resultado.append(LineaCancion(tipo="sección", texto=linea.strip()))
                i += 1
                continue

            if self.es_linea_de_acordes(linea):
                acordes = self.extraer_acordes_de_linea(linea)

                # Mira si la siguiente línea es letra.
                siguiente = lineas[i + 1] if i + 1 < n else None
                if siguiente is not None and not self.es_linea_de_acordes(siguiente) and siguiente.strip():
                    # Emparejar acordes + letra.
                    resultado.append(LineaCancion(
                        tipo="acordes_letra",
                        acordes=acordes,
                        letra=siguiente,
                    ))
                    i += 2
                else:
                    # Línea de acordes sin letra asociada.
                    resultado.append(LineaCancion(
                        tipo="acordes",
                        acordes=acordes,
                    ))
                    i += 1
            else:
                # Línea de letra suelta (sin acordes encima).
                resultado.append(LineaCancion(tipo="letra", letra=linea))
                i += 1

        return resultado

    def detectar_tono(self, estructura: List[LineaCancion]) -> str:
        """
        Detecta el acorde más frecuente como aproximación de tono.

        Nota: esto devuelve el acorde más repetido, no necesariamente la
        tónica. Para una detección musical real se necesitaría análisis
        funcional (tónica/dominante).
        """
        from collections import Counter

        contador: Counter[str] = Counter()
        for linea in estructura:
            for acorde_info in linea.acordes:
                contador[self.normalizar_acorde(acorde_info.acorde)] += 1

        if not contador:
            return "No detectado"
        return contador.most_common(1)[0][0]

    # ------------------------------------------------------------------
    # Generación HTML
    # ------------------------------------------------------------------

    def generar_html_visual(self, estructura: List[LineaCancion]) -> str:
        """
        Genera HTML donde los acordes aparecen encima de la letra,
        manteniendo la posición exacta mediante fuente monoespaciada y
        posicionamiento relativo en unidades 'ch'.
        """
        lineas_html: List[str] = []
        lineas_html.append('<div class="cancion-con-acordes">')

        for linea in estructura:
            if linea.tipo == "vacía":
                lineas_html.append('<div class="linea-vacia"></div>')

            elif linea.tipo == "sección":
                escapado = html.escape(linea.texto)
                lineas_html.append(f'<div class="seccion">{escapado}</div>')

            elif linea.tipo == "letra":
                escapado = html.escape(linea.letra)
                lineas_html.append(f'<div class="letra-solo">{escapado}</div>')

            elif linea.tipo == "acordes":
                acordes_html = " ".join(
                    html.escape(self.normalizar_acorde(a.acorde))
                    for a in linea.acordes
                )
                lineas_html.append(f'<div class="linea-acordes-suelta">{acordes_html}</div>')

            elif linea.tipo == "acordes_letra":
                lineas_html.append('<div class="bloque-acordes-letra">')
                lineas_html.append('  <div class="linea-acordes">')

                # Calcular el ancho necesario para que el acorde más lejano
                # encaje exactamente. Usamos espacios no rompibles al final de
                # la letra para mantener la posición sin modificar el texto visible.
                max_fin = max(
                    (a.posicion + len(a.acorde) for a in linea.acordes),
                    default=0,
                )
                ancho_letra = len(linea.letra)
                padding = max(0, max_fin - ancho_letra)
                letra_visual = linea.letra + ("\u00a0" * padding)

                for acorde_info in linea.acordes:
                    left = acorde_info.posicion
                    acorde_esc = html.escape(self.normalizar_acorde(acorde_info.acorde))
                    lineas_html.append(
                        f'    <span class="acorde" style="left:{left}ch">{acorde_esc}</span>'
                    )

                lineas_html.append('  </div>')
                letra_esc = html.escape(letra_visual)
                lineas_html.append(f'  <div class="linea-letra">{letra_esc}</div>')
                lineas_html.append('</div>')

        lineas_html.append('</div>')
        return "\n".join(lineas_html)

    def generar_html_completo(self, estructura: List[LineaCancion]) -> str:
        """Genera un documento HTML completo con CSS para visualización exacta."""
        body = self.generar_html_visual(estructura)
        return f"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<title>Canción con acordes</title>
<style>
.cancion-con-acordes {{
    font-family: "Courier New", Courier, monospace;
    line-height: 1.6;
    white-space: pre;
}}
.bloque-acordes-letra {{
    position: relative;
    margin-bottom: 0.2em;
}}
.linea-acordes {{
    position: relative;
    height: 1.2em;
}}
.acorde {{
    position: absolute;
    top: 0;
    color: #c0392b;
    font-weight: bold;
}}
.linea-letra {{
    color: #2c3e50;
}}
.seccion {{
    font-weight: bold;
    margin-top: 1em;
    color: #2980b9;
}}
</style>
</head>
<body>
{body}
</body>
</html>"""


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_posicionamiento_exacto():
    texto_ejemplo = """PREPARAD EL CAMINO
escuchar

SOL   Lam        Sim                 DO          RE7
PREPARAD EL CAMINO AL SEÑOR
SOL            Lam            Sim        DO   RE7   SOL
Y ESCUCHAD LA PALABRA DE DIOS.(Bis)
SOL Mim
Voz que clama en el desierto:"""

    parser = AcordesParser()
    estructura = parser.parsear_cancion_completa(texto_ejemplo)

    # 1. No debe detectar la palabra "LA" como acorde.
    for linea in estructura:
        for acorde in linea.acordes:
            assert acorde.acorde.upper() != "LA", \
                f"Falso positivo: {acorde.acorde} en letra"

    # 2. La letra debe conservarse exacta.
    letras = [l.letra for l in estructura if l.tipo == "acordes_letra"]
    assert "Y ESCUCHAD LA PALABRA DE DIOS.(Bis)" in letras, \
        f"Letra corrompida: {letras}"

    # 3. Posiciones sobre letra (no negativas).
    for linea in estructura:
        if linea.tipo == "acordes_letra":
            for acorde in linea.acordes:
                assert acorde.posicion >= 0, \
                    f"Posición negativa para {acorde.acorde}"

    print("✓ test_posicionamiento_exacto pasado")


def test_extensiones_y_slash():
    parser = AcordesParser()
    casos = [
        "Do Do# Reb Re# Solb Sol#",
        "C C# Db D# Gb G#",
        "Do7 Dom7 DoM Domaj7",
        "C7 Cm7 CM Cmaj7",
        "Do/Sol Re/La C/E D/F#",
        "Cadd9 Csus4 Ddim Eaug Fm9 G11 A13",
    ]
    for caso in casos:
        assert parser.es_linea_de_acordes(caso), f"No detectó acordes: {caso}"

    print("✓ test_extensiones_y_slash pasado")


def test_html_sin_xss():
    texto = "SOL\n<script>alert(1)</script>"
    html_out = AcordesParser().generar_html_completo(
        AcordesParser().parsear_cancion_completa(texto)
    )
    assert "<script>" not in html_out
    assert "&lt;script&gt;" in html_out
    print("✓ test_html_sin_xss pasado")


def test_posicion_html_exacto():
    """Verifica que cada span de acorde tenga left == posicion del acorde."""
    import re as _re
    texto = "SOL   Lam        Sim                 DO          RE7\nPREPARAD EL CAMINO AL SEÑOR"
    estructura = AcordesParser().parsear_cancion_completa(texto)
    html_out = AcordesParser().generar_html_visual(estructura)

    spans = list(_re.finditer(r'<span class="acorde" style="left:(\d+)ch">([^<]+)</span>', html_out))
    acordes = [a for l in estructura for a in l.acordes]
    assert len(spans) == len(acordes)
    for span, acorde in zip(spans, acordes):
        assert int(span.group(1)) == acorde.posicion, \
            f"{acorde.acorde}: esperado {acorde.posicion}, got {span.group(1)}"
    print("✓ test_posicion_html_exacto pasado")


def demo():
    texto_ejemplo = """PREPARAD EL CAMINO
escuchar

SOL   Lam        Sim                 DO          RE7
PREPARAD EL CAMINO AL SEÑOR
SOL            Lam            Sim        DO   RE7   SOL
Y ESCUCHAD LA PALABRA DE DIOS.(Bis)
SOL Mim
Voz que clama en el desierto:"""

    parser = AcordesParser()
    estructura = parser.parsear_cancion_completa(texto_ejemplo)

    print("=== ESTRUCTURA JSON ===")
    print(json.dumps(
        [
            {
                "tipo": l.tipo,
                "acordes": [{"acorde": a.acorde, "posicion": a.posicion} for a in l.acordes],
                "letra": l.letra,
                "texto": l.texto,
            }
            for l in estructura
        ],
        indent=2,
        ensure_ascii=False,
    ))
    print()
    print("=== TONO DETECTADO ===")
    print(parser.detectar_tono(estructura))
    print()
    print("=== HTML VISUAL ===")
    print(parser.generar_html_visual(estructura))


if __name__ == "__main__":
    test_posicionamiento_exacto()
    test_extensiones_y_slash()
    test_html_sin_xss()
    test_posicion_html_exacto()
    print()
    demo()
