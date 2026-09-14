#!/usr/bin/env python3
"""
Scraper para las lecturas dominicales de ciudadredonda.org (backup de Koinonia).
Extrae: Primera lectura, Salmo, Segunda lectura (si aplica), Evangelio
"""

import logging
import os
import re
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

import requests
from bs4 import BeautifulSoup

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

PROJECT_DIR = Path(os.environ.get('CCE_PROJECT_DIR', Path(__file__).parent.parent.parent))
DB_PATH = PROJECT_DIR / "data" / "db.sqlite3"
BASE_CALENDAR_URL = "https://www.ciudadredonda.org/calendario/"
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}


class CiudadRedondaClient:
    """Cliente HTTP simple para ciudadredonda.org."""

    def __init__(self, timeout: int = 20) -> None:
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        self.timeout = timeout

    def get(self, url: str) -> Optional[str]:
        """Obtiene una pagina web."""
        try:
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            return response.text
        except requests.exceptions.RequestException as e:
            logger.error("Error al obtener %s: %s", url, e)
            return None

    def close(self) -> None:
        self.session.close()


class CiudadRedondaParser:
    """Parser HTML de las lecturas de Ciudad Redonda."""

    def __init__(self) -> None:
        self.temporadas = {
            'adviento': ['adviento', 'i domingo de adviento', 'ii domingo de adviento'],
            'navidad': ['navidad', 'navideño', 'epifanía'],
            'cuaresma': ['cuaresma', 'miércoles de ceniza', 'domingo de ramos'],
            'pascua': ['pascua', 'resurrección', 'pascual', 'pentecostés'],
            'ordinario': ['ordinario', 'tiempo ordinario'],
        }
        self.colores = {
            'adviento': 'violeta',
            'navidad': 'blanco',
            'cuaresma': 'violeta',
            'pascua': 'blanco',
            'ordinario': 'verde',
        }

    def parse_calendar(self, html: str, fecha: str) -> Optional[str]:
        """Busca en el calendario el enlace al evento de lecturas del domingo."""
        soup = BeautifulSoup(html, 'html.parser')
        
        # Buscar el contenedor del día (ej: mec-calendar-events-sec-31736-20260920)
        fecha_solo = fecha.replace('-', '')
        contenedor = soup.find(id=re.compile(rf'.*{fecha_solo}$'))
        
        if not contenedor:
            logger.warning("No se encontró contenedor para fecha %s", fecha)
            return None
        
        # Buscar enlace a "Evangelio y Lecturas"
        for link in contenedor.find_all('a', href=True):
            texto = link.get_text(strip=True).lower()
            if 'evangelio y lecturas' in texto or 'lecturas' in texto:
                href = link['href']
                if href.startswith('/'):
                    href = f"https://www.ciudadredonda.org{href}"
                return href
        
        logger.warning("No se encontró enlace a lecturas para fecha %s", fecha)
        return None

    def parse_lecturas(self, html: str, fecha: str) -> dict:
        """Parsea el HTML de las lecturas."""
        soup = BeautifulSoup(html, 'html.parser')

        resultado = {
            'fecha': fecha,
            'fuente': 'ciudadredonda',
            'fecha_scraping': datetime.now().isoformat(),
        }

        # Extraer título
        titulo = soup.find('h1', class_='mec-divi-simple-header')
        if titulo:
            resultado['celebracion'] = titulo.get_text(strip=True)

        # Extraer secciones
        secciones = self._extraer_secciones(soup)
        
        if 'primera' in secciones:
            resultado['primera_lectura_cita'] = secciones['primera']['cita']
            resultado['primera_lectura_texto'] = secciones['primera']['texto']
        
        if 'salmo' in secciones:
            resultado['salmo_cita'] = secciones['salmo']['cita']
            resultado['salmo_antifona'] = secciones['salmo']['antifona']
            resultado['salmo_texto'] = secciones['salmo']['texto']
        
        if 'segunda' in secciones:
            resultado['segunda_lectura_cita'] = secciones['segunda']['cita']
            resultado['segunda_lectura_texto'] = secciones['segunda']['texto']
        
        if 'evangelio' in secciones:
            resultado['evangelio_cita'] = secciones['evangelio']['cita']
            resultado['evangelio_texto'] = secciones['evangelio']['texto']

        resultado.update(self._detectar_temporada(soup, resultado.get('celebracion', '')))
        
        self._validar_lecturas(resultado)
        return resultado

    def _extraer_secciones(self, soup: BeautifulSoup) -> dict:
        """Extrae todas las secciones de lectura del HTML."""
        secciones = {}
        
        # Buscar todos los h2 que contienen los títulos de sección
        for h2 in soup.find_all('h2'):
            texto_h2 = h2.get_text(strip=True).lower()
            
            if 'primera lectura' in texto_h2:
                secciones['primera'] = self._extraer_contenido_lectura(h2)
            elif 'salmo' in texto_h2:
                secciones['salmo'] = self._extraer_salmo(h2)
            elif 'segunda lectura' in texto_h2:
                secciones['segunda'] = self._extraer_contenido_lectura(h2)
            elif 'evangelio' in texto_h2:
                secciones['evangelio'] = self._extraer_contenido_lectura(h2)
        
        return secciones

    def _extraer_contenido_lectura(self, tag) -> dict:
        """Extrae cita y texto de una sección de lectura."""
        # La cita está en el primer <p><b>...</b></p> después del h2
        cita = None
        texto = []
        
        for elem in tag.find_all_next():
            # Detenerse al siguiente h2
            if elem.name == 'h2':
                break
            
            if elem.name == 'p':
                contenido = elem.get_text(strip=True)
                if contenido:
                    # Si contiene negrita, es probablemente la cita
                    if elem.find('b') and not texto:
                        cita = self._limpiar_cita(contenido)
                    elif 'palabra de dios' not in contenido.lower():
                        texto.append(contenido)
        
        return {
            'cita': cita,
            'texto': '\n'.join(texto) if texto else None
        }

    def _extraer_salmo(self, tag) -> dict:
        """Extrae cita, antifona y texto del salmo."""
        cita = None
        antifona = None
        texto = []
        
        for elem in tag.find_all_next():
            if elem.name == 'h2':
                break
            
            if elem.name == 'p':
                # Obtener todo el HTML interno para preservar <br>
                html_interno = str(elem)
                # Convertir <br> a saltos de línea
                html_con_br = html_interno.replace('<br/>', '\n').replace('<br />', '\n').replace('<br>', '\n')
                soup_temp = BeautifulSoup(html_con_br, 'html.parser')
                contenido = soup_temp.get_text(strip=True)
                
                if not contenido:
                    continue
                
                # Buscar antifona: párrafo que empieza con "R/." seguido de texto en cursiva
                if contenido.lower().startswith('r/.') or contenido.lower().startswith('r/'):
                    # Es antifona si no tiene <b> y es corto
                    if not elem.find('b') and len(contenido) < 100:
                        match = re.search(r'R[/\.]\.?\s*(.+)', contenido, re.IGNORECASE)
                        if match:
                            antifona = match.group(1).strip('"').strip()
                        continue
                
                # Párrafos con <b>R/.</b> al final son estrofas del salmo
                if elem.find('b'):
                    b_text = elem.find('b').get_text(strip=True).lower()
                    if 'r/' in b_text or 'r.' in b_text:
                        texto_limpio = re.sub(r'\s*R[/\.]\.?\s*$', '', contenido, flags=re.IGNORECASE).strip()
                        if texto_limpio:
                            texto.append(texto_limpio)
                        continue
                
                # El primer párrafo con <b> es la cita (ej: "Sal 144")
                if elem.find('b') and not cita:
                    cita = self._limpiar_cita(contenido)
                    continue
                
                # Resto de párrafos son texto del salmo
                if 'palabra de dios' not in contenido.lower():
                    texto.append(contenido)
        
        return {
            'cita': cita,
            'antifona': antifona,
            'texto': '\n'.join(texto) if texto else None
        }

    def _limpiar_cita(self, texto: str) -> str:
        """Limpia y extrae la cita bíblica del texto."""
        # Quitar "Lectura de..." y dejar solo la referencia
        match = re.search(r'\(([\w\s,\.\-:]+)\)', texto)
        if match:
            return match.group(1).strip()
        # Si no hay paréntesis, buscar patrón de referencia
        match = re.search(r'[A-Za-z]+\s*\d+[,:;\-\s\.]*\d*', texto)
        if match:
            return match.group(0).strip()
        return texto.strip()

    def _detectar_temporada(self, soup: BeautifulSoup, celebracion: str) -> dict:
        """Detecta la temporada litúrgica."""
        resultado = {}
        texto_completo = (soup.get_text() + ' ' + celebracion).lower()

        # Orden de búsqueda: más específico a menos específico
        # "ordinario" aparece en "tiempo ordinario", pero no queremos
        # que coincida antes que otras temporadas
        temporada_encontrada = None
        for temp, palabras in self.temporadas.items():
            if any(p in texto_completo for p in palabras):
                temporada_encontrada = temp
                # No hacer break para que las temporadas más específicas
                # puedan sobreescribir si aparecen más de una
        
        resultado['temporada'] = temporada_encontrada or 'ordinario'

        # Extraer número de domingo
        match = re.search(r'(\d+)[º°]?\s*domingo', texto_completo, re.IGNORECASE)
        if match:
            resultado['domingo'] = f"Domingo {match.group(1)}"

        # Extraer ciclo
        match = re.search(r'ciclo\s+([ABC])', texto_completo, re.IGNORECASE)
        if match:
            resultado['ciclo'] = match.group(1)

        resultado['color_liturgico'] = self.colores.get(resultado.get('temporada', 'ordinario'), 'verde')
        return resultado

    def _validar_lecturas(self, resultado: dict) -> None:
        """Valida que existan al menos primera lectura, salmo y evangelio."""
        faltantes = []
        for campo in ['primera_lectura_texto', 'salmo_texto', 'evangelio_texto']:
            if not resultado.get(campo):
                faltantes.append(campo)
        if faltantes:
            raise ValueError(f"Lecturas incompletas. Faltan: {', '.join(faltantes)}")


