#!/usr/bin/env python3
"""
Motor de matching temático entre lecturas y canciones.
Relaciona las lecturas dominicales con canciones del cancionero por temas comunes.
"""

import sqlite3
import json
from pathlib import Path

PROJECT_DIR = Path.home() / "proyectos" / "CCE-M5-Web-Presentaciones"
DB_PATH = PROJECT_DIR / "data" / "db.sqlite3"

# Palabras clave por tema
TEMAS_PALABRAS = {
    'perdon': ['perdon', 'misericordia', 'pecado', 'culpa', 'reconciliacion'],
    'paz': ['paz', 'cordero', 'reconciliacion', 'unidad', 'hermanos'],
    'esperanza': ['esperanza', 'manana', 'futuro', 'nuevo', 'renovar'],
    'amor': ['amor', 'caridad', 'dios nos ama', 'entrega'],
    'camino': ['camino', 'sendero', 'verdad', 'vida', 'seguir'],
    'luz': ['luz', 'brillar', 'oscuridad', 'iluminar'],
    'agua': ['agua', 'beber', 'sed', 'manantial', 'rio'],
    'pan': ['pan', 'comer', 'hambre', 'alimento', 'nutrir'],
    'maria': ['maria', 'virgen', 'amparo', 'proteccion', 'madre'],
    'espiritu': ['espiritu', 'fuego', 'viento', 'pentecostes'],
    'alabanza': ['alabar', 'gloria', 'honor', 'santo', 'adorar'],
    'servicio': ['servir', 'humilde', 'pobre', 'ayudar', 'dar'],
    'fe': ['fe', 'creer', 'confiar', 'esperar'],
    'salvacion': ['salvar', 'salvacion', 'libertad', 'redimir']
}

class MatchingEngine:
    def __init__(self):
        self.conn = sqlite3.connect(str(DB_PATH))
        self.cursor = self.conn.cursor()
    
    def extraer_temas_de_texto(self, texto):
        """Extrae temas de un texto basado en palabras clave"""
        if not texto:
            return []
        
        texto_lower = texto.lower()
        temas_encontrados = []
        
        for tema, palabras in TEMAS_PALABRAS.items():
            score = 0
            for palabra in palabras:
                if palabra in texto_lower:
                    score += 1
            
            if score > 0:
                temas_encontrados.append({
                    'tema': tema,
                    'score': score,
                    'palabras': [p for p in palabras if p in texto_lower]
                })
        
        # Ordenar por score
        temas_encontrados.sort(key=lambda x: x['score'], reverse=True)
        return temas_encontrados
    
    def analizar_lectura(self, lectura_id):
        """Analiza una lectura y extrae sus temas"""
        self.cursor.execute('''
            SELECT primera_lectura_texto, salmo_texto, segunda_lectura_texto, evangelio_texto
            FROM lecturas WHERE id = ?
        ''', (lectura_id,))
        
        row = self.cursor.fetchone()
        if not row:
            return None
        
        # Combinar todos los textos
        texto_completo = ' '.join([str(c) for c in row if c])
        
        return self.extraer_temas_de_texto(texto_completo)
    
    def analizar_cancion(self, cancion_id):
        """Analiza una canción y extrae sus temas"""
        self.cursor.execute('''
            SELECT letra_sin_acordes FROM canciones WHERE id = ?
        ''', (cancion_id,))
        
        row = self.cursor.fetchone()
        if not row or not row[0]:
            return None
        
        return self.extraer_temas_de_texto(row[0])
    
    def calcular_match(self, temas_lectura, temas_cancion):
        """Calcula el score de matching entre temas"""
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
            score_total += dict_lectura[tema] * dict_cancion[tema]
        
        return score_total
    
    def encontrar_canciones_para_lectura(self, lectura_id, limite=3):
        """Encuentra las mejores canciones para una lectura"""
        temas_lectura = self.analizar_lectura(lectura_id)
        
        if not temas_lectura:
            return []
        
        print(f"Temas de la lectura: {[t['tema'] for t in temas_lectura[:3]]}")
        
        # Analizar todas las canciones
        self.cursor.execute('SELECT id, titulo FROM canciones')
        canciones = self.cursor.fetchall()
        
        matches = []
        for cancion_id, titulo in canciones:
            temas_cancion = self.analizar_cancion(cancion_id)
            if temas_cancion:
                score = self.calcular_match(temas_lectura, temas_cancion)
                if score > 0:
                    matches.append({
                        'cancion_id': cancion_id,
                        'titulo': titulo,
                        'score': score,
                        'temas_comunes': [t['tema'] for t in temas_cancion if t['tema'] in [tl['tema'] for tl in temas_lectura]]
                    })
        
        # Ordenar por score y limitar
        matches.sort(key=lambda x: x['score'], reverse=True)
        return matches[:limite]
    
    def guardar_match(self, lectura_id, cancion_id, score, momento_liturgico='general'):
        """Guarda un match en la base de datos"""
        # Por ahora, guardamos en la tabla presentaciones como propuesta
        self.cursor.execute('''
            INSERT INTO presentaciones (fecha_domingo, canciones_json, estado)
            VALUES (?, ?, ?)
        ''', (
            lectura_id,
            json.dumps([{'cancion_id': cancion_id, 'score': score, 'momento': momento_liturgico}]),
            'propuesta'
        ))
        self.conn.commit()
    
    def cerrar(self):
        """Cierra la conexión a la base de datos"""
        self.conn.close()

def probar_matching():
    """Prueba el motor de matching"""
    print("=" * 70)
    print("MOTOR DE MATCHING TEMATICO")
    print("=" * 70)
    
    engine = MatchingEngine()
    
    # Verificar si hay lecturas en la DB
    engine.cursor.execute('SELECT id, celebracion FROM lecturas LIMIT 1')
    lectura = engine.cursor.fetchone()
    
    if not lectura:
        print("No hay lecturas en la base de datos.")
        print("Ejecutar primero: python src/scrapers/koinonia_scraper.py")
        engine.cerrar()
        return
    
    lectura_id, celebracion = lectura
    print(f"\nLectura: {celebracion}")
    print(f"ID: {lectura_id}")
    
    # Encontrar canciones
    print("\nBuscando canciones relacionadas...")
    matches = engine.encontrar_canciones_para_lectura(lectura_id, limite=5)
    
    if matches:
        print(f"\n✅ Encontradas {len(matches)} coincidencias:")
        for i, match in enumerate(matches, 1):
            print(f"\n{i}. {match['titulo']}")
            print(f"   Score: {match['score']}")
            print(f"   Temas comunes: {', '.join(match['temas_comunes'])}")
    else:
        print("\n❌ No se encontraron coincidencias")
    
    engine.cerrar()
    print("\n" + "=" * 70)

if __name__ == "__main__":
    probar_matching()
