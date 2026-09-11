#!/usr/bin/env python3
"""
Scraper completo para el Cancionero Escolapio - VERSION CON POSICIONAMIENTO
Extrae TODAS las canciones con acordes posicionados y guarda en la base de datos
"""

import requests
from bs4 import BeautifulSoup
import json
import re
import sqlite3
import sys
from pathlib import Path
import time

# Configuracion
PROJECT_DIR = Path.home() / "proyectos" / "CCE-M5-Web-Presentaciones"
DB_PATH = PROJECT_DIR / "data" / "db.sqlite3"
OUTPUT_DIR = PROJECT_DIR / "data" / "canciones"
BASE_URL = "https://ccem5music.blogspot.com/p/cancionero-escolapio.html"
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

# Importar parser V2
sys.path.insert(0, str(PROJECT_DIR / "src" / "parsers"))
from acordes_parser_v2 import AcordesParser

class CancioneroScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        self.parser = AcordesParser()
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        
    def obtener_pagina(self, url):
        """Obtiene una pagina web"""
        try:
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            return response.text
        except Exception as e:
            print(f"  ERROR al obtener {url}: {e}")
            return None
    
    def extraer_enlaces_canciones(self, html):
        """Extrae los enlaces a cada cancion desde la pagina del cancionero"""
        soup = BeautifulSoup(html, 'html.parser')
        canciones = []
        
        # Buscar enlaces que apunten a paginas de canciones
        for enlace in soup.find_all('a', href=True):
            href = enlace['href']
            texto = enlace.get_text(strip=True)
            
            # Filtrar enlaces que parecen ser canciones
            if '/p/' in href and texto and len(texto) > 2:
                url_completa = href if href.startswith('http') else f"https://ccem5music.blogspot.com{href}"
                
                # Evitar duplicados
                if not any(c['url'] == url_completa for c in canciones):
                    canciones.append({
                        'titulo': texto,
                        'url': url_completa
                    })
        
        return canciones
    
    def obtener_cancion(self, url):
        """Obtiene y parsea una cancion con formato posicionado"""
        html = self.obtener_pagina(url)
        if not html:
            return None
        
        soup = BeautifulSoup(html, 'html.parser')
        
        # Buscar el contenido principal
        post_body = soup.find('div', class_='post-body') or soup.find('div', class_='entry-content')
        if not post_body:
            return None
        
        # Extraer texto con formato preservado
        # Usamos get_text con separador para mantener la estructura de lineas
        texto_completo = post_body.get_text('\n').strip()
        
        # Guardar HTML original como backup
        html_original = str(post_body)
        
        # Parsear con el nuevo parser
        estructura = self.parser.parsear_cancion_completa(texto_completo)
        
        # Detectar tono
        tono = self.parser.detectar_tono(estructura)
        
        # Generar HTML visual
        html_visual = self.parser.generar_html_visual(estructura)
        
        return {
            'titulo': None,
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
        """Guarda una cancion en la base de datos"""
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()
        
        # Verificar si existe columna estructura_json
        cursor.execute("PRAGMA table_info(canciones)")
        columnas = [row[1] for row in cursor.fetchall()]
        
        if 'estructura_json' not in columnas:
            # Agregar nueva columna
            cursor.execute('ALTER TABLE canciones ADD COLUMN estructura_json TEXT')
            cursor.execute('ALTER TABLE canciones ADD COLUMN html_visual TEXT')
            cursor.execute('ALTER TABLE canciones ADD COLUMN html_original TEXT')
            conn.commit()
        
        cursor.execute('''
            INSERT OR REPLACE INTO canciones 
            (titulo, titulo_url, letra_con_acordes, letra_sin_acordes, acordes_json, 
             estructura_json, html_visual, html_original, tono, fuente)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            cancion['titulo'],
            cancion['url'],
            cancion.get('letra_con_acordes', ''),
            cancion.get('letra_sin_acordes', ''),
            json.dumps([]),  # acordes_json legacy
            cancion.get('estructura_json', '[]'),
            cancion.get('html_visual', ''),
            cancion.get('html_original', ''),
            cancion.get('tono', ''),
            'blogspot'
        ))
        
        conn.commit()
        conn.close()
    
    def ejecutar(self):
        """Ejecuta el scraper completo"""
        print("=" * 70)
        print("SCRAPER CANCIONERO ESCOLAPIO - VERSION CON POSICIONAMIENTO")
        print("=" * 70)
        
        # Obtener pagina principal
        html = self.obtener_pagina(BASE_URL)
        if not html:
            print("ERROR: No se pudo obtener la pagina principal")
            return
        
        # Extraer enlaces
        canciones = self.extraer_enlaces_canciones(html)
        print(f"Encontradas {len(canciones)} canciones")
        print()
        
        # Procesar cada cancion
        exitosas = 0
        for i, cancion_info in enumerate(canciones, 1):
            print(f"[{i:2d}/{len(canciones):2d}] {cancion_info['titulo']}")
            
            datos = self.obtener_cancion(cancion_info['url'])
            if datos:
                datos['titulo'] = cancion_info['titulo']
                self.guardar_en_db(datos)
                print(f"      ✅ Guardada (Tono: {datos['tono']})")
                exitosas += 1
            else:
                print(f"      ❌ No se pudo procesar")
            
            # Pausa para no sobrecargar el servidor
            time.sleep(1)
        
        print()
        print("=" * 70)
        print(f"Resumen: {exitosas}/{len(canciones)} canciones procesadas correctamente")
        print(f"=" * 70)

def main():
    scraper = CancioneroScraper()
    scraper.ejecutar()

if __name__ == "__main__":
    main()
