#!/usr/bin/env python3
"""
Generador de presentaciones PPTX para la asamblea (sin acordes)
Formato 16:9 basado en 274 Domingo 21 06 2026.pptx
"""

from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE
from datetime import datetime
import sqlite3
from pathlib import Path

PROJECT_DIR = Path.home() / "proyectos" / "CCE-M5-Web-Presentaciones"
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

class GeneradorPPTX:
    def __init__(self):
        self.prs = Presentation()
        # Configurar dimensiones 16:9 (13.333 x 7.5 pulgadas)
        self.prs.slide_width = Inches(13.333)
        self.prs.slide_height = Inches(7.5)
        
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        
    def crear_diapositiva_titulo(self, titulo, subtitulo, color_fondo='verde'):
        """Crea diapositiva de titulo"""
        blank_layout = self.prs.slide_layouts[6]  # Blank layout
        slide = self.prs.slides.add_slide(blank_layout)
        
        # Fondo
        background = slide.background
        fill = background.fill
        fill.solid()
        fill.fore_color.rgb = COLORES_LITURGICOS.get(color_fondo, COLORES_LITURGICOS['verde'])
        
        # Titulo
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
        
        # Subtitulo
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
        """Crea diapositiva de lectura"""
        blank_layout = self.prs.slide_layouts[6]
        slide = self.prs.slides.add_slide(blank_layout)
        
        # Fondo blanco
        background = slide.background
        fill = background.fill
        fill.solid()
        fill.fore_color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
        
        # Titulo de la lectura
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
        p.text = texto[:500] + "..." if len(texto) > 500 else texto
        p.font.size = Pt(18)
        p.font.color.rgb = RGBColor(0x33, 0x33, 0x33)
        p.line_spacing = 1.5
        
        return slide
    
    def crear_diapositiva_cancion(self, titulo, letra, momento, color_fondo='blanco'):
        """Crea diapositiva de cancion (sin acordes)"""
        blank_layout = self.prs.slide_layouts[6]
        slide = self.prs.slides.add_slide(blank_layout)
        
        # Fondo
        background = slide.background
        fill = background.fill
        fill.solid()
        fill.fore_color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
        
        # Titulo del momento
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
        
        # Titulo de la cancion
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
        p.text = letra[:800] + "..." if len(letra) > 800 else letra
        p.font.size = Pt(20)
        p.font.color.rgb = RGBColor(0x33, 0x33, 0x33)
        p.line_spacing = 1.5
        p.alignment = PP_ALIGN.CENTER
        
        return slide
    
    def generar_presentacion(self, fecha_domingo, lectura_id, canciones_ids):
        """
        Genera una presentacion completa.
        
        Args:
            fecha_domingo: Fecha del domingo (YYYY-MM-DD)
            lectura_id: ID de la lectura en la DB
            canciones_ids: Lista de IDs de canciones por momento
        """
        conn = sqlite3.connect(str(DB_PATH))
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
            print(f"ERROR: No se encontró lectura {lectura_id}")
            return None
        
        (celebracion, temporada, color, 
         p_cita, p_texto, s_cita, s_antifona, s_texto,
         seg_cita, seg_texto, e_cita, e_texto) = lectura
        
        # Portada
        self.crear_diapositiva_titulo(
            celebracion or "Celebración del Domingo",
            fecha_domingo,
            color or 'verde'
        )
        
        # Primera lectura
        if p_texto:
            self.crear_diapositiva_lectura(
                "Primera Lectura",
                p_cita or "",
                p_texto,
                color or 'verde'
            )
        
        # Salmo
        if s_texto:
            self.crear_diapositiva_lectura(
                "Salmo Responsorial",
                s_cita or "",
                f"Antífona: {s_antifona or ''}\n\n{s_texto}",
                color or 'verde'
            )
        
        # Segunda lectura
        if seg_texto:
            self.crear_diapositiva_lectura(
                "Segunda Lectura",
                seg_cita or "",
                seg_texto,
                color or 'verde'
            )
        
        # Evangelio
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
                cursor.execute('SELECT titulo, letra_sin_acordes FROM canciones WHERE id = ?', (cancion_id,))
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
        
        conn.close()
        
        print(f"✅ Presentación generada: {filepath}")
        return filepath

def probar_generador():
    """Prueba el generador con datos mock"""
    print("=" * 70)
    print("GENERADOR DE PRESENTACIONES PPTX")
    print("=" * 70)
    
    generador = GeneradorPPTX()
    
    # Crear presentacion de prueba
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    
    # Portada
    generador.crear_diapositiva_titulo(
        "Domingo XXIV del Tiempo Ordinario",
        "14 de septiembre de 2026",
        'verde'
    )
    
    # Diapositiva de prueba
    generador.crear_diapositiva_cancion(
        "PREPARAD EL CAMINO",
        "PREPARAD EL CAMINO AL SEÑOR\nY ESCUCHAD LA PALABRA DE DIOS.(Bis)\n\nVoz que clama en el desierto:\npreparad los caminos de Dios,\ndesterrad la mentira por siempre,\npreparad los caminos de Dios(Bis)",
        "Entrada",
        'blanco'
    )
    
    # Guardar
    filepath = OUTPUT_DIR / "prueba_presentacion.pptx"
    generador.prs.save(str(filepath))
    
    print(f"\n✅ Presentación de prueba generada: {filepath}")
    print(f"Dimensiones: 13.333\" x 7.5\" (16:9)")
    print(f"Diapositivas: {len(generador.prs.slides)}")
    print("=" * 70)

if __name__ == "__main__":
    probar_generador()
