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
    
    def __init__(self):
        self.master_path = MASTER_PATH
        self.output_dir = OUTPUT_DIR
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
        """Rebuild PPTX with selected slides."""
        try:
            # Read presentation.xml
            pres_path = temp_dir / "ppt" / "presentation.xml"
            pres_tree = ET.parse(pres_path)
            pres_root = pres_tree.getroot()
            
            ns = {'p': 'http://schemas.openxmlformats.org/presentationml/2006/main'}
            
            # Find sldIdLst
            sldIdLst = pres_root.find('.//p:sldIdLst', ns)
            if sldIdLst is None:
                print("ERROR: Could not find sldIdLst")
                return False
            
            # Get all slide info
            slides_info = []
            for sldId in sldIdLst:
                id_val = sldId.get('id')
                r_id = sldId.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id')
                slides_info.append({'id': id_val, 'rId': r_id, 'elem': sldId})
            
            # Read presentation rels
            pres_rels_path = temp_dir / "ppt" / "_rels" / "presentation.xml.rels"
            pres_rels_tree = ET.parse(pres_rels_path)
            pres_rels_root = pres_rels_tree.getroot()
            
            # Map rId to slide filename
            rId_to_slide = {}
            for rel in pres_rels_root:
                rid = rel.get('Id')
                target = rel.get('Target')
                if target and target.startswith('slides/slide'):
                    rId_to_slide[rid] = target
            
            # Map slide number to rId
            slide_num_to_rId = {}
            for i, info in enumerate(slides_info, 1):
                slide_num_to_rId[i] = info['rId']
            
            # Determine which slides to keep
            keep_rIds = []
            for num in slide_numbers:
                if num in slide_num_to_rId:
                    keep_rIds.append(slide_num_to_rId[num])
            
            # Remove unwanted slides from sldIdLst
            for sldId in list(sldIdLst):
                r_id = sldId.get('{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id')
                if r_id not in keep_rIds:
                    sldIdLst.remove(sldId)
            
            # Remove unwanted relationships
            for rel in list(pres_rels_root):
                rid = rel.get('Id')
                if rid not in keep_rIds and rid in rId_to_slide:
                    pres_rels_root.remove(rel)
            
            # Save modified XMLs
            pres_tree.write(pres_path, xml_declaration=True, encoding='UTF-8')
            pres_rels_tree.write(pres_rels_path, xml_declaration=True, encoding='UTF-8')
            
            # Remove slide files we don't need
            slides_dir = temp_dir / "ppt" / "slides"
            rels_dir = temp_dir / "ppt" / "slides" / "_rels"
            
            for i in range(1, len(slides_info) + 1):
                if i not in slide_numbers:
                    slide_file = slides_dir / f"slide{i}.xml"
                    rels_file = rels_dir / f"slide{i}.xml.rels"
                    if slide_file.exists():
                        slide_file.unlink()
                    if rels_file.exists():
                        rels_file.unlink()
            
            # Rebuild PPTX
            with zipfile.ZipFile(output_path, 'w', zipfile.ZIP_DEFLATED) as zf:
                for root_dir, dirs, files in os.walk(temp_dir):
                    for file in files:
                        file_path = Path(root_dir) / file
                        arcname = str(file_path.relative_to(temp_dir))
                        zf.write(file_path, arcname)
            
            return True
            
        except Exception as e:
            print(f"Error rebuilding PPTX: {e}")
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
                
                if self._rebuild_pptx(temp_dir, output_path, slides_to_keep):
                    print(f"✅ Presentación generada: {output_path}")
                    print(f"   Slides: {len(slides_to_keep)}")
                    return output_path
                else:
                    print("ERROR: No se pudo generar la presentación")
                    return None
                
        except Exception as e:
            print(f"ERROR: {e}")
            return None


if __name__ == "__main__":
    gen = GeneradorPPTXMaster()
    # Test
    gen.generar_presentacion("2026-09-20", 12, {
        "entrada": 8, "perdon": 8, "gloria": 8, "salmo": 8,
        "aleluya": 8, "ofertorio": 8, "santo": 8, "padre_nuestro": 8,
        "paz": 8, "comunion": 8, "maria": 8, "despedida": 8,
    })
