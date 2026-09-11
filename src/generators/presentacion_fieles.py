#!/usr/bin/env python3
"""
Generador de presentaciones PPTX para la asamblea (sin acordes)
Formato 16:9 basado en 274 Domingo 21 06 2026.pptx

MEJORAS APLICADAS (basado en análisis de OpenCode + Kimi):
- Logging profesional
- Manejo seguro de conexiones SQLite
- Validación de datos antes de generar
- Templates reutilizables
- Mejor manejo de errores
"""

from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
import sqlite3
import logging
from pathlib import Path

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuracion
PROJECT_DIR = Path(__file__).parent.parent.parent
DB_PATH = PROJECT_DIR / "data" / "db.sqlite3"
OUTPUT_DIR = PROJECT_DIR / "presentaciones"

# Colores liturgicos
COLORES_LITURGICOS = {
    'verde': RGBColor(0x4C, 0xAF, 0x50),
    'violeta': RGBColor(0x9C, 0x27, 0xB0),
    'blanco': RGBColor(0xFF, 0xFF, 0xFF),
    'rojo': RGBColor(0xF4, 0x43, 0x36),
    'rosa': RGBColor(0xE9, 0x1E, 0x63),
    'negro': RGBColor(0x21, 0x21, 0x21)
}

# Dimensiones 16:9
SLIDE_WIDTH = Inches(13.333)
SLIDE_HEIGHT = Inches(7.5)


