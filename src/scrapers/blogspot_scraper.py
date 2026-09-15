#!/usr/bin/env python3
"""
Scraper completo para el Cancionero Escolapio - VERSION CON POSICIONAMIENTO
Extrae TODAS las canciones con acordes posicionados y guarda en la base de datos.
"""

import json
import logging
import os
import random
import re
import sqlite3
import time
from pathlib import Path
from typing import Any, Optional
from urllib.parse import unquote, urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from parsers.acordes_parser_v3 import AcordesParser

# Detecci\u00f3n de momento lit\u00fargico basada en texto del cancionero
PALABRAS_MOMENTO = {
    "entrada": ["entrada", "abrir", "puertas", "preparad el camino"],
    "perdon": ["perdon", "misericordia", "kyrie", "senor ten piedad", "cristo ten piedad"],
    "gloria": ["gloria", "glorificamos", "alabanza", "gloria a dios"],
    "salmo": ["salmo", "sal 39", "salmo 39", "aqui estoy"],
    "aleluya": ["aleluya", "aleluya, aleluya"],
    "ofertorio": ["ofertorio", "ofrenda", "pan", "vino"],
    "santo": ["santo", "santo santo santo", "hosanna"],
    "padre_nuestro": ["padre nuestro", "padrenuestro"],
    "paz": ["paz", "senor dame tu paz", "paz y bien"],
    "comunion": ["comunion", "cuerpo", "sangre", "pan de vida"],
    "maria": ["maria", "ave maria", "madre", "magnificat"],
    "despedida": ["despedida", "envia", "espiritu", "vayamos"],
}


def detectar_momento_liturgico(texto: str) -> str:
    texto_lower = texto.lower()
    conteos = {}
    for momento, palabras in PALABRAS_MOMENTO.items():
        conteos[momento] = sum(1 for p in palabras if p in texto_lower)
    max_momento = max(conteos, key=conteos.get, default="")
    return max_momento if conteos.get(max_momento, 0) > 0 else "general"


# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuracion con variable de entorno
PROJECT_DIR = Path(os.environ.get("CCE_PROJECT_DIR", Path.home() / "proyectos" / "CCE-M5-Web-Presentaciones"))
DB_PATH = PROJECT_DIR / "data" / "db.sqlite3"
BASE_URL = "https://ccem5music.blogspot.com/p/cancionero-escolapio.html"
ALLOWED_HOSTS = {"ccem5music.blogspot.com"}
PROGRESS_PATH = PROJECT_DIR / "data" / "scraper_progress.json"
MAX_RESPONSE_SIZE = 10 * 1024 * 1024  # 10 MB

# User-Agent rotativo para evitar bloqueos
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
]

# Atributos/eventos peligrosos a eliminar para sanitizacion visual
DANGEROUS_ATTRS_RE = re.compile(r'^(on|style|formaction|xlink:href|data|xmlns)', re.IGNORECASE)
DANGEROUS_TAGS = {'script', 'style', 'iframe', 'object', 'embed', 'form', 'input', 'button', 'textarea'}


def _normalizar_url(url: str, base_url: str = BASE_URL) -> Optional[str]:
    url_completa = urljoin(base_url, url)
    parsed = urlparse(url_completa)
    if parsed.scheme != 'https':
        return None
    netloc = parsed.netloc.lower()
    if netloc not in ALLOWED_HOSTS:
        return None
    path = unquote(parsed.path)
    url_normalizada = f"{parsed.scheme}://{netloc}{path}"
    return url_normalizada.split('#')[0].split('?')[0].rstrip('/')


def _sanitize_html_visual(soup: BeautifulSoup) -> str:
    for tag in list(soup.find_all()):
        if tag.name in DANGEROUS_TAGS:
            tag.decompose()
            continue
        for attr in list(tag.attrs.keys()):
            if DANGEROUS_ATTRS_RE.match(attr):
                del tag.attrs[attr]
    return str(soup)


