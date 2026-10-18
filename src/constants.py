"""Constantes compartidas del proyecto CCE-M5-Web-Presentaciones."""

from pathlib import Path

from pptx.util import Cm

PROJECT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_DIR / "data"
DB_PATH = DATA_DIR / "db.sqlite3"
LEMA_DIR = DATA_DIR / "lemas"
ILUSTRACIONES_DIR = DATA_DIR / "ilustraciones"
OUTPUT_DIR_HTML = PROJECT_DIR / "presentaciones_html"
OUTPUT_DIR_PPTX = PROJECT_DIR / "presentaciones"
BORRADOR_DIR = PROJECT_DIR / "borradores"
TEMPLATE_PATH = DATA_DIR / "templates" / "274_Domingo_21_06_2026.pptx"

# 4:3 en cm reales: 33,87 cm × 25,4025 cm
SLIDE_WIDTH_INCHES = float(Cm(33.87)) / 914400
SLIDE_HEIGHT_INCHES = float(Cm(25.4025)) / 914400

MOMENTOS_ES = [
    "Entrada",
    "Perdón",
    "Gloria",
    "Salmo",
    "Aleluya",
    "Ofertorio",
    "Santo",
    "Padre Nuestro",
    "Paz",
    "Comunión",
    "Canto a María",
    "Despedida",
]

MOMENTOS_KEY = [
    "entrada",
    "perdon",
    "gloria",
    "salmo",
    "aleluya",
    "ofertorio",
    "santo",
    "padre_nuestro",
    "paz",
    "comunion",
    "maria",
    "despedida",
]

MOMENTO_A_KEY = dict(zip(MOMENTOS_ES, MOMENTOS_KEY, strict=False))

# Colores litúrgicos (fondos degradados)
COLORES_LITURGICOS = {
    "verde": {"from": "#e8f5e9", "to": "#c8e6c9", "acento": "#2e7d32"},
    "blanco": {"from": "#fffdf5", "to": "#f5f5f5", "acento": "#5d4037"},
    "rojo": {"from": "#ffebee", "to": "#ffcdd2", "acento": "#c62828"},
    "morado": {"from": "#f3e5f5", "to": "#e1bee7", "acento": "#6a1b9a"},
    "rosa": {"from": "#fce4ec", "to": "#f8bbd0", "acento": "#ad1457"},
    "negro": {"from": "#eeeeee", "to": "#bdbdbd", "acento": "#212121"},
}

# Rutas preferidas de ilustración por tipo de slide
ILUSTRACIONES_PREFERIDAS = {
    "portada": ["comunidad_oracion.svg", "corazon.svg"],
    "entrada": ["camino.svg", "corazon.svg"],
    "perdon": ["corazon.svg", "comunidad_oracion.svg"],
    "gloria": ["corazon.svg"],
    "salmo": ["biblia_abierta.svg", "corazon.svg"],
    "aleluya": ["corazon.svg", "camino.svg"],
    "primera_lectura": ["biblia_abierta.png", "escuchar.png"],
    "segunda_lectura": ["biblia_abierta.svg", "comunidad_oracion.svg"],
    "evangelio": ["comunidad_oracion.svg", "corazon.svg"],
    "credo": ["comunidad_oracion.svg", "corazon.svg"],
    "ofertorio": ["pan_vino.png", "pan_vino.svg", "corazon.svg"],
    "santo": ["corazon.svg", "pan_vino.svg"],
    "padre_nuestro": ["comunidad_oracion.svg", "corazon.svg"],
    "paz": ["comunidad_oracion.svg", "corazon.svg"],
    "comunion": ["pan_vino.png", "pan_vino.svg", "comunidad_oracion.svg"],
    "maria": ["comunidad_oracion.svg", "corazon.svg"],
    "despedida": ["camino.svg", "comunidad_oracion.svg"],
}

TEXTOS_LITURGICOS = {
    "acto_penitencial": (
        "Yo confieso ante Dios todopoderoso\n"
        "y ante vosotros, hermanos,\n"
        "que he pecado mucho de pensamiento, palabra, obra y omisión:\n"
        "por mi culpa, por mi culpa, por mi gran culpa.\n\n"
        "Por eso ruego a Santa María, siempre Virgen,\n"
        "a los ángeles, a los santos y a vosotros, hermanos,\n"
        "que intercedáis por mí ante Dios, nuestro Señor."
    ),
    "bendicion_agua": "(Se bendice el agua y se asperja sobre la asamblea)",
    "gloria": (
        "Gloria a Dios en el cielo,\n"
        "y en la tierra paz a los hombres que ama el Señor.\n"
        "Te alabamos, te bendecimos, te adoramos, te glorificamos.\n"
        "Te damos gracias, Señor Dios, Rey celestial."
    ),
    "credo": (
        "Creo en Dios, Padre todopoderoso, creador del cielo y de la tierra.\n"
        "Creo en Jesucristo, su único Hijo, nuestro Señor, que fue concebido por obra y gracia del Espíritu Santo; "
        "nació de Santa María Virgen; padeció bajo el poder de Poncio Pilato; fue crucificado, muerto y sepultado; "
        "descendió a los infiernos; al tercer día resucitó de entre los muertos; subió a los cielos y está sentado a la derecha de Dios Padre todopoderoso.\n"
        "Desde allí ha de venir a juzgar a vivos y muertos.\n"
        "Creo en el Espíritu Santo, la santa Iglesia católica, la comunión de los santos, el perdón de los pecados, "
        "la resurrección de la carne y la vida eterna. Amén."
    ),
    "santo": (
        "Santo, santo, santo es el Señor,\n"
        "Dios del universo.\n"
        "Llenos están el cielo y la tierra de tu gloria.\n"
        "Hosanna en el cielo.\n"
        "Bendito el que viene en nombre del Señor.\n"
        "Hosanna en el cielo."
    ),
    "padre_nuestro": (
        "Padre nuestro, que estás en el cielo,\n"
        "santificado sea tu nombre;\n"
        "venga a nosotros tu reino;\n"
        "hágase tu voluntad en la tierra como en el cielo.\n\n"
        "Danos hoy nuestro pan de cada día;\n"
        "perdona nuestras ofensas,\n"
        "como también nosotros perdonamos a los que nos ofenden;\n"
        "no nos dejes caer en la tentación,\n"
        "y líbranos del mal."
    ),
    "paz": (
        "Señor Jesucristo, que dijiste a tus apóstoles:\n"
        "«La paz os dejo, mi paz os doy»,\n"
        "no tengas en cuenta nuestros pecados,\n"
        "sino la fe de tu Iglesia,\n"
        "y conforme a tu palabra concédele la paz y la unidad.\n\n"
        "Tú que vives y reinas por los siglos de los siglos. Amén.\n\n"
        "La paz del Señor esté siempre con vosotros."
    ),
    "maria": (
        "Dios te salve, María;\n"
        "llena eres de gracia;\n"
        "el Señor es contigo.\n"
        "Bendita tú eres entre todas las mujeres,\n"
        "y bendito es el fruto de tu vientre, Jesús.\n\n"
        "Santa María, Madre de Dios,\n"
        "ruega por nosotros, pecadores,\n"
        "ahora y en la hora de nuestra muerte. Amén."
    ),
    "despedida": (
        "Que el Señor nos bendiga, nos guarde de todo mal\n" "y nos lleve a la vida eterna. Amén."
    ),
}

LEMA_CURSO = "Somos uno"
URL_LEMA_CURSO = "https://escolappios.es/somos-uno-lema-del-curso-26-27/"