class CiudadRedondaRepository:
    """Repositorio SQLite para lecturas (misma tabla que Koinonia)."""

    def __init__(self, db_path: Optional[Path] = None) -> None:
        self.db_path = db_path or DB_PATH

    def guardar(self, lecturas: dict) -> None:
        """Guarda las lecturas en la base de datos."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO lecturas
                    (fecha, domingo, temporada, ciclo, color_liturgico, celebracion,
                     primera_lectura_cita, primera_lectura_texto,
                     salmo_cita, salmo_antifona, salmo_texto,
                     segunda_lectura_cita, segunda_lectura_texto,
                     evangelio_cita, evangelio_texto,
                     fuente_scraping)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(fecha) DO UPDATE SET
                        domingo = excluded.domingo,
                        temporada = excluded.temporada,
                        ciclo = excluded.ciclo,
                        color_liturgico = excluded.color_liturgico,
                        celebracion = excluded.celebracion,
                        primera_lectura_cita = excluded.primera_lectura_cita,
                        primera_lectura_texto = excluded.primera_lectura_texto,
                        salmo_cita = excluded.salmo_cita,
                        salmo_antifona = excluded.salmo_antifona,
                        salmo_texto = excluded.salmo_texto,
                        segunda_lectura_cita = excluded.segunda_lectura_cita,
                        segunda_lectura_texto = excluded.segunda_lectura_texto,
                        evangelio_cita = excluded.evangelio_cita,
                        evangelio_texto = excluded.evangelio_texto,
                        fuente_scraping = excluded.fuente_scraping
                ''', (
                    lecturas.get('fecha'),
                    lecturas.get('domingo', ''),
                    lecturas.get('temporada', ''),
                    lecturas.get('ciclo', ''),
                    lecturas.get('color_liturgico', 'verde'),
                    lecturas.get('celebracion', ''),
                    lecturas.get('primera_lectura_cita', ''),
                    lecturas.get('primera_lectura_texto', ''),
                    lecturas.get('salmo_cita', ''),
                    lecturas.get('salmo_antifona', ''),
                    lecturas.get('salmo_texto', ''),
                    lecturas.get('segunda_lectura_cita', ''),
                    lecturas.get('segunda_lectura_texto', ''),
                    lecturas.get('evangelio_cita', ''),
                    lecturas.get('evangelio_texto', ''),
                    'ciudadredonda',
                ))
                conn.commit()
                logger.info("Lecturas guardadas para %s", lecturas.get('fecha'))
        except Exception as e:
            logger.error("Error al guardar lecturas: %s", e)
            raise


def obtener_lecturas_ciudadredonda(fecha: str, db_path: Optional[Path] = None) -> Optional[dict]:
    """
    Función principal: obtiene lecturas de Ciudad Redonda para una fecha.
    
    Args:
        fecha: Fecha en formato YYYY-MM-DD
        db_path: Ruta opcional a la base de datos
    
    Returns:
        Dict con las lecturas o None si falla
    """
    client = CiudadRedondaClient()
    parser = CiudadRedondaParser()
    repo = CiudadRedondaRepository(db_path)
    
    try:
        # Paso 1: Obtener calendario y buscar enlace
        logger.info("Obteniendo calendario de Ciudad Redonda...")
        calendario_html = client.get(BASE_CALENDAR_URL)
        if not calendario_html:
            return None
        
        lecturas_url = parser.parse_calendar(calendario_html, fecha)
        if not lecturas_url:
            return None
        
        # Paso 2: Obtener página de lecturas
        logger.info("Obteniendo lecturas de %s", lecturas_url)
        lecturas_html = client.get(lecturas_url)
        if not lecturas_html:
            return None
        
        # Paso 3: Parsear y guardar
        resultado = parser.parse_lecturas(lecturas_html, fecha)
        repo.guardar(resultado)
        
        return resultado
        
    except Exception as e:
        logger.error("Error al obtener lecturas de Ciudad Redonda: %s", e)
        return None
    finally:
        client.close()


if __name__ == "__main__":
    # Prueba
    import sys
    fecha = sys.argv[1] if len(sys.argv) > 1 else datetime.now().strftime('%Y-%m-%d')
    resultado = obtener_lecturas_ciudadredonda(fecha)
    if resultado:
        print(f"✅ Lecturas obtenidas para {fecha}")
        print(f"   Celebración: {resultado.get('celebracion')}")
        print(f"   Evangelio: {resultado.get('evangelio_cita')}")
    else:
        print(f"❌ No se pudieron obtener lecturas para {fecha}")
