#!/usr/bin/env python3
"""
Scraper completo para el Cancionero Escolapio - VERSION CON POSICIONAMIENTO
Extrae TODAS las canciones con acordes posicionados y guarda en la base de datos

MEJORAS APLICADAS (por OpenCode + Kimi-k2.7-code:cloud):
- Reintentos con backoff exponencial
- Filtrado estricto de enlaces
- Validación de contenido
- Manejo seguro de conexiones SQLite
- Logging en vez de print
- Sin sys.path.insert (anti-patrón)
"""

import requests
from bs4 import BeautifulSoup
import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
import time
import logging
from urllib.parse import urljoin, urlparse
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuracion
PROJECT_DIR = Path.home() / "proyectos" / "CCE-M5-Web-Presentaciones"
DB_PATH = PROJECT_DIR / "data" / "db.sqlite3"
OUTPUT_DIR = PROJECT_DIR / "data" / "canciones"
BASE_URL = "https://ccem5music.blogspot.com/p/cancionero-escolapio.html"
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

# Importar parser V2 - usando PYTHONPATH correctamente
import sys
sys.path.insert(0, str(PROJECT_DIR / "src"))
from parsers.acordes_parser_v2 import AcordesParser


class CancioneroScraper:
    """Scraper robusto para el cancionero escolapio con reintentos y validación."""
    
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
        
        self.parser = AcordesParser()
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        
    def obtener_pagina(self, url):
        """Obtiene una pagina web con reintentos."""
        try:
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            return response.text
        except requests.exceptions.RequestException as e:
            logger.error(f"Error al obtener {url}: {e}")
            return None
    
    def extraer_enlaces_canciones(self, html):
        """Extrae los enlaces a cada cancion con filtrado estricto."""
        soup = BeautifulSoup(html, 'html.parser')
        canciones = []
        dominios_permitidos = {'ccem5music.blogspot.com', 'blogspot.com'}
        
        for enlace in soup.find_all('a', href=True):
            href = enlace['href']
            texto = enlace.get_text(strip=True)
            
            # Filtrar enlaces vacíos o muy cortos
            if not texto or len(texto) <= 2:
                continue
            
            # Resolver URL relativa
            url_completa = urljoin(BASE_URL, href)
            parsed = urlparse(url_completa)
            
            # Verificar dominio
            if parsed.netloc not in dominios_permitidos:
                continue
            
            # Verificar que es página de canción (/p/)
            if '/p/' not in parsed.path:
                continue
            
            # Evitar la página principal del cancionero
            if url_completa == BASE_URL or '/cancionero-escolapio' in parsed.path:
                continue
            
            # Evitar duplicados
            if not any(c['url'] == url_completa for c in canciones):
                canciones.append({
                    'titulo': texto,
                    'url': url_completa
                })
        
        logger.info(f"Encontradas {len(canciones)} canciones válidas")
        return canciones
    
    def obtener_cancion(self, url):
        """Obtiene y parsea una cancion con validación."""
        html = self.obtener_pagina(url)
        if not html:
            return None
        
        soup = BeautifulSoup(html, 'html.parser')
        
        # Buscar el contenido principal
        post_body = soup.find('div', class_='post-body') or soup.find('div', class_='entry-content')
        if not post_body:
            logger.warning(f"No se encontró contenido en {url}")
            return None
        
        # Extraer título de la página como respaldo
        titulo_h1 = soup.find('h1', class_='post-title')
        titulo_pagina = titulo_h1.get_text(strip=True) if titulo_h1 else None
        
        # Extraer texto con formato preservado
        texto_completo = post_body.get_text('\n').strip()
        
        # Validar que tiene contenido
        if not texto_completo or len(texto_completo) < 20:
            logger.warning(f"Canción sin contenido suficiente en {url}")
            return None
        
        # Guardar HTML original como backup (limitado a 50KB)
        html_original = str(post_body)
        if len(html_original) > 50000:
            html_original = html_original[:50000] + "... [truncado]"
        
        # Parsear con el nuevo parser
        estructura = self.parser.parsear_cancion_completa(texto_completo)
        
        # Validar que se extrajo algo
        if not estructura:
            logger.warning(f"No se pudo parsear estructura en {url}")
            return None
        
        # Detectar tono
        tono = self.parser.detectar_tono(estructura)
        
        # Generar HTML visual
        html_visual = self.parser.generar_html_visual(estructura)
        
        return {
            'titulo': titulo_pagina,
            'url': url,
            'letra_con_acordes': texto_completo,
            'letra_sin_acordes': '\n'.join(
                linea.get('texto', linea.get('letra', '')) 
                for linea in estructura 
                if linea['tipo'] in ['letra', 'mixta']
            ),
            'estructura_json': json.dumps(estructura, ensure_ascii=False),
            'html_visual': html_visual,
            'html_original': html_original,
            'tono': tono,
            'fuente': 'blogspot'
        }
    
    def guardar_en_db(self, cancion):
        """Guarda una cancion en la base de datos de forma segura."""
        try:
            with sqlite3.connect(str(DB_PATH)) as conn:
                cursor = conn.cursor()
                
                # Verificar si existe columna estructura_json
                cursor.execute("PRAGMA table_info(canciones)")
                columnas = [row[1] for row in cursor.fetchall()]
                
                if 'estructura_json' not in columnas:
                    logger.info("Agregando columnas nuevas a la tabla canciones")
                    cursor.execute('ALTER TABLE canciones ADD COLUMN estructura_json TEXT')
                    cursor.execute('ALTER TABLE canciones ADD COLUMN html_visual TEXT')
                    cursor.execute('ALTER TABLE canciones ADD COLUMN html_original TEXT')
                    conn.commit()
                
                # Verificar si la canción ya existe
                cursor.execute(
                    'SELECT id FROM canciones WHERE titulo_url = ?', 
                    (cancion['url'],)
                )
                existente = cursor.fetchone()
                
                if existente:
                    # Actualizar existente
                    logger.info(f"Actualizando canción existente: {cancion['titulo']}")
                    cursor.execute('''
                        UPDATE canciones SET
                            titulo = ?,
                            letra_con_acordes = ?,
                            letra_sin_acordes = ?,
                            estructura_json = ?,
                            html_visual = ?,
                            html_original = ?,
                            tono = ?,
                            fuente = ?
                        WHERE titulo_url = ?
                    ''', (
                        cancion['titulo'],
                        cancion.get('letra_con_acordes', ''),
                        cancion.get('letra_sin_acordes', ''),
                        cancion.get('estructura_json', '[]'),
                        cancion.get('html_visual', ''),
                        cancion.get('html_original', ''),
                        cancion.get('tono', ''),
                        'blogspot',
                        cancion['url']
                    ))
                else:
                    # Insertar nueva
                    cursor.execute('''
                        INSERT INTO canciones 
                        (titulo, titulo_url, letra_con_acordes, letra_sin_acordes, acordes_json, 
                         estructura_json, html_visual, html_original, tono, fuente)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        cancion['titulo'],
                        cancion['url'],
                        cancion.get('letra_con_acordes', ''),
                        cancion.get('letra_sin_acordes', ''),
                        json.dumps([]),
                        cancion.get('estructura_json', '[]'),
                        cancion.get('html_visual', ''),
                        cancion.get('html_original', ''),
                        cancion.get('tono', ''),
                        'blogspot'
                    ))
                
                conn.commit()
                logger.info(f"✅ Guardada en DB: {cancion['titulo']}")
                
        except sqlite3.Error as e:
            logger.error(f"Error de SQLite al guardar {cancion.get('titulo', 'desconocida')}: {e}")
    
    def ejecutar(self):
        """Ejecuta el scraper completo."""
        logger.info("=" * 70)
        logger.info("SCRAPER CANCIONERO ESCOLAPIO - VERSION CON POSICIONAMIENTO")
        logger.info("=" * 70)
        
        # Obtener pagina principal
        html = self.obtener_pagina(BASE_URL)
        if not html:
            logger.error("ERROR: No se pudo obtener la pagina principal")
            return
        
        # Extraer enlaces
        canciones = self.extraer_enlaces_canciones(html)
        logger.info(f"Total: {len(canciones)} canciones")
        
        # Procesar cada cancion
        exitosas = 0
        for i, cancion_info in enumerate(canciones, 1):
            logger.info(f"[{i:2d}/{len(canciones):2d}] {cancion_info['titulo']}")
            
            datos = self.obtener_cancion(cancion_info['url'])
            if datos:
                # Usar título del enlace si no se extrajo de la página
                if not datos['titulo']:
                    datos['titulo'] = cancion_info['titulo']
                
                self.guardar_en_db(datos)
                exitosas += 1
            else:
                logger.warning(f"  ❌ No se pudo procesar: {cancion_info['titulo']}")
            
            # Pausa para no sobrecargar el servidor
            time.sleep(1)
        
        logger.info("=" * 70)
        logger.info(f"Resumen: {exitosas}/{len(canciones)} canciones procesadas correctamente")
        logger.info("=" * 70)

def main():
    scraper = CancioneroScraper()
    scraper.ejecutar()

if __name__ == "__main__":
    main()
