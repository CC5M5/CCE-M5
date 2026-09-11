#!/usr/bin/env python3
"""
Scraper para las lecturas dominicales de servicioskoinonia.org
Extrae: Primera lectura, Salmo, Segunda lectura (si aplica), Evangelio

MEJORAS APLICADAS (basado en análisis de OpenCode + Kimi):
- Reintentos con backoff exponencial
- Parseo más robusto con selectores CSS
- Detección correcta del domingo actual
- Logging profesional
- Manejo de rate-limiting
- Normalización de fechas a ISO
"""

import requests
from bs4 import BeautifulSoup
import sqlite3
import logging
from datetime import datetime, timedelta
from pathlib import Path
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuracion
PROJECT_DIR = Path(__file__).parent.parent.parent
DB_PATH = PROJECT_DIR / "data" / "db.sqlite3"
BASE_URL = "https://servicioskoinonia.org/biblico/calendario"
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

class KoinoniaScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        
        # Configurar reintentos con backoff exponencial
        retry = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504]
        )
        adapter = HTTPAdapter(max_retries=retry)
        self.session.mount('https://', adapter)
        self.session.mount('http://', adapter)
        
    def obtener_pagina(self, url):
        """Obtiene una pagina web con reintentos."""
        try:
            response = self.session.get(url, timeout=20)
            response.raise_for_status()
            return response.text
        except requests.exceptions.RequestException as e:
            logger.error(f"Error al obtener {url}: {e}")
            return None
    
    def parsear_lecturas(self, html, fecha_codigo):
        """Parsea el HTML de las lecturas con selectores robustos."""
        soup = BeautifulSoup(html, 'html.parser')
        
        resultado = {
            'fecha': self._normalizar_fecha(fecha_codigo),
            'fuente': 'koinonia',
            'fecha_scraping': datetime.now().isoformat()
        }
        
        # Extraer titulo/celebracion
        titulo = soup.find('h1') or soup.find('h2')
        if titulo:
            resultado['celebracion'] = titulo.get_text(strip=True)
        
        # Extraer secciones usando selectores CSS más específicos
        # Primera lectura
        primera = self._extraer_seccion_robusta(soup, ['primera lectura', 'lectura del día'])
        if primera:
            resultado['primera_lectura_cita'] = primera.get('cita')
            resultado['primera_lectura_texto'] = primera.get('texto')
        
        # Salmo
        salmo = self._extraer_seccion_robusta(soup, ['salmo', 'salmo responsorial'])
        if salmo:
            resultado['salmo_cita'] = salmo.get('cita')
            resultado['salmo_antifona'] = salmo.get('antifona')
            resultado['salmo_texto'] = salmo.get('texto')
        
        # Segunda lectura
        segunda = self._extraer_seccion_robusta(soup, ['segunda lectura'])
        if segunda:
            resultado['segunda_lectura_cita'] = segunda.get('cita')
            resultado['segunda_lectura_texto'] = segunda.get('texto')
        
        # Evangelio
        evangelio = self._extraer_seccion_robusta(soup, ['evangelio', 'lectura del evangelio'])
        if evangelio:
            resultado['evangelio_cita'] = evangelio.get('cita')
            resultado['evangelio_texto'] = evangelio.get('texto')
        
        # Detectar temporada litúrgica y domingo
        resultado.update(self._detectar_temporada(soup, resultado.get('celebracion', '')))
        
        return resultado
    
    def _extraer_seccion_robusta(self, soup, posibles_titulos):
        """Extrae una sección de lectura con selectores más robustos."""
        for tag in soup.find_all(['h2', 'h3', 'h4', 'p', 'div']):
            texto = tag.get_text(strip=True).lower()
            if any(titulo.lower() in texto for titulo in posibles_titulos):
                # Buscar el contenido siguiente de forma más robusta
                siguiente = tag.find_next_sibling()
                if siguiente:
                    return {
                        'cita': tag.get_text(strip=True),
                        'texto': siguiente.get_text(strip=True)
                    }
        return None
    
    def _detectar_temporada(self, soup, celebracion):
        """Detecta la temporada litúrgica de forma más precisa."""
        resultado = {}
        texto_completo = soup.get_text().lower()
        
        # Temporadas con palabras clave más específicas
        temporadas = {
            'adviento': ['adviento', 'i domingo de adviento', 'ii domingo de adviento'],
            'navidad': ['navidad', 'navideño', 'epifanía'],
            'cuaresma': ['cuaresma', 'miércoles de ceniza', 'domingo de ramos'],
            'pascua': ['pascua', 'resurrección', 'pascual', 'pentecostés'],
            'ordinario': ['ordinario', 'tiempo ordinario']
        }
        
        for temp, palabras in temporadas.items():
            if any(p in texto_completo for p in palabras):
                resultado['temporada'] = temp
                break
        else:
            resultado['temporada'] = 'ordinario'
        
        # Detectar numero de domingo más preciso
        import re
        match = re.search(r'(\d+)[º°]?\s*domingo', texto_completo, re.IGNORECASE)
        if match:
            resultado['domingo'] = f"Domingo {match.group(1)}"
        
        # Detectar ciclo (A, B, C)
        match = re.search(r'ciclo\s+([ABC])', texto_completo, re.IGNORECASE)
        if match:
            resultado['ciclo'] = match.group(1)
        
        # Color liturgico basado en temporada
        colores = {
            'adviento': 'violeta',
            'navidad': 'blanco',
            'cuaresma': 'violeta',
            'pascua': 'blanco',
            'ordinario': 'verde'
        }
        resultado['color_liturgico'] = colores.get(resultado.get('temporada', 'ordinario'), 'verde')
        
        return resultado
    
    def _normalizar_fecha(self, fecha_codigo):
        """Normaliza fecha de YYYYMMDD a ISO format."""
        try:
            return datetime.strptime(fecha_codigo, '%Y%m%d').date().isoformat()
        except ValueError:
            return fecha_codigo
    
    def obtener_lecturas(self, fecha):
        """Obtiene las lecturas para una fecha específica."""
        if isinstance(fecha, str):
            codigo = fecha
        else:
            codigo = fecha.strftime('%Y%m%d')
        
        url = f"{BASE_URL}/texto.php?codigo={codigo}"
        logger.info(f"Obteniendo lecturas para: {codigo}")
        
        html = self.obtener_pagina(url)
        if not html:
            return None
        
        return self.parsear_lecturas(html, codigo)
    
    def obtener_proximo_domingo(self):
        """Obtiene las lecturas para el próximo domingo (incluyendo hoy si es domingo)."""
        hoy = datetime.now().date()
        
        # Calcular próximo domingo (si hoy es domingo, devuelve hoy)
        dias_hasta_domingo = (6 - hoy.weekday()) % 7
        proximo_domingo = hoy + timedelta(days=dias_hasta_domingo)
        
        logger.info(f"Próximo domingo: {proximo_domingo}")
        return self.obtener_lecturas(proximo_domingo)
    
    def guardar_en_db(self, lecturas):
        """Guarda las lecturas en la base de datos de forma segura."""
        try:
            with sqlite3.connect(str(DB_PATH)) as conn:
                cursor = conn.cursor()
                
                # Crear tabla si no existe
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS lecturas (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        fecha DATE NOT NULL,
                        domingo TEXT,
                        temporada TEXT NOT NULL,
                        ciclo TEXT,
                        color_liturgico TEXT NOT NULL,
                        primera_lectura_cita TEXT,
                        primera_lectura_texto TEXT,
                        salmo_cita TEXT,
                        salmo_antifona TEXT,
                        salmo_texto TEXT,
                        segunda_lectura_cita TEXT,
                        segunda_lectura_texto TEXT,
                        evangelio_cita TEXT,
                        evangelio_texto TEXT,
                        fuente_scraping TEXT DEFAULT 'koinonia',
                        fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(fecha)
                    )
                ''')
                
                # Insertar o actualizar
                cursor.execute('''
                    INSERT INTO lecturas 
                    (fecha, domingo, temporada, ciclo, color_liturgico,
                     primera_lectura_cita, primera_lectura_texto,
                     salmo_cita, salmo_antifona, salmo_texto,
                     segunda_lectura_cita, segunda_lectura_texto,
                     evangelio_cita, evangelio_texto,
                     fuente_scraping)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(fecha) DO UPDATE SET
                        domingo = excluded.domingo,
                        temporada = excluded.temporada,
                        ciclo = excluded.ciclo,
                        color_liturgico = excluded.color_liturgico,
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
                    lecturas.get('primera_lectura_cita', ''),
                    lecturas.get('primera_lectura_texto', ''),
                    lecturas.get('salmo_cita', ''),
                    lecturas.get('salmo_antifona', ''),
                    lecturas.get('salmo_texto', ''),
                    lecturas.get('segunda_lectura_cita', ''),
                    lecturas.get('segunda_lectura_texto', ''),
                    lecturas.get('evangelio_cita', ''),
                    lecturas.get('evangelio_texto', ''),
                    'koinonia'
                ))
                
                conn.commit()
                logger.info(f"✅ Lecturas guardadas para {lecturas.get('fecha')}")
                
        except sqlite3.Error as e:
            logger.error(f"Error de SQLite al guardar lecturas: {e}")

def main():
    scraper = KoinoniaScraper()
    lecturas = scraper.obtener_proximo_domingo()
    
    if lecturas:
        scraper.guardar_en_db(lecturas)
        logger.info(f"Celebración: {lecturas.get('celebracion', 'No detectada')}")
        logger.info(f"Temporada: {lecturas.get('temporada', 'No detectada')}")
    else:
        logger.error("No se pudieron obtener las lecturas")

if __name__ == "__main__":
    main()
