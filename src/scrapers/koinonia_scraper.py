#!/usr/bin/env python3
"""
Scraper para las lecturas dominicales de servicioskoinonia.org
Extrae: Primera lectura, Salmo, Segunda lectura (si aplica), Evangelio
"""

import requests
from bs4 import BeautifulSoup
import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
import time
import sys

# Configuracion
PROJECT_DIR = Path.home() / "proyectos" / "CCE-M5-Web-Presentaciones"
DB_PATH = PROJECT_DIR / "data" / "db.sqlite3"
BASE_URL = "https://servicioskoinonia.org/biblico/calendario"
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

class KoinoniaScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        
    def obtener_lecturas(self, fecha):
        """
        Obtiene las lecturas para una fecha especifica.
        
        Args:
            fecha: datetime.date o string en formato YYYYMMDD
        
        Returns:
            dict con lecturas o None si error
        """
        if isinstance(fecha, str):
            codigo = fecha
        else:
            codigo = fecha.strftime('%Y%m%d')
        
        url = f"{BASE_URL}/texto.php?codigo={codigo}"
        print(f"Obteniendo lecturas para: {codigo}")
        
        try:
            response = self.session.get(url, timeout=20)
            response.raise_for_status()
            return self.parsear_lecturas(response.text, codigo)
        except Exception as e:
            print(f"  ERROR: {e}")
            return None
    
    def parsear_lecturas(self, html, codigo):
        """Parsea el HTML de las lecturas"""
        soup = BeautifulSoup(html, 'html.parser')
        
        # Extraer informacion basica
        resultado = {
            'fecha': codigo,
            'fuente': 'koinonia',
            'fecha_scraping': datetime.now().isoformat()
        }
        
        # Buscar titulo/celebracion
        titulo = soup.find('h1') or soup.find('h2')
        if titulo:
            resultado['celebracion'] = titulo.get_text(strip=True)
        
        # Extraer secciones de lecturas
        # En Koinonia, cada lectura suele estar en un contenedor especifico
        
        # Primera lectura
        primera = self._extraer_seccion(soup, ['primera lectura', 'lectura del día'])
        if primera:
            resultado['primera_lectura_cita'] = primera.get('cita')
            resultado['primera_lectura_texto'] = primera.get('texto')
        
        # Salmo
        salmo = self._extraer_seccion(soup, ['salmo', 'salmo responsorial'])
        if salmo:
            resultado['salmo_cita'] = salmo.get('cita')
            resultado['salmo_antifona'] = salmo.get('antifona')
            resultado['salmo_texto'] = salmo.get('texto')
        
        # Segunda lectura (si aplica)
        segunda = self._extraer_seccion(soup, ['segunda lectura'])
        if segunda:
            resultado['segunda_lectura_cita'] = segunda.get('cita')
            resultado['segunda_lectura_texto'] = segunda.get('texto')
        
        # Evangelio
        evangelio = self._extraer_seccion(soup, ['evangelio', 'lectura del evangelio'])
        if evangelio:
            resultado['evangelio_cita'] = evangelio.get('cita')
            resultado['evangelio_texto'] = evangelio.get('texto')
        
        # Detectar temporada liturgica y domingo
        resultado.update(self._detectar_temporada(soup, resultado.get('celebracion', '')))
        
        return resultado
    
    def _extraer_seccion(self, soup, posibles_titulos):
        """Extrae una seccion de lectura del HTML"""
        # Buscar por texto del titulo
        for tag in soup.find_all(['h2', 'h3', 'h4', 'p', 'div']):
            texto = tag.get_text(strip=True).lower()
            if any(titulo.lower() in texto for titulo in posibles_titulos):
                # Encontrar el contenido siguiente
                siguiente = tag.find_next_sibling()
                if siguiente:
                    return {
                        'cita': tag.get_text(strip=True),
                        'texto': siguiente.get_text(strip=True)
                    }
        return None
    
    def _detectar_temporada(self, soup, celebracion):
        """Detecta la temporada liturgica y numero de domingo"""
        resultado = {}
        
        # Buscar en el texto
        texto_completo = soup.get_text().lower()
        
        # Temporadas
        temporadas = {
            'adviento': ['adviento', 'i domingo de adviento'],
            'navidad': ['navidad', 'navideño'],
            'cuaresma': ['cuaresma', 'ceniza', 'cuaresma'],
            'pascua': ['pascua', 'resurrección', 'pascual'],
            'ordinario': ['ordinario', 'tiempo ordinario']
        }
        
        for temp, palabras in temporadas.items():
            if any(p in texto_completo for p in palabras):
                resultado['temporada'] = temp
                break
        else:
            resultado['temporada'] = 'ordinario'
        
        # Detectar numero de domingo
        import re
        match = re.search(r'(\w+)\s+domingo', texto_completo, re.IGNORECASE)
        if match:
            resultado['domingo'] = match.group(0)
        
        # Detectar ciclo (A, B, C)
        match = re.search(r'ciclo\s+([ABC])', texto_completo, re.IGNORECASE)
        if match:
            resultado['ciclo'] = match.group(1)
        
        # Color liturgico (basado en temporada)
        colores = {
            'adviento': 'violeta',
            'navidad': 'blanco',
            'cuaresma': 'violeta',
            'pascua': 'blanco',
            'ordinario': 'verde'
        }
        resultado['color_liturgico'] = colores.get(resultado.get('temporada', 'ordinario'), 'verde')
        
        return resultado
    
    def guardar_en_db(self, lecturas):
        """Guarda las lecturas en la base de datos"""
        conn = sqlite3.connect(str(DB_PATH))
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO lecturas 
            (fecha, domingo, temporada, ciclo, color_liturgico,
             primera_lectura_cita, primera_lectura_texto,
             salmo_cita, salmo_antifona, salmo_texto,
             segunda_lectura_cita, segunda_lectura_texto,
             evangelio_cita, evangelio_texto,
             fuente_scraping)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
        conn.close()
        print(f"  ✅ Guardada en DB")
    
    def obtener_proximo_domingo(self):
        """Obtiene las lecturas para el proximo domingo"""
        hoy = datetime.now().date()
        
        # Calcular proximo domingo
        dias_hasta_domingo = (6 - hoy.weekday()) % 7
        if dias_hasta_domingo == 0:
            dias_hasta_domingo = 7
        proximo_domingo = hoy + timedelta(days=dias_hasta_domingo)
        
        print(f"Próximo domingo: {proximo_domingo}")
        return self.obtener_lecturas(proximo_domingo)
    
    def ejecutar(self, fecha=None):
        """Ejecuta el scraper para una fecha especifica o el proximo domingo"""
        print("=" * 70)
        print("SCRAPER LECTURAS KOINONIA")
        print("=" * 70)
        
        if fecha:
            lecturas = self.obtener_lecturas(fecha)
        else:
            lecturas = self.obtener_proximo_domingo()
        
        if lecturas:
            self.guardar_en_db(lecturas)
            print(f"\nCelebración: {lecturas.get('celebracion', 'No detectada')}")
            print(f"Temporada: {lecturas.get('temporada', 'No detectada')}")
            print(f"Color: {lecturas.get('color_liturgico', 'No detectado')}")
        else:
            print("\n❌ No se pudieron obtener las lecturas")
        
        print("=" * 70)

def main():
    scraper = KoinoniaScraper()
    
    # Si se pasa fecha como argumento, usarla
    if len(sys.argv) > 1:
        scraper.ejecutar(sys.argv[1])
    else:
        scraper.ejecutar()

if __name__ == "__main__":
    main()
