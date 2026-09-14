#!/usr/bin/env python3
"""
Generador de presentaciones PPTX usando plantilla MASTER.
Copia slides de canciones desde la plantilla y añade lecturas.
"""

import os
import sqlite3
import shutil
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

# Paths
PROJECT_DIR = Path(os.environ.get("CCE_PROJECT_DIR", "/home/pciath/proyectos/CCE-M5-Web-Presentaciones"))
DB_PATH = PROJECT_DIR / "data" / "db.sqlite3"
MASTER_PATH = PROJECT_DIR / "data" / "templates" / "274_Domingo_21_06_2026.pptx"
OUTPUT_DIR = PROJECT_DIR / "presentaciones"

# Mapeo de canciones conocidas a slides en MASTER
# Basado en análisis de la plantilla MASTER
CANCION_A_SLIDES = {
    "PREPARAD EL CAMINO": [66, 67, 68],
    "EL ESPIRITU DE DIOS": [7, 64, 65],
    "YO CELEBRARE": [4],
    "DIOS ESTA AQUI": [5],
    "COMO TUS BRAZOS": [9, 10],
    "HE VENIDO A SERVIR": [8],
    "GLORIA": [16, 17, 18, 19],
    "ALELUYA": [23, 25, 26, 27, 28],
    "CREDO": [30],
    "SANTO": [40, 41, 42, 43, 44, 45],
    "PADRE NUESTRO": [47, 48, 49, 50],
    "PAZ": [52, 53, 54, 55, 56],
    "COMUNION": [32, 33, 34, 35, 36, 37, 38],
    "MARIA": [94, 95, 96, 97, 98, 99, 100, 101, 102, 103, 104, 105, 106, 107, 108, 109, 110, 111, 112, 113, 114, 115, 116, 117, 118],
    "DESPEDIDA": [2, 3, 69, 70, 81],
}