class CancioneroScraper:
    """Scraper robusto para el cancionero escolapio con reintentos y validacion."""

    def __init__(self) -> None:
        self.session = requests.Session()
        retry = Retry(
            total=5,
            backoff_factor=0.5,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods={"HEAD", "GET"}
        )
        adapter = HTTPAdapter(max_retries=retry)
        self.session.mount('https://', adapter)

        self.db_path = DB_PATH
        self.db: Optional[sqlite3.Connection] = None
        self._init_db()
        self._progress: dict[str, Any] = self._load_progress()

    def __enter__(self) -> 'CancioneroScraper':
        if self.db is None or self.db.total_changes < 0:
            self.db = self._open_connection()
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        if self.db:
            self.db.close()
            self.db = None
        if self.session:
            self.session.close()

    def _open_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def _init_db(self) -> None:
        os.makedirs(self.db_path.parent, exist_ok=True)
        self.db = self._open_connection()
        try:
            self.db.execute('''
                CREATE TABLE IF NOT EXISTS canciones (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    titulo TEXT NOT NULL,
                    titulo_url TEXT NOT NULL UNIQUE,
                    letra_con_acordes TEXT,
                    letra_sin_acordes TEXT,
                    estructura_json TEXT,
                    html_visual TEXT,
                    html_original TEXT,
                    tono TEXT,
                    momento_liturgico TEXT,
                    fuente TEXT
                )
            ''')
            self.db.commit()
            logger.info("Base de datos inicializada con WAL mode")
        except sqlite3.Error:
            logger.exception("Error inicializando base de datos")
            raise

    def _load_progress(self) -> dict[str, Any]:
        if PROGRESS_PATH.exists():
            try:
                with open(PROGRESS_PATH, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError):
                logger.exception("Error cargando progreso previo")
        return {'procesadas': [], 'fallidas': []}

    def _save_progress(self) -> None:
        os.makedirs(PROGRESS_PATH.parent, exist_ok=True)
        with open(PROGRESS_PATH, 'w', encoding='utf-8') as f:
            json.dump(self._progress, f, ensure_ascii=False, indent=2)

    def _get_page(self, url: str) -> Optional[bytes]:
        headers = {'User-Agent': random.choice(USER_AGENTS)}
        try:
            response = self.session.get(url, headers=headers, timeout=15, stream=True)
            response.raise_for_status()
            response.raise_for_status()
            content = b''
            for chunk in response.iter_content(chunk_size=8192):
                content += chunk
                if len(content) > MAX_RESPONSE_SIZE:
                    logger.warning(f"Respuesta demasiado grande para {url}")
                    return None
            return content
        except requests.exceptions.RequestException:
            logger.exception(f"Error al obtener {url}")
            return None

    def extraer_enlaces_canciones(self, html_bytes: bytes) -> list[dict[str, str]]:
        soup = BeautifulSoup(html_bytes, 'lxml')
        canciones: list[dict[str, str]] = []
        seen_urls: set[str] = set()

        for enlace in soup.find_all('a', href=True):
            href = enlace['href']
            texto = enlace.get_text(strip=True)

            if not texto or len(texto) <= 2:
                continue

            url_normalizada = _normalizar_url(href)
            if not url_normalizada:
                continue

            parsed = urlparse(url_normalizada)
            if '/p/' not in parsed.path:
                continue

            if url_normalizada == BASE_URL or '/cancionero-escolapio' in parsed.path:
                continue

            if url_normalizada in seen_urls:
                continue

            seen_urls.add(url_normalizada)
            canciones.append({
                'titulo': texto,
                'url': url_normalizada
            })

        logger.info(f"Encontradas {len(canciones)} canciones validas")
        return canciones

    def obtener_cancion(self, url: str) -> Optional[dict[str, Any]]:
        html_bytes = self._get_page(url)
        if not html_bytes:
            return None

        try:
            soup = BeautifulSoup(html_bytes, 'lxml')
        except Exception:
            logger.exception(f"Error parseando HTML de {url}")
            return None

        post_body = soup.find('div', class_='post-body') or soup.find('div', class_='entry-content')
        if not post_body:
            logger.warning(f"No se encontro contenido en {url}")
            return None

        titulo_h1 = soup.find('h1', class_='post-title')
        titulo_pagina = titulo_h1.get_text(strip=True) if titulo_h1 else None

        # Copia para sanitizar HTML visual
        visual_soup = BeautifulSoup(str(post_body), 'lxml')
        html_visual = _sanitize_html_visual(visual_soup)
        html_original = str(post_body)

        for tag in post_body.find_all(['script', 'style', 'nav', 'footer', 'aside', 'iframe']):
            tag.decompose()

        texto_completo = post_body.get_text('\n').strip()

        if not texto_completo or len(texto_completo) < 20:
            logger.warning(f"Cancion sin contenido suficiente en {url}")
            return None

        try:
            parser = AcordesParser()
            estructura = parser.parsear_cancion_completa(texto_completo)
        except Exception:
            logger.exception(f"Error parseando cancion {url}")
            return None

        if not estructura:
            logger.warning(f"No se pudo parsear estructura en {url}")
            return None

        try:
            tono = parser.detectar_tono(estructura)
            html_visual = parser.generar_html_visual(estructura)
            momento_liturgico = detectar_momento_liturgico(texto_completo)
        except Exception:
            logger.exception(f"Error generando representacion visual de {url}")
            tono = ''
            html_visual = ''
            momento_liturgico = ''

        lineas_letra = []
        for linea in estructura:
            if linea.tipo in ("letra", "acordes_letra"):
                lineas_letra.append(linea.letra)
            elif linea.tipo in ("sección",):
                if linea.texto:
                    lineas_letra.append(linea.texto)

        return {
            'titulo': titulo_pagina,
            'url': url,
            'letra_con_acordes': texto_completo,
            'letra_sin_acordes': '\n'.join(lineas_letra),
            'estructura_json': json.dumps(
                [
                    {
                        "tipo": l.tipo,
                        "acordes": [{"acorde": a.acorde, "posicion": a.posicion} for a in l.acordes],
                        "letra": l.letra,
                        "texto": l.texto,
                    }
                    for l in estructura
                ],
                ensure_ascii=False,
            ),
            'html_visual': html_visual,
            'html_original': html_original,
            'tono': tono,
            'momento_liturgico': momento_liturgico,
            'fuente': 'blogspot'
        }

    def guardar_lote(self, canciones: list[dict[str, Any]]) -> None:
        if not canciones or self.db is None:
            return

        registros_insert: list[tuple[Any, ...]] = []
        registros_update: list[tuple[Any, ...]] = []

        for cancion in canciones:
            titulo = (cancion.get('titulo') or cancion.get('url') or "Sin titulo").strip()
            url = cancion.get('url', '')

            cursor = self.db.cursor()
            cursor.execute('SELECT id FROM canciones WHERE titulo_url = ?', (url,))
            existente = cursor.fetchone()

            if existente:
                registros_update.append((
                    titulo,
                    cancion.get('letra_con_acordes', ''),
                    cancion.get('letra_sin_acordes', ''),
                    cancion.get('estructura_json', '[]'),
                    cancion.get('html_visual', ''),
                    cancion.get('html_original', ''),
                    cancion.get('tono', ''),
                    cancion.get('momento_liturgico', ''),
                    'blogspot',
                    url
                ))
            else:
                registros_insert.append((
                    titulo,
                    url,
                    cancion.get('letra_con_acordes', ''),
                    cancion.get('letra_sin_acordes', ''),
                    cancion.get('estructura_json', '[]'),
                    cancion.get('html_visual', ''),
                    cancion.get('html_original', ''),
                    cancion.get('tono', ''),
                    cancion.get('momento_liturgico', ''),
                    'blogspot'
                ))

        try:
            with self.db:
                if registros_insert:
                    self.db.executemany('''
                        INSERT INTO canciones
                        (titulo, titulo_url, letra_con_acordes, letra_sin_acordes,
                         estructura_json, html_visual, html_original, tono, momento_liturgico, fuente)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', registros_insert)
                if registros_update:
                    self.db.executemany('''
                        UPDATE canciones SET
                            titulo = ?,
                            letra_con_acordes = ?,
                            letra_sin_acordes = ?,
                            estructura_json = ?,
                            html_visual = ?,
                            html_original = ?,
                            tono = ?,
                            momento_liturgico = ?,
                            fuente = ?
                        WHERE titulo_url = ?
                    ''', registros_update)
            logger.info(f"Guardado lote de {len(canciones)} canciones")
        except sqlite3.Error:
            logger.exception("Error de SQLite al guardar lote")

    def ejecutar(self) -> None:
        logger.info("=" * 70)
        logger.info("SCRAPER CANCIONERO ESCOLAPIO - VERSION CON POSICIONAMIENTO")
        logger.info("=" * 70)

        html = self._get_page(BASE_URL)
        if not html:
            logger.error("ERROR: No se pudo obtener la pagina principal")
            return

        canciones = self.extraer_enlaces_canciones(html)
        logger.info(f"Total: {len(canciones)} canciones")

        ya_procesadas = set(self._progress.get('procesadas', []))
        lote: list[dict[str, Any]] = []
        lote_size = 10
        exitosas = 0
        fallidas = 0

        for i, cancion_info in enumerate(canciones, 1):
            url = cancion_info['url']
            if url in ya_procesadas:
                logger.info(f"[{i:2d}/{len(canciones):2d}] Saltando ya procesada: {cancion_info['titulo']}")
                continue

            logger.info(f"[{i:2d}/{len(canciones):2d}] {cancion_info['titulo']}")

            try:
                datos = self.obtener_cancion(url)
            except Exception:
                logger.exception(f"Error inesperado procesando {url}")
                datos = None

            if datos:
                if not datos['titulo']:
                    datos['titulo'] = cancion_info['titulo']
                lote.append(datos)
                self._progress['procesadas'].append(url)
                exitosas += 1
            else:
                self._progress['fallidas'].append(url)
                fallidas += 1
                logger.warning(f"  No se pudo procesar: {cancion_info['titulo']}")

            if len(lote) >= lote_size:
                self.guardar_lote(lote)
                self._save_progress()
                lote = []

            time.sleep(random.uniform(1.0, 2.5))

        if lote:
            self.guardar_lote(lote)
            self._save_progress()

        logger.info("=" * 70)
        logger.info(f"Resumen: {exitosas}/{len(canciones)} canciones procesadas correctamente, {fallidas} fallidas")
        logger.info("=" * 70)


def main() -> None:
    with CancioneroScraper() as scraper:
        scraper.ejecutar()


if __name__ == "__main__":
    main()
