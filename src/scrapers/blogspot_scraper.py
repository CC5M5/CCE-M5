#!/usr/bin/env python3
"""
Scraper completo para el Cancionero Escolapio - VERSION CON POSICIONAMIENTO
Extrae TODAS las canciones con acordes posicionados y guarda en la base de datos

MEJORAS APLICADAS (basado en análisis de OpenCode + Kimi + Context7):
- Reintentos con backoff exponencial
- Filtrado estricto de enlaces con validación de dominio
- Validación de contenido
- Manejo seguro de conexiones SQLite (WAL mode)
- Logging profesional
- Sin sys.path.insert (anti-patrón)
- Eliminación de scripts/styles antes de extraer texto
- User-Agent rotativo
- Encoding explícito con response.content
"""

import requests
from bs4 import BeautifulSoup
import json
import sqlite3
import logging
import random
import os
from pathlib import Path
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from urllib.parse import urljoin, urlparse

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuración con variable de entorno
PROJECT_DIR = Path(os.environ.get(
    "CCE_PROJECT_DIR", 
    Path.home() / "proyectos" / "CCE-M5-Web-Presentaciones"
))
DB_PATH = PROJECT_DIR / "data" / "db.sqlite3"
BASE_URL = "https://ccem5music.blogspot.com/p/cancionero-escolapio.html"
ALLOWED_HOSTS = {"ccem5music.blogspot.com"}

# User-Agent rotativo para evitar bloqueos
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'
]