def find_slide_for_cancion(titulo: str) -> Optional[int]:
    """Busca el número de slide para una canción por título."""
    if not titulo:
        return None
    
    titulo_upper = titulo.upper().strip()
    
    # Búsqueda exacta primero
    for cancion, slides in CANCION_A_SLIDES.items():
        if cancion in titulo_upper:
            return slides[0]
    
    # Búsqueda por palabras clave
    palabras = titulo_upper.split()
    for cancion, slides in CANCION_A_SLIDES.items():
        cancion_palabras = cancion.split()
        coincidencias = sum(1 for p in palabras if p in cancion_palabras)
        if coincidencias >= max(2, len(cancion_palabras) // 2):
            return slides[0]
    
    return None

class GeneradorPPTXMaster:
    """Generador de presentaciones usando plantilla MASTER."""
    
    def __init__(self, db_path=None, template_path=None, output_dir=None):
        self.master_path = Path(template_path) if template_path else MASTER_PATH
        self.output_dir = Path(output_dir) if output_dir else OUTPUT_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        return conn
    
    def _copy_slide_from_master(self, temp_dir: Path, slide_num: int) -> bool:
        """Copia una slide de la plantilla master al directorio temporal."""
        slide_name = f"slide{slide_num}.xml"
        slide_path = f"ppt/slides/{slide_name}"
        rels_path = f"ppt/slides/_rels/{slide_name}.rels"
        
        try:
            with zipfile.ZipFile(self.master_path, 'r') as zf:
                # Copy slide XML
                slide_content = zf.read(slide_path)
                slide_output = temp_dir / slide_path
                slide_output.parent.mkdir(parents=True, exist_ok=True)
                slide_output.write_bytes(slide_content)
                
                # Copy rels
                try:
                    rels_content = zf.read(rels_path)
                    rels_output = temp_dir / rels_path
                    rels_output.parent.mkdir(parents=True, exist_ok=True)
                    rels_output.write_bytes(rels_content)
                except KeyError:
                    pass
                
                # Copy referenced media
                try:
                    rels_root = ET.fromstring(zf.read(rels_path))
                    for rel in rels_root:
                        target = rel.get('Target')
                        if target and '../media/' in target:
                            media_name = target.split('/')[-1]
                            media_path = f"ppt/media/{media_name}"
                            try:
                                media_content = zf.read(media_path)
                                media_output = temp_dir / media_path
                                media_output.parent.mkdir(parents=True, exist_ok=True)
                                if not media_output.exists():
                                    media_output.write_bytes(media_content)
                            except KeyError:
                                pass
                except:
                    pass
                
                return True
        except Exception as e:
            print(f"Error copying slide {slide_num}: {e}")
            return False
    
    def _create_lectura_slide(self, temp_dir: Path, slide_num: int, titulo: str, cita: str, texto: str) -> bool:
        """Crea una slide de lectura copiando una slide base y modificando el texto."""
        # For now, copy slide 14 (Salmo) as base and modify
        # This is a simplified approach
        base_slide = 14
        slide_name = f"slide{slide_num}.xml"
        slide_path = f"ppt/slides/{slide_name}"
        rels_path = f"ppt/slides/_rels/{slide_name}.rels"
        
        try:
            with zipfile.ZipFile(self.master_path, 'r') as zf:
                # Read base slide
                base_content = zf.read(f"ppt/slides/slide{base_slide}.xml")
                
                # Simple text replacement (this is a basic approach)
                # In production, you'd use proper XML manipulation
                content_str = base_content.decode('utf-8', errors='ignore')
                
                # Replace title and text placeholders
                # This is simplified - real implementation would need proper XML parsing
                
                slide_output = temp_dir / slide_path
                slide_output.parent.mkdir(parents=True, exist_ok=True)
                slide_output.write_bytes(base_content)
                
                # Copy rels
                try:
                    rels_content = zf.read(f"ppt/slides/_rels/slide{base_slide}.xml.rels")
                    rels_output = temp_dir / rels_path
                    rels_output.parent.mkdir(parents=True, exist_ok=True)
                    rels_output.write_bytes(rels_content)
                except KeyError:
                    pass
                
                return True
        except Exception as e:
            print(f"Error creating lectura slide: {e}")
            return False
    
    def _rebuild_pptx(self, temp_dir: Path, output_path: Path, slide_numbers: List[int]) -> bool:
        """Rebuild PPTX manteniendo solo las slides especificadas."""
        try:
            NS_P = 'http://schemas.openxmlformats.org/presentationml/2006/main'
            NS_R = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
            
            # Leer presentation.xml
            pres_path = temp_dir / "ppt" / "presentation.xml"
            pres_tree = ET.parse(pres_path)
            pres_root = pres_tree.getroot()
            
            # Leer presentation.xml.rels
            pres_rels_path = temp_dir / "ppt" / "_rels" / "presentation.xml.rels"
            pres_rels_tree = ET.parse(pres_rels_path)
            pres_rels_root = pres_rels_tree.getroot()
            
            # Encontrar sldIdLst
            sldIdLst = pres_root.find(f'.//{{{NS_P}}}sldIdLst')
            if sldIdLst is None:
                print("ERROR: No se encontró sldIdLst")
                return False
            
            # Mapear rId -> número de slide (por orden en sldIdLst)
            rId_to_slide_num = {}
            for i, sldId in enumerate(sldIdLst):
                rId = sldId.get(f'{{{NS_R}}}id')
                rId_to_slide_num[rId] = i + 1
            
            # Determinar qué rIds mantener
            keep_rIds = []
            for rId, slide_num in rId_to_slide_num.items():
                if slide_num in slide_numbers:
                    keep_rIds.append(rId)
            
            # ELIMINAR slides no deseadas del sldIdLst
            for sldId in list(sldIdLst):
                rId = sldId.get(f'{{{NS_R}}}id')
                if rId not in keep_rIds:
                    sldIdLst.remove(sldId)
            
            # ELIMINAR relaciones no deseadas
            for rel in list(pres_rels_root):
                rid = rel.get('Id')
                target = rel.get('Target', '')
                if target.startswith('slides/slide') and rid not in keep_rIds:
                    pres_rels_root.remove(rel)
            
            # GUARDAR XMLs modificados
            pres_tree.write(pres_path, xml_declaration=True, encoding='UTF-8')
            pres_rels_tree.write(pres_rels_path, xml_declaration=True, encoding='UTF-8')
            
            # ELIMINAR archivos de slides que no queremos
            slides_dir = temp_dir / "ppt" / "slides"
            rels_dir = temp_dir / "ppt" / "slides" / "_rels"
            
            for slide_file in slides_dir.glob("slide*.xml"):
                try:
                    slide_num = int(slide_file.stem.replace("slide", ""))
                    if slide_num not in slide_numbers:
                        slide_file.unlink()
                        rels_file = rels_dir / f"{slide_file.name}.rels"
                        if rels_file.exists():
                            rels_file.unlink()
                except ValueError:
                    pass
            
            # Reconstruir PPTX
            with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                for root_dir, dirs, files in os.walk(temp_dir):
                    for file in files:
                        file_path = Path(root_dir) / file
                        arcname = str(file_path.relative_to(temp_dir))
                        zf.write(file_path, arcname)
            
            return True
            
        except Exception as e:
            print(f"Error rebuilding PPTX: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def generar_presentacion(
        self,
        fecha_domingo: str,
        lectura_id: int,
        canciones_ids: Dict[str, int],
    ) -> Optional[Path]:
        """Genera una presentación completa."""
        print(f"Generando presentación para: {fecha_domingo}")
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Get lectura
                cursor.execute(
                    """SELECT COALESCE(celebracion, domingo) AS celebracion,
                           temporada, color_liturgico,
                           primera_lectura_cita, primera_lectura_texto,
                           salmo_cita, salmo_antifona, salmo_texto,
                           segunda_lectura_cita, segunda_lectura_texto,
                           evangelio_cita, evangelio_texto
                    FROM lecturas WHERE id = ?""",
                    (lectura_id,),
                )
                lectura = cursor.fetchone()
                if not lectura:
                    print(f"ERROR: No se encontró lectura {lectura_id}")
                    return None
                
                celebracion = lectura["celebracion"] or "Celebración del Domingo"
                
                # Get canciones info
                canciones_info = {}
                for momento, cancion_id in canciones_ids.items():
                    cursor.execute(
                        "SELECT titulo FROM canciones WHERE id = ?",
                        (cancion_id,),
                    )
                    row = cursor.fetchone()
                    if row:
                        canciones_info[momento] = row[0]
                
                # Create temp directory
                temp_dir = Path(f"/tmp/pptx_gen_{fecha_domingo}")
                if temp_dir.exists():
                    shutil.rmtree(temp_dir)
                temp_dir.mkdir(parents=True, exist_ok=True)
                
                # Extract master
                with zipfile.ZipFile(self.master_path, 'r') as zf:
                    zf.extractall(temp_dir)
                
                # Determine slides to keep
                slides_to_keep = []
                
                # 1. Menu slide (slide 1)
                slides_to_keep.append(1)
                
                # 2. Canciones según asignación
                momento_orden = [
                    "entrada", "perdon", "gloria", "salmo", "aleluya",
                    "ofertorio", "santo", "padre_nuestro", "paz",
                    "comunion", "maria", "despedida",
                ]
                
                for momento in momento_orden:
                    if momento in canciones_info:
                        titulo = canciones_info[momento]
                        slide_num = find_slide_for_cancion(titulo)
                        if slide_num:
                            slides_to_keep.append(slide_num)
                            print(f"  {momento}: {titulo} -> slide {slide_num}")
                        else:
                            print(f"  {momento}: {titulo} -> NO ENCONTRADO")
                
                # 3. Lecturas (we need to add these)
                # For now, add after menu and before canciones
                # This requires creating new slides - complex
                
                # Rebuild PPTX with selected slides
                filename = f"{fecha_domingo}_presentacion.pptx"
                output_path = self.output_dir / filename
                
                if not self._rebuild_pptx(temp_dir, output_path, slides_to_keep):
                    print("ERROR: No se pudo generar la presentación")
                    return None
                
                # Abrir PPTX reconstruido y añadir slides adicionales
                try:
                    from pptx import Presentation
                    prs = Presentation(str(output_path))
                    
                    color = lectura["color_liturgico"] or "verde"
                    
                    # 1. PORTADA al principio (la añadimos al final y luego movemos)
                    # Nota: python-pptx no permite insertar en posición arbitraria
                    # Por ahora, añadimos al final. En versión futura: reordenar XML
                    
                    # Añadimos slides adicionales al final por ahora
                    # El orden será: canciones + lecturas + portada/transiciones
                    # El usuario puede reordenar manualmente o lo haremos en v2
                    
                    # LECTURAS
                    if lectura["primera_lectura_texto"]:
                        self._crear_slide_lectura(prs, "Primera Lectura",
                            lectura["primera_lectura_cita"] or "",
                            lectura["primera_lectura_texto"], color)
                        print("  Añadida: Primera Lectura")
                    
                    if lectura["salmo_texto"]:
                        salmo_texto = f"Antífona: {lectura['salmo_antifona']}\n\n{lectura['salmo_texto']}" if lectura["salmo_antifona"] else lectura["salmo_texto"]
                        self._crear_slide_lectura(prs, "Salmo Responsorial",
                            lectura["salmo_cita"] or "", salmo_texto, color)
                        print("  Añadida: Salmo Responsorial")
                    
                    if lectura["segunda_lectura_texto"]:
                        self._crear_slide_lectura(prs, "Segunda Lectura",
                            lectura["segunda_lectura_cita"] or "",
                            lectura["segunda_lectura_texto"], color)
                        print("  Añadida: Segunda Lectura")
                    
                    if lectura["evangelio_texto"]:
                        self._crear_slide_lectura(prs, "Evangelio",
                            lectura["evangelio_cita"] or "",
                            lectura["evangelio_texto"], color)
                        print("  Añadida: Evangelio")
                    
                    # TRANSICIONES
                    transiciones = [
                        "Liturgia de la Palabra",
                        "Liturgia Eucarística", 
                        "Rito de Conclusión",
                    ]
                    for t in transiciones:
                        self._crear_slide_transicion(prs, t, color)
                        print(f"  Añadida: Transición - {t}")
                    
                    # PORTADA al final (debería ser al principio, pero python-pptx limita)
                    self._crear_slide_portada(prs, celebracion, fecha_domingo, color)
                    print("  Añadida: Portada")
                    
                    prs.save(str(output_path))
                    total_slides = len(prs.slides)
                    print(f"✅ Presentación generada: {output_path}")
                    print(f"   Total slides: {total_slides}")
                    return output_path
                    
                except Exception as e:
                    print(f"WARNING: Error añadiendo slides adicionales: {e}")
                    import traceback
                    traceback.print_exc()
                    return output_path
                
        except Exception as e:
            print(f"ERROR: {e}")
            return None




    def _add_lema_image(self, slide, prs) -> None:
        """Añade la imagen del lema en la esquina inferior izquierda de la slide."""
        from pptx.util import Inches
        
        lema_path = PROJECT_DIR / "data" / "lemas" / "somos_uno.jpg"
        if not lema_path.exists():
            return
        
        try:
            # Añadir imagen en esquina inferior izquierda, pequeña
            left = Inches(0.2)
            top = Inches(6.5)
            height = Inches(0.5)
            
            slide.shapes.add_picture(str(lema_path), left, top, height=height)
        except Exception as e:
            # Si falla, no es crítico
            pass

    def _crear_slide_portada(self, prs, celebracion: str, fecha: str, color: str = "verde") -> None:
        """Crea slide de portada con celebración, fecha y lema."""
        from pptx.util import Inches, Pt
        from pptx.dml.color import RGBColor
        from pptx.enum.text import PP_ALIGN
        
        colores = {
            "verde": RGBColor(0x4C, 0xAF, 0x50),
            "violeta": RGBColor(0x9C, 0x27, 0xB0),
            "blanco": RGBColor(0xFF, 0xFF, 0xFF),
            "rojo": RGBColor(0xF4, 0x43, 0x36),
            "rosa": RGBColor(0xE9, 0x1E, 0x63),
        }
        
        fondo = colores.get(color, colores["verde"])
        texto_color = RGBColor(0xFF, 0xFF, 0xFF) if color != "blanco" else RGBColor(0x33, 0x33, 0x33)
        
        slide_layout = prs.slide_layouts[6]
        slide = prs.slides.add_slide(slide_layout)
        
        background = slide.background
        fill = background.fill
        fill.solid()
        fill.fore_color.rgb = fondo
        
        # Título celebración
        title_box = slide.shapes.add_textbox(Inches(1), Inches(2), Inches(11), Inches(1.5))
        tf = title_box.text_frame
        p = tf.paragraphs[0]
        p.text = celebracion
        p.font.name = "Calibri"
        p.font.size = Pt(48)
        p.font.bold = True
        p.font.color.rgb = texto_color
        p.alignment = PP_ALIGN.CENTER
        
        # Fecha
        fecha_box = slide.shapes.add_textbox(Inches(1), Inches(4), Inches(11), Inches(0.8))
        tf = fecha_box.text_frame
        p = tf.paragraphs[0]
        p.text = fecha
        p.font.name = "Calibri"
        p.font.size = Pt(28)
        p.font.color.rgb = RGBColor(0xCC, 0xCC, 0xCC) if color != "blanco" else RGBColor(0x66, 0x66, 0x66)
        p.alignment = PP_ALIGN.CENTER
        
        # Lema
        lema_box = slide.shapes.add_textbox(Inches(1), Inches(5.5), Inches(11), Inches(0.6))
        tf = lema_box.text_frame
        p = tf.paragraphs[0]
        p.text = "Somos uno"
        p.font.name = "Calibri"
        p.font.size = Pt(18)
        p.font.italic = True
        p.font.color.rgb = RGBColor(0xE6, 0x1B, 0x23)  # Rojo escolapio
        p.alignment = PP_ALIGN.CENTER
        
        # Añadir lema
        self._add_lema_image(slide, prs)
    
    def _crear_slide_transicion(self, prs, momento: str, color: str = "verde") -> None:
        """Crea slide de transición entre momentos litúrgicos."""
        from pptx.util import Inches, Pt
        from pptx.dml.color import RGBColor
        from pptx.enum.text import PP_ALIGN
        
        colores = {
            "verde": RGBColor(0x4C, 0xAF, 0x50),
            "violeta": RGBColor(0x9C, 0x27, 0xB0),
            "blanco": RGBColor(0xFF, 0xFF, 0xFF),
            "rojo": RGBColor(0xF4, 0x43, 0x36),
            "rosa": RGBColor(0xE9, 0x1E, 0x63),
        }
        
        fondo = colores.get(color, colores["verde"])
        texto_color = RGBColor(0xFF, 0xFF, 0xFF) if color != "blanco" else RGBColor(0x33, 0x33, 0x33)
        
        slide_layout = prs.slide_layouts[6]
        slide = prs.slides.add_slide(slide_layout)
        
        background = slide.background
        fill = background.fill
        fill.solid()
        fill.fore_color.rgb = fondo
        
        # Texto momento
        text_box = slide.shapes.add_textbox(Inches(1), Inches(3), Inches(11), Inches(1))
        tf = text_box.text_frame
        p = tf.paragraphs[0]
        p.text = momento.upper()
        p.font.name = "Calibri"
        p.font.size = Pt(44)
        p.font.bold = True
        p.font.color.rgb = texto_color
        p.alignment = PP_ALIGN.CENTER

    def _crear_slide_lectura(self, prs, titulo: str, cita: str, texto: str, color: str = "verde") -> None:
        """Crea una slide de lectura con fondo de color litúrgico."""
        from pptx import Presentation
        from pptx.util import Inches, Pt
        from pptx.dml.color import RGBColor
        from pptx.enum.text import PP_ALIGN
        
        # Colores litúrgicos
        colores = {
            "verde": RGBColor(0x4C, 0xAF, 0x50),
            "violeta": RGBColor(0x9C, 0x27, 0xB0),
            "blanco": RGBColor(0xFF, 0xFF, 0xFF),
            "rojo": RGBColor(0xF4, 0x43, 0x36),
            "rosa": RGBColor(0xE9, 0x1E, 0x63),
        }
        
        fondo = colores.get(color, colores["verde"])
        texto_color = RGBColor(0xFF, 0xFF, 0xFF) if color != "blanco" else RGBColor(0x33, 0x33, 0x33)
        
        # Crear slide con layout en blanco
        slide_layout = prs.slide_layouts[6]  # BLANK
        slide = prs.slides.add_slide(slide_layout)
        
        # Fondo de color
        background = slide.background
        fill = background.fill
        fill.solid()
        fill.fore_color.rgb = fondo
        
        # Título de la lectura
        title_box = slide.shapes.add_textbox(Inches(0.5), Inches(0.3), Inches(12.333), Inches(0.8))
        tf = title_box.text_frame
        p = tf.paragraphs[0]
        p.text = titulo
        p.font.name = "Calibri"
        p.font.size = Pt(36)
        p.font.bold = True
        p.font.color.rgb = texto_color
        p.alignment = PP_ALIGN.LEFT
        
        # Cita bíblica
        if cita:
            cita_box = slide.shapes.add_textbox(Inches(0.5), Inches(1.2), Inches(12.333), Inches(0.5))
            tf = cita_box.text_frame
            p = tf.paragraphs[0]
            p.text = cita
            p.font.name = "Calibri"
            p.font.size = Pt(20)
            p.font.italic = True
            p.font.color.rgb = RGBColor(0xCC, 0xCC, 0xCC) if color != "blanco" else RGBColor(0x66, 0x66, 0x66)
            p.alignment = PP_ALIGN.LEFT
        
        # Texto de la lectura (limitado a 500 caracteres por slide)
        texto_limpio = texto[:500] if texto else "Texto no disponible."
        if len(texto) > 500:
            texto_limpio += "..."
        
        text_box = slide.shapes.add_textbox(Inches(0.5), Inches(2.0), Inches(12.333), Inches(4.5))
        tf = text_box.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.text = texto_limpio
        p.font.name = "Calibri"
        p.font.size = Pt(20)
        p.font.color.rgb = texto_color
        p.line_spacing = 1.5
        p.alignment = PP_ALIGN.LEFT

if __name__ == "__main__":
    gen = GeneradorPPTXMaster()
    # Test
    gen.generar_presentacion("2026-09-20", 12, {
        "entrada": 8, "perdon": 8, "gloria": 8, "salmo": 8,
        "aleluya": 8, "ofertorio": 8, "santo": 8, "padre_nuestro": 8,
        "paz": 8, "comunion": 8, "maria": 8, "despedida": 8,
    })
