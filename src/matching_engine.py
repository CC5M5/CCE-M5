#!/usr/bin/env python3
"""
Motor de matching temático entre lecturas y canciones.
Relaciona las lecturas dominicales con canciones del cancionero por temas comunes.

MEJORAS APLICADAS (basado en análisis de OpenCode + Kimi):
- Logging profesional
- Manejo seguro de conexiones SQLite
- Scoring ponderado más preciso
- Filtrado de resultados por relevancia
- Límite de resultados configurable
"""

import sqlite3
import json
import logging
from pathlib import Path
from collections import Counter

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuracion
PROJECT_DIR = Path(__file__).parent.parent.parent
DB_PATH = PROJECT_DIR / "data" / "db.sqlite3"

# Palabras clave por tema (expandido y ponderado)
TEMAS_PALABRAS = {
    'perdon': {
        'palabras': ['perdon', 'misericordia', 'pecado', 'culpa', 'reconciliacion', 'perdona'],
        'peso': 1.5
    },
    'paz': {
        'palabras': ['paz', 'cordero', 'reconciliacion', 'unidad', 'hermanos', 'concordia'],
        'peso': 1.2
    },
    'esperanza': {
        'palabras': ['esperanza', 'manana', 'futuro', 'nuevo', 'renovar', 'amanecer'],
        'peso': 1.0
    },
    'amor': {
        'palabras': ['amor', 'caridad', 'dios nos ama', 'entrega', 'querer', 'afecto'],
        'peso': 1.3
    },
    'camino': {
        'palabras': ['camino', 'sendero', 'verdad', 'vida', 'seguir', 'andar', 'senda'],
        'peso': 1.1
    },
    'luz': {
        'palabras': ['luz', 'brillar', 'oscuridad', 'iluminar', 'claridad', 'resplandor'],
        'peso': 1.0
    },
    'agua': {
        'palabras': ['agua', 'beber', 'sed', 'manantial', 'rio', 'fuente', 'bautismo'],
        'peso': 1.0
    },
    'pan': {
        'palabras': ['pan', 'comer', 'hambre', 'alimento', 'nutrir', 'mesa', 'cuerpo'],
        'peso': 1.2
    },
    'maria': {
        'palabras': ['maria', 'virgen', 'amparo', 'proteccion', 'madre', 'magnificat'],
        'peso': 1.4
    },
    'espiritu': {
        'palabras': ['espiritu', 'fuego', 'viento', 'pentecostes', 'consolador'],
        'peso': 1.3
    },
    'alabanza': {
        'palabras': ['alabar', 'gloria', 'honor', 'santo', 'adorar', 'cantar', 'loar'],
        'peso': 1.1
    },
    'servicio': {
        'palabras': ['servir', 'humilde', 'pobre', 'ayudar', 'dar', 'servicio', 'ministrar'],
        'peso': 1.0
    },
    'fe': {
        'palabras': ['fe', 'creer', 'confiar', 'esperar', 'firmeza', 'conviccion'],
        'peso': 1.2
    },
    'salvacion': {
        'palabras': ['salvar', 'salvacion', 'libertad', 'redimir', 'rescate', 'liberar'],
        'peso': 1.3
    }
}


