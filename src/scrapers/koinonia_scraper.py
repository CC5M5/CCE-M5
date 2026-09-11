#!/usr/bin/env python3
"""
Scraper para las lecturas dominicales de servicioskoinonia.org
Extrae: Primera lectura, Salmo, Segunda lectura (si aplica), Evangelio
"""

import logging
import os
import re
import sqlite3
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional
from zoneinfo import ZoneInfo

import requests
import requests_cache
from bs4 import BeautifulSoup, Tag
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuracion
PROJECT_DIR = Path(os.environ.get('CCE_PROJECT_DIR', Path(__file__).parent.parent.parent))
DB_PATH = PROJECT_DIR / "data" / "db.sqlite3"
BASE_URL = "https://servicioskoinonia.org/biblico/calendario"
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}
FECHA_CODIGO_RE = re.compile(r'^\d{8}$')
CITA_RE = re.compile(
    r'(?:\d+(?:\.\s*\d+(?:\s*,\s*\d+[-–]\d+)?)?\s+)?'
    r'[A-Z][a-zA-Z]{0,3}\s*\d+(?:,\s*\d+[-–]\d+|\.\s*\d+(?:,\s*\d+)?)?'
)


class KoinoniaClient:
    """Cliente HTTP con cache y reintentos para servicioskoinonia.org."""

    def __init__(self, cache_name: Optional[str] = None, ttl_seconds: int = 43200) -> None:
        self.cache_name = cache_name or str(PROJECT_DIR / "data" / "koinonia_cache")
        self.session = requests_cache.CachedSession(
            self.cache_name,
            expire_after=ttl_seconds,
            backend='sqlite',
        )
        self.session.headers.update(HEADERS)
        retry = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504]
        )
        adapter = HTTPAdapter(max_retries=retry)
        self.session.mount('https://', adapter)
        self.session.mount('http://', adapter)

    def __enter__(self) -> 'KoinoniaClient':
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    def get(self, url: str) -> Optional[str]:
        """Obtiene una pagina web con cache y reintentos."""
        try:
            response = self.session.get(url, timeout=20)
            response.raise_for_status()
            return response.content.decode('utf-8', errors='replace')
        except requests.exceptions.RequestException as e:
            logger.error("Error al obtener %s: %s", url, e)
            return None

    def close(self) -> None:
        """Cierra la sesion HTTP subyacente."""
        self.session.close()


