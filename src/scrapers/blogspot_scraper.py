#!/usr/bin/env python3
"""
Scraper completo para el Cancionero Escolapio de CCE M5 Music (Blogspot)
Extrae TODAS las canciones, las parsea y guarda en la base de datos
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

# Importar parser
sys.path.insert(0, str(PROJECT_DIR / "src" / "parsers"))
from acordes_parser import AcordesParser

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
        """Obtiene y parsea una cancion"""
        html = self.obtener_pagina(url)
        if not html:
            return None
        
        soup = BeautifulSoup(html, 'html.parser')
        
        # Buscar el contenido principal
        post_body = soup.find('div', class_='post-body') or soup.find('div', class_='entry-content')
        if not post_body:
            return None
        
        # Extraer texto
        texto_completo = post_body.get_text('\n').strip()
        
        # Separar letra y acordes
        resultado = self.parser.separar_letra_y_acordes(texto_completo)
        
        # Detectar tono y momento
        tono = self.parser.detectar_tono(resultado['acordes'])
        
        return {
            'titulo': None,  # Se asignara despues
            'url': url,
            'letra_con_acordes': resultado['letra'] + '\n\n' + resultado['acordes'],
            'letra_sin_acordes': resultado['letra'],
            'acordes_json': json.dumps(resultado['acordes_lista']),
            'tono': tono,
            'fuente': 'blogspot'
        }
    
    def guardar_en_db(self, cancion):
        """Guarda una cancion en la base de datos"""
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO canciones 
            (titulo, titulo_url, letra_con_acordes, letra_sin_acordes, acordes_json, tono, fuente)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            cancion['titulo'],
            cancion['url'],
            cancion.get('letra_con_acordes', ''),
            cancion.get('letra_sin_acordes', ''),
            cancion.get('acordes_json', '[]'),
            cancion.get('tono', ''),
            'blogspot'
        ))
        
        conn.commit()
        conn.close()
    
    def ejecutar(self):
        """Ejecuta el scraper completo"""
        print("=" * 70)
        print("SCRAPER CANCIONERO ESCOLAPIO - VERSION COMPLETA")
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