class CancioneroScraper:
    """Scraper robusto para el cancionero escolapio con reintentos y validación."""
    
    def __init__(self):
        self.session = requests.Session()
        
        # Configurar reintentos con backoff exponencial
        retry = Retry(
            total=5,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods={"HEAD", "GET"}
        )
        adapter = HTTPAdapter(max_retries=retry)
        self.session.mount('https://', adapter)
        self.session.mount('http://', adapter)
        
        # Configurar conexión SQLite persistente con WAL mode
        self.db_path = DB_PATH
        self._init_db()
        
    def _init_db(self):
        """Inicializa la base de datos con WAL mode para mejor concurrencia."""
        conn = sqlite3.connect(str(self.db_path))
        try:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA foreign_keys=ON")
            logger.info("Base de datos inicializada con WAL mode")
        finally:
            conn.close()
    
    def _get_connection(self):
        """Obtiene conexión a la base de datos."""
        conn = sqlite3.connect(str(self.db_path))
        conn.execute("PRAGMA foreign_keys=ON")
        return conn
    
    def obtener_pagina(self, url):
        """Obtiene una página web con reintentos y User-Agent rotativo."""
        headers = {'User-Agent': random.choice(USER_AGENTS)}
        try:
            response = self.session.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            # Usar content (bytes) para que BeautifulSoup detecte encoding
            return response.content
        except requests.exceptions.RequestException as e:
            logger.exception(f"Error al obtener {url}")
            return None
    
    def extraer_enlaces_canciones(self, html_bytes):
        """Extrae los enlaces a cada canción con filtrado estricto."""
        soup = BeautifulSoup(html_bytes, 'lxml')
        canciones = []
        seen_urls = set()
        
        for enlace in soup.find_all('a', href=True):
            href = enlace['href']
            texto = enlace.get_text(strip=True)
            
            # Filtrar enlaces vacíos o muy cortos
            if not texto or len(texto) <= 2:
                continue
            
            # Resolver URL relativa
            url_completa = urljoin(BASE_URL, href)
            parsed = urlparse(url_completa)
            
            # Verificar dominio exacto (no solo sufijo)
            if parsed.netloc not in ALLOWED_HOSTS:
                continue
            
            # Verificar que es página de canción (/p/)
            if '/p/' not in parsed.path:
                continue
            
            # Evitar la página principal del cancionero
            if url_completa == BASE_URL or '/cancionero-escolapio' in parsed.path:
                continue
            
            # Normalizar URL (quitar fragmentos, query, trailing slash)
            url_normalizada = url_completa.split('#')[0].split('?')[0].rstrip('/')
            
            # Evitar duplicados usando set
            if url_normalizada in seen_urls:
                continue
            
            seen_urls.add(url_normalizada)
            canciones.append({
                'titulo': texto,
                'url': url_normalizada
            })
        
        logger.info(f"Encontradas {len(canciones)} canciones válidas")
        return canciones
    
    def obtener_cancion(self, url):
        """Obtiene y parsea una canción con validación."""
        html_bytes = self.obtener_pagina(url)
        if not html_bytes:
            return None
        
        soup = BeautifulSoup(html_bytes, 'lxml')
        
        # Buscar el contenido principal
        post_body = soup.find('div', class_='post-body') or soup.find('div', class_='entry-content')
        if not post_body:
            logger.warning(f"No se encontró contenido en {url}")
            return None
        
        # Extraer título de la página como respaldo
        titulo_h1 = soup.find('h1', class_='post-title')
        titulo_pagina = titulo_h1.get_text(strip=True) if titulo_h1 else None
        
        # Eliminar scripts, styles y otros elementos no deseados
        for tag in post_body.find_all(['script', 'style', 'nav', 'footer', 'aside', 'iframe']):
            tag.decompose()
        
        # Extraer texto con formato preservado
        texto_completo = post_body.get_text('\n').strip()
        
        # Validar que tiene contenido
        if not texto_completo or len(texto_completo) < 20:
            logger.warning(f"Canción sin contenido suficiente en {url}")
            return None
        
        # Parsear con el parser V2
        # Nota: importamos directamente desde el módulo
        from parsers.acordes_parser_v2 import AcordesParser
        parser = AcordesParser()
        
        estructura = parser.parsear_cancion_completa(texto_completo)
        
        # Validar que se extrajo algo
        if not estructura:
            logger.warning(f"No se pudo parsear estructura en {url}")
            return None
        
        # Detectar tono
        tono = parser.detectar_tono(estructura)
        
        # Generar HTML visual
        html_visual = parser.generar_html_visual(estructura)
        
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
            'tono': tono,
            'fuente': 'blogspot'
        }
    
    def guardar_en_db(self, cancion):
        """Guarda una canción en la base de datos de forma segura."""
        # Sanitizar título
        titulo = (cancion.get('titulo') or cancion.get('titulo_url') or "Sin título").strip()
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Verificar si existe columna estructura_json
                cursor.execute("PRAGMA table_info(canciones)")
                columnas = [row[1] for row in cursor.fetchall()]
                
                if 'estructura_json' not in columnas:
                    logger.info("Agregando columnas nuevas a la tabla canciones")
                    cursor.execute('ALTER TABLE canciones ADD COLUMN estructura_json TEXT')
                    cursor.execute('ALTER TABLE canciones ADD COLUMN html_visual TEXT')
                    conn.commit()
                
                # Verificar si la canción ya existe por URL normalizada
                cursor.execute(
                    'SELECT id FROM canciones WHERE titulo_url = ?', 
                    (cancion['url'],)
                )
                existente = cursor.fetchone()
                
                if existente:
                    # Actualizar existente
                    logger.info(f"Actualizando canción existente: {titulo}")
                    cursor.execute('''
                        UPDATE canciones SET
                            titulo = ?,
                            letra_con_acordes = ?,
                            letra_sin_acordes = ?,
                            estructura_json = ?,
                            html_visual = ?,
                            tono = ?,
                            fuente = ?
                        WHERE titulo_url = ?
                    ''', (
                        titulo,
                        cancion.get('letra_con_acordes', ''),
                        cancion.get('letra_sin_acordes', ''),
                        cancion.get('estructura_json', '[]'),
                        cancion.get('html_visual', ''),
                        cancion.get('tono', ''),
                        'blogspot',
                        cancion['url']
                    ))
                else:
                    # Insertar nueva
                    cursor.execute('''
                        INSERT INTO canciones 
                        (titulo, titulo_url, letra_con_acordes, letra_sin_acordes, 
                         estructura_json, html_visual, tono, fuente)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        titulo,
                        cancion['url'],
                        cancion.get('letra_con_acordes', ''),
                        cancion.get('letra_sin_acordes', ''),
                        cancion.get('estructura_json', '[]'),
                        cancion.get('html_visual', ''),
                        cancion.get('tono', ''),
                        'blogspot'
                    ))
                
                conn.commit()
                logger.info(f"✅ Guardada en DB: {titulo}")
                
        except sqlite3.Error as e:
            logger.exception(f"Error de SQLite al guardar {titulo}")
    
    def ejecutar(self):
        """Ejecuta el scraper completo."""
        logger.info("=" * 70)
        logger.info("SCRAPER CANCIONERO ESCOLAPIO - VERSION CON POSICIONAMIENTO")
        logger.info("=" * 70)
        
        # Obtener página principal
        html = self.obtener_pagina(BASE_URL)
        if not html:
            logger.error("ERROR: No se pudo obtener la página principal")
            return
        
        # Extraer enlaces
        canciones = self.extraer_enlaces_canciones(html)
        logger.info(f"Total: {len(canciones)} canciones")
        
        # Procesar cada canción
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
            
            # Pausa con jitter para no sobrecargar el servidor
            time.sleep(random.uniform(1.0, 2.5))
        
        logger.info("=" * 70)
        logger.info(f"Resumen: {exitosas}/{len(canciones)} canciones procesadas correctamente")
        logger.info("=" * 70)


def main():
    scraper = CancioneroScraper()
    scraper.ejecutar()


if __name__ == "__main__":
    main()