class MatchingEngine:
    """Motor de matching temático con scoring ponderado."""
    
    def __init__(self, db_path=None):
        self.db_path = db_path or DB_PATH
    
    def _get_connection(self):
        """Obtiene una conexión a la base de datos."""
        return sqlite3.connect(str(self.db_path))
    
    def extraer_temas_de_texto(self, texto):
        """Extrae temas de un texto con scoring ponderado."""
        if not texto:
            return []
        
        texto_lower = texto.lower()
        temas_encontrados = []
        
        for tema, config in TEMAS_PALABRAS.items():
            score = 0
            palabras_encontradas = []
            
            for palabra in config['palabras']:
                # Contar ocurrencias de cada palabra
                count = texto_lower.count(palabra)
                if count > 0:
                    score += count
                    palabras_encontradas.append(palabra)
            
            if score > 0:
                # Aplicar peso del tema
                score_ponderado = score * config['peso']
                temas_encontrados.append({
                    'tema': tema,
                    'score': score_ponderado,
                    'palabras': palabras_encontradas
                })
        
        # Ordenar por score descendente
        temas_encontrados.sort(key=lambda x: x['score'], reverse=True)
        return temas_encontrados
    
    def analizar_lectura(self, lectura_id):
        """Analiza una lectura y extrae sus temas."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    SELECT primera_lectura_texto, salmo_texto, 
                           segunda_lectura_texto, evangelio_texto
                    FROM lecturas WHERE id = ?
                ''', (lectura_id,))
                
                row = cursor.fetchone()
                if not row:
                    logger.warning(f"No se encontró lectura con ID {lectura_id}")
                    return None
                
                # Combinar todos los textos
                texto_completo = ' '.join([str(c) for c in row if c])
                return self.extraer_temas_de_texto(texto_completo)
                
        except sqlite3.Error as e:
            logger.error(f"Error al analizar lectura {lectura_id}: {e}")
            return None
    
    def analizar_cancion(self, cancion_id):
        """Analiza una canción y extrae sus temas."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    'SELECT letra_sin_acordes FROM canciones WHERE id = ?',
                    (cancion_id,)
                )
                
                row = cursor.fetchone()
                if not row or not row[0]:
                    return None
                
                return self.extraer_temas_de_texto(row[0])
                
        except sqlite3.Error as e:
            logger.error(f"Error al analizar canción {cancion_id}: {e}")
            return None
    
    def calcular_match(self, temas_lectura, temas_cancion):
        """Calcula el score de matching entre temas con ponderación."""
        if not temas_lectura or not temas_cancion:
            return 0
        
        # Crear diccionarios de temas
        dict_lectura = {t['tema']: t['score'] for t in temas_lectura}
        dict_cancion = {t['tema']: t['score'] for t in temas_cancion}
        
        # Temas comunes
        temas_comunes = set(dict_lectura.keys()) & set(dict_cancion.keys())
        
        if not temas_comunes:
            return 0
        
        # Calcular score ponderado
        score_total = 0
        for tema in temas_comunes:
            # Multiplicar scores para dar más peso a coincidencias fuertes
            score_total += dict_lectura[tema] * dict_cancion[tema]
        
        # Normalizar por número de temas
        score_normalizado = score_total / (len(temas_comunes) ** 0.5)
        
        return score_normalizado
    
    def encontrar_canciones_para_lectura(self, lectura_id, limite=5, score_minimo=1.0):
        """Encuentra las mejores canciones para una lectura."""
        logger.info(f"Buscando canciones para lectura {lectura_id}")
        
        temas_lectura = self.analizar_lectura(lectura_id)
        if not temas_lectura:
            logger.warning("No se pudieron extraer temas de la lectura")
            return []
        
        logger.info(f"Temas encontrados: {[t['tema'] for t in temas_lectura[:3]]}")
        
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('SELECT id, titulo FROM canciones')
                canciones = cursor.fetchall()
                
                matches = []
                for cancion_id, titulo in canciones:
                    temas_cancion = self.analizar_cancion(cancion_id)
                    if temas_cancion:
                        score = self.calcular_match(temas_lectura, temas_cancion)
                        if score >= score_minimo:
                            matches.append({
                                'cancion_id': cancion_id,
                                'titulo': titulo,
                                'score': round(score, 2),
                                'temas_comunes': [
                                    t['tema'] for t in temas_cancion 
                                    if t['tema'] in [tl['tema'] for tl in temas_lectura]
                                ]
                            })
                
                # Ordenar por score y limitar
                matches.sort(key=lambda x: x['score'], reverse=True)
                return matches[:limite]
                
        except sqlite3.Error as e:
            logger.error(f"Error al buscar canciones: {e}")
            return []
    
    def guardar_match(self, lectura_id, cancion_id, score, momento_liturgico='general'):
        """Guarda un match en la base de datos."""
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                
                # Crear tabla si no existe
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS matches (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        lectura_id INTEGER,
                        cancion_id INTEGER,
                        score REAL,
                        momento_liturgico TEXT,
                        fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (lectura_id) REFERENCES lecturas(id),
                        FOREIGN KEY (cancion_id) REFERENCES canciones(id)
                    )
                ''')
                
                cursor.execute('''
                    INSERT INTO matches (lectura_id, cancion_id, score, momento_liturgico)
                    VALUES (?, ?, ?, ?)
                ''', (lectura_id, cancion_id, score, momento_liturgico))
                
                conn.commit()
                logger.info(f"✅ Match guardado: lectura {lectura_id} -> canción {cancion_id}")
                
        except sqlite3.Error as e:
            logger.error(f"Error al guardar match: {e}")


def probar_matching():
    """Prueba el motor de matching."""
    logger.info("=" * 70)
    logger.info("MOTOR DE MATCHING TEMATICO")
    logger.info("=" * 70)
    
    engine = MatchingEngine()
    
    # Verificar si hay lecturas en la DB
    try:
        with engine._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT id, celebracion FROM lecturas LIMIT 1')
            lectura = cursor.fetchone()
    except sqlite3.Error:
        lectura = None
    
    if not lectura:
        logger.warning("No hay lecturas en la base de datos.")
        logger.info("Ejecutar primero: python src/scrapers/koinonia_scraper.py")
        return
    
    lectura_id, celebracion = lectura
    logger.info(f"Lectura: {celebracion} (ID: {lectura_id})")
    
    # Encontrar canciones
    matches = engine.encontrar_canciones_para_lectura(lectura_id, limite=5)
    
    if matches:
        logger.info(f"\n✅ Encontradas {len(matches)} coincidencias:")
        for i, match in enumerate(matches, 1):
            logger.info(f"\n{i}. {match['titulo']}")
            logger.info(f"   Score: {match['score']}")
            logger.info(f"   Temas: {', '.join(match['temas_comunes'])}")
    else:
        logger.info("\n❌ No se encontraron coincidencias")
    
    logger.info("=" * 70)


if __name__ == "__main__":
    probar_matching()