class GeneradorPPTX:
    """Generador de presentaciones litúrgicas en formato 16:9."""
    
    def __init__(self, db_path=None):
        self.db_path = db_path or DB_PATH
        self.prs = Presentation()
        self.prs.slide_width = SLIDE_WIDTH
        self.prs.slide_height = SLIDE_HEIGHT
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    def _get_connection(self):
        """Obtiene conexión a la base de datos."""
        return sqlite3.connect(str(self.db_path))
    
    def crear_diapositiva_titulo(self, titulo, subtitulo, color_fondo='verde'):
        """Crea diapositiva de título con color litúrgico."""
        slide = self.prs.slides.add_slide(self.prs.slide_layouts[6])
        
        # Fondo
        background = slide.background
        fill = background.fill
        fill.solid()
        fill.fore_color.rgb = COLORES_LITURGICOS.get(color_fondo, COLORES_LITURGICOS['verde'])
        
        # Título principal
        left = Inches(1)
        top = Inches(2.5)
        width = Inches(11.333)
        height = Inches(1.5)
        
        textbox = slide.shapes.add_textbox(left, top, width, height)
        tf = textbox.text_frame
        p = tf.paragraphs[0]
        p.text = titulo
        p.font.size = Pt(54)
        p.font.bold = True
        p.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
        p.alignment = PP_ALIGN.CENTER
        
        # Subtítulo
        top = Inches(4.2)
        textbox = slide.shapes.add_textbox(left, top, width, height)
        tf = textbox.text_frame
        p = tf.paragraphs[0]
        p.text = subtitulo
        p.font.size = Pt(28)
        p.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
        p.alignment = PP_ALIGN.CENTER
        
        return slide
    
    def crear_diapositiva_lectura(self, titulo, cita, texto, color_fondo='blanco'):
        """Crea diapositiva de lectura."""
        slide = self.prs.slides.add_slide(self.prs.slide_layouts[6])
        
        # Fondo blanco
        background = slide.background
        fill = background.fill
        fill.solid()
        fill.fore_color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
        
        # Título de la lectura
        left = Inches(0.5)
        top = Inches(0.3)
        width = Inches(12.333)
        height = Inches(0.6)
        
        textbox = slide.shapes.add_textbox(left, top, width, height)
        tf = textbox.text_frame
        p = tf.paragraphs[0]
        p.text = titulo
        p.font.size = Pt(32)
        p.font.bold = True
        p.font.color.rgb = COLORES_LITURGICOS.get(color_fondo, COLORES_LITURGICOS['verde'])
        
        # Cita
        top = Inches(1.0)
        textbox = slide.shapes.add_textbox(left, top, width, height)
        tf = textbox.text_frame
        p = tf.paragraphs[0]
        p.text = cita
        p.font.size = Pt(20)
        p.font.italic = True
        p.font.color.rgb = RGBColor(0x66, 0x66, 0x66)
        
        # Texto de la lectura
        top = Inches(1.8)
        height = Inches(5.0)
        textbox = slide.shapes.add_textbox(left, top, width, height)
        tf = textbox.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        
        # Limitar texto para que quepa en la diapositiva
        texto_limpio = texto[:500] + "..." if len(texto) > 500 else texto
        p.text = texto_limpio
        p.font.size = Pt(18)
        p.font.color.rgb = RGBColor(0x33, 0x33, 0x33)
        p.line_spacing = 1.5
        
        return slide
    
    def crear_diapositiva_cancion(self, titulo, letra, momento, color_fondo='blanco'):
        """Crea diapositiva de canción sin acordes."""
        slide = self.prs.slides.add_slide(self.prs.slide_layouts[6])
        
        # Fondo blanco
        background = slide.background
        fill = background.fill
        fill.solid()
        fill.fore_color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
        
        # Título del momento
        left = Inches(0.5)
        top = Inches(0.3)
        width = Inches(12.333)
        height = Inches(0.5)
        
        textbox = slide.shapes.add_textbox(left, top, width, height)
        tf = textbox.text_frame
        p = tf.paragraphs[0]
        p.text = momento.upper()
        p.font.size = Pt(24)
        p.font.bold = True
        p.font.color.rgb = RGBColor(0x99, 0x99, 0x99)
        
        # Título de la canción
        top = Inches(0.9)
        textbox = slide.shapes.add_textbox(left, top, width, height)
        tf = textbox.text_frame
        p = tf.paragraphs[0]
        p.text = titulo
        p.font.size = Pt(36)
        p.font.bold = True
        p.font.color.rgb = RGBColor(0x33, 0x33, 0x33)
        
        # Letra
        top = Inches(1.8)
        height = Inches(5.2)
        textbox = slide.shapes.add_textbox(left, top, width, height)
        tf = textbox.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        
        # Limitar letra para que quepa
        letra_limpia = letra[:800] + "..." if len(letra) > 800 else letra
        p.text = letra_limpia
        p.font.size = Pt(20)
        p.font.color.rgb = RGBColor(0x33, 0x33, 0x33)
        p.line_spacing = 1.5
        p.alignment = PP_ALIGN.CENTER
        
        return slide
    
    def generar_presentacion(self, fecha_domingo, lectura_id, canciones_ids):
        """Genera una presentación completa."""
        logger.info(f"Generando presentación para: {fecha_domingo}")
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Obtener lecturas
                cursor.execute('''
                    SELECT celebracion, temporada, color_liturgico,
                           primera_lectura_cita, primera_lectura_texto,
                           salmo_cita, salmo_antifona, salmo_texto,
                           segunda_lectura_cita, segunda_lectura_texto,
                           evangelio_cita, evangelio_texto
                    FROM lecturas WHERE id = ?
                ''', (lectura_id,))
                
                lectura = cursor.fetchone()
                if not lectura:
                    logger.error(f"No se encontró lectura {lectura_id}")
                    return None
                
                (celebracion, temporada, color, 
                 p_cita, p_texto, s_cita, s_antifona, s_texto,
                 seg_cita, seg_texto, e_cita, e_texto) = lectura
                
                # Validar datos mínimos
                if not celebracion:
                    celebracion = "Celebración del Domingo"
                
                # Portada
                self.crear_diapositiva_titulo(
                    celebracion,
                    fecha_domingo,
                    color or 'verde'
                )
                
                # Lecturas
                if p_texto:
                    self.crear_diapositiva_lectura(
                        "Primera Lectura",
                        p_cita or "",
                        p_texto,
                        color or 'verde'
                    )
                
                if s_texto:
                    self.crear_diapositiva_lectura(
                        "Salmo Responsorial",
                        s_cita or "",
                        f"Antífona: {s_antifona or ''}\n\n{s_texto}",
                        color or 'verde'
                    )
                
                if seg_texto:
                    self.crear_diapositiva_lectura(
                        "Segunda Lectura",
                        seg_cita or "",
                        seg_texto,
                        color or 'verde'
                    )
                
                if e_texto:
                    self.crear_diapositiva_lectura(
                        "Evangelio",
                        e_cita or "",
                        e_texto,
                        color or 'verde'
                    )
                
                # Canciones
                momentos = ['entrada', 'perdon', 'gloria', 'salmo', 'aleluya', 
                           'ofertorio', 'santo', 'padre_nuestro', 'paz', 
                           'comunion', 'maria', 'despedida']
                
                for momento in momentos:
                    if momento in canciones_ids:
                        cancion_id = canciones_ids[momento]
                        cursor.execute(
                            'SELECT titulo, letra_sin_acordes FROM canciones WHERE id = ?',
                            (cancion_id,)
                        )
                        cancion = cursor.fetchone()
                        
                        if cancion:
                            titulo, letra = cancion
                            self.crear_diapositiva_cancion(
                                titulo or "Canción",
                                letra or "",
                                momento,
                                'blanco'
                            )
                
                # Guardar
                filename = f"{fecha_domingo}_presentacion.pptx"
                filepath = OUTPUT_DIR / filename
                self.prs.save(str(filepath))
                
                logger.info(f"✅ Presentación generada: {filepath}")
                logger.info(f"Diapositivas: {len(self.prs.slides)}")
                return filepath
                
        except sqlite3.Error as e:
            logger.error(f"Error de base de datos: {e}")
            return None
        except Exception as e:
            logger.error(f"Error al generar presentación: {e}")
            return None


def probar_generador():
    """Prueba el generador con datos de ejemplo."""
    logger.info("=" * 70)
    logger.info("GENERADOR DE PRESENTACIONES PPTX")
    logger.info("=" * 70)
    
    generador = GeneradorPPTX()
    
    # Crear presentación de prueba
    generador.crear_diapositiva_titulo(
        "Domingo XXIV del Tiempo Ordinario",
        "14 de septiembre de 2026",
        'verde'
    )
    
    generador.crear_diapositiva_cancion(
        "PREPARAD EL CAMINO",
        "PREPARAD EL CAMINO AL SEÑOR\nY ESCUCHAD LA PALABRA DE DIOS.(Bis)",
        "Entrada",
        'blanco'
    )
    
    # Guardar
    filepath = OUTPUT_DIR / "prueba_presentacion.pptx"
    generador.prs.save(str(filepath))
    
    logger.info(f"\n✅ Presentación de prueba: {filepath}")
    logger.info(f"Dimensiones: 13.333\" x 7.5\" (16:9)")
    logger.info(f"Diapositivas: {len(generador.prs.slides)}")
    logger.info("=" * 70)


if __name__ == "__main__":
    probar_generador()