class KoinoniaParser:
    """Parser HTML de las lecturas de Koinonia."""

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

    def parse(self, html: str, fecha_codigo: str) -> dict:
        """Parsea el HTML de las lecturas con selectores robustos."""
        soup = BeautifulSoup(html, 'html.parser')

        resultado = {
            'fecha': self._normalizar_fecha(fecha_codigo),
            'fuente': 'koinonia',
            'fecha_scraping': datetime.now().isoformat(),
        }

        titulo = soup.find('h1') or soup.find('h2')
        if titulo:
            resultado['celebracion'] = titulo.get_text(strip=True)

        primera = self._extraer_seccion(soup, ['primera lectura', 'lectura del día'])
        if primera:
            resultado['primera_lectura_cita'] = primera.get('cita')
            resultado['primera_lectura_texto'] = primera.get('texto')

        salmo = self._extraer_seccion(soup, ['salmo', 'salmo responsorial'])
        if salmo:
            resultado['salmo_cita'] = salmo.get('cita')
            resultado['salmo_antifona'] = salmo.get('antifona')
            resultado['salmo_texto'] = salmo.get('texto')

        segunda = self._extraer_seccion(soup, ['segunda lectura'])
        if segunda:
            resultado['segunda_lectura_cita'] = segunda.get('cita')
            resultado['segunda_lectura_texto'] = segunda.get('texto')

        evangelio = self._extraer_seccion(soup, ['evangelio', 'lectura del evangelio'])
        if evangelio:
            resultado['evangelio_cita'] = evangelio.get('cita')
            resultado['evangelio_texto'] = evangelio.get('texto')

        resultado.update(self._detectar_temporada(soup, resultado.get('celebracion', '')))

        self._validar_lecturas(resultado)
        return resultado

    def _extraer_seccion(self, soup: BeautifulSoup, posibles_titulos: list[str]) -> Optional[dict]:
        """Extrae una seccion de lectura usando find_next_sibling."""
        for tag in soup.find_all(['h2', 'h3', 'h4', 'p', 'div']):
            texto = tag.get_text(strip=True).lower()
            if any(titulo.lower() in texto for titulo in posibles_titulos):
                siguiente = tag.find_next_sibling()
                if siguiente:
                    return {
                        'cita': self._extraer_cita(tag),
                        'texto': siguiente.get_text(strip=True),
                    }
        return None

    def _extraer_cita(self, tag: Tag) -> Optional[str]:
        """Extrae la cita biblica real del titulo usando regex."""
        texto = tag.get_text(strip=True)
        match = CITA_RE.search(texto)
        return match.group(0) if match else None

    def _detectar_temporada(self, soup: BeautifulSoup, celebracion: str) -> dict:
        """Detecta la temporada liturgica de forma precisa."""
        resultado: dict = {}
        texto_completo = soup.get_text().lower()

        for temp, palabras in self.temporadas.items():
            if any(p in texto_completo for p in palabras):
                resultado['temporada'] = temp
                break
        else:
            resultado['temporada'] = 'ordinario'

        match = re.search(r'(\d+)[º°]?\s*domingo', texto_completo, re.IGNORECASE)
        if match:
            resultado['domingo'] = f"Domingo {match.group(1)}"

        match = re.search(r'ciclo\s+([ABC])', texto_completo, re.IGNORECASE)
        if match:
            resultado['ciclo'] = match.group(1)

        resultado['color_liturgico'] = self.colores.get(resultado.get('temporada', 'ordinario'), 'verde')
        return resultado

    def _normalizar_fecha(self, fecha_codigo: str) -> str:
        """Normaliza fecha de YYYYMMDD a ISO format."""
        fecha = datetime.strptime(fecha_codigo, '%Y%m%d')
        return fecha.date().isoformat()

    def _validar_lecturas(self, resultado: dict) -> None:
        """Valida que existan al menos primera lectura, salmo y evangelio."""
        faltantes = []
        for campo in ['primera_lectura_texto', 'salmo_texto', 'evangelio_texto']:
            if not resultado.get(campo):
                faltantes.append(campo)
        if faltantes:
            raise ValueError(f"Lecturas incompletas. Faltan: {', '.join(faltantes)}")


class KoinoniaRepository:
    """Repositorio SQLite para lecturas de Koinonia."""

    def __init__(self, db_path: Optional[Path] = None) -> None:
        self.db_path = db_path or DB_PATH

    def guardar(self, lecturas: dict) -> None:
        """Guarda las lecturas en la base de datos de forma segura."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            with sqlite3.connect(str(self.db_path)) as conn:
                cursor = conn.cursor()
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
                    'koinonia',
                ))
                conn.commit()
                logger.info("Lecturas guardadas para %s", lecturas.get('fecha'))
        except sqlite3.Error as e:
            logger.error("Error de SQLite al guardar lecturas: %s", e)


class KoinoniaScraper:
    """Orquesta cliente, parser y repositorio de lecturas."""

    def __init__(self, client: Optional[KoinoniaClient] = None, repo: Optional[KoinoniaRepository] = None) -> None:
        self.client = client or KoinoniaClient()
        self.parser = KoinoniaParser()
        self.repo = repo or KoinoniaRepository()

    def obtener_lecturas(self, fecha: datetime) -> Optional[dict]:
        """Obtiene las lecturas para una fecha especifica."""
        codigo = fecha.strftime('%Y%m%d')
        if not FECHA_CODIGO_RE.match(codigo):
            raise ValueError(f"Codigo de fecha invalido: {codigo}")
        url = f"{BASE_URL}/texto.php?codigo={codigo}"
        logger.info("Obteniendo lecturas para: %s", codigo)
        html = self.client.get(url)
        if not html:
            return None
        return self.parser.parse(html, codigo)

    def obtener_proximo_domingo(self) -> Optional[dict]:
        """Obtiene las lecturas para el proximo domingo (incluyendo hoy si es domingo)."""
        madrid = ZoneInfo('Europe/Madrid')
        ahora = datetime.now(madrid)
        hoy = ahora.date()
        dias_hasta_domingo = (6 - hoy.weekday()) % 7
        proximo_domingo = hoy + timedelta(days=dias_hasta_domingo)
        logger.info("Proximo domingo: %s", proximo_domingo)
        return self.obtener_lecturas(datetime.combine(proximo_domingo, ahora.time(), tzinfo=madrid))

    def guardar_en_db(self, lecturas: dict) -> None:
        """Delega el guardado en el repositorio."""
        self.repo.guardar(lecturas)
