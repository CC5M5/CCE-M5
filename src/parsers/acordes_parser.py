#!/usr/bin/env python3
"""
Parser de acordes para el Cancionero Escolapio - VERSION CORREGIDA
Separa letra y acordes, identifica momentos liturgicos
"""

import re
import json

class AcordesParser:
    def __init__(self):
        # Acordes validos en notacion espanola (mayusculas y minusculas)
        self.acordes_base = ['Do', 'Re', 'Mi', 'Fa', 'Sol', 'La', 'Si']
        self.acordes_variantes = [
            'Do', 'Do#', 'Dom', 'Do7', 'Dom7', 'DoM',
            'Re', 'Re#', 'Rem', 'Re7', 'Rem7', 'ReM',
            'Mi', 'Mim', 'Mi7', 'Mim7', 'MiM',
            'Fa', 'Fa#', 'Fam', 'Fa7', 'Fam7', 'FaM',
            'Sol', 'Sol#', 'Solm', 'Sol7', 'Solm7', 'SolM',
            'La', 'La#', 'Lam', 'La7', 'Lam7', 'LaM',
            'Si', 'Sim', 'Si7', 'Sim7', 'SiM',
        ]
        
        # Compilar patron para detectar acordes (case insensitive)
        patron = '|'.join(re.escape(a) for a in self.acordes_variantes)
        self.patron_acordes = re.compile(r'\b(' + patron + r')\b', re.IGNORECASE)
        
        # Patron para identificar lineas que son SOLO acordes
        # Una linea de acordes tiene palabras que coinciden con acordes
        self.patron_linea_acordes = re.compile(
            r'^[\s]*(?:' + patron + r')[\s]*$', 
            re.IGNORECASE
        )
    
    def detectar_acordes_en_linea(self, linea):
        """Detecta si una linea contiene SOLO acordes (sin letra)"""
        linea_limpia = linea.strip()
        if not linea_limpia:
            return False
        
        # Dividir en palabras
        palabras = linea_limpia.split()
        if not palabras:
            return False
        
        # Contar cuantas palabras son acordes
        acordes_encontrados = 0
        for palabra in palabras:
            # Limpiar simbolos comunes
            palabra_limpia = re.sub(r'[\(\)\[\]\.\,]', '', palabra)
            if self.patron_acordes.match(palabra_limpia):
                acordes_encontrados += 1
        
        # Si todas o casi todas las palabras son acordes, es linea de acordes
        return acordes_encontrados / len(palabras) >= 0.7
    
    def separar_letra_y_acordes(self, texto):
        """Separa la letra de los acordes del texto completo"""
        lineas = texto.split('\n')
        
        letra_lineas = []
        acordes_lineas = []
        
        for linea in lineas:
            if self.detectar_acordes_en_linea(linea):
                acordes_lineas.append(linea.strip())
            else:
                # Limpiar linea de acordes sueltos que puedan quedar
                letra_limpia = self._limpiar_acordes_de_linea(linea)
                letra_lineas.append(letra_limpia)
        
        # Extraer todos los acordes unicos del texto
        todos_acordes = self.patron_acordes.findall(texto)
        acordes_unicos = sorted(set(todos_acordes))
        
        return {
            'letra': '\n'.join(letra_lineas).strip(),
            'acordes': '\n'.join(acordes_lineas).strip(),
            'acordes_lista': acordes_unicos
        }
    
    def _limpiar_acordes_de_linea(self, linea):
        """Elimina acordes sueltos de una linea de letra"""
        # Si la linea tiene muchos acordes dispersos, limpiar
        palabras = linea.split()
        palabras_limpias = []
        
        for palabra in palabras:
            palabra_limpia = re.sub(r'[\(\)\[\]\.\,]', '', palabra)
            # Solo eliminar si es un acorde suelto (no parte de la letra)
            if self.patron_acordes.match(palabra_limpia) and len(palabras) > 3:
                continue
            palabras_limpias.append(palabra)
        
        return ' '.join(palabras_limpias)
    
    def detectar_tono(self, acordes_texto):
        """Detecta el tono principal de la cancion"""
        acordes = self.patron_acordes.findall(acordes_texto)
        if not acordes:
            return "No detectado"
        
        # El tono suele ser el primer acorde o el mas frecuente
        from collections import Counter
        contador = Counter(acordes)
        return contador.most_common(1)[0][0]
    
    def detectar_momento_liturgico(self, titulo, texto):
        """Intenta detectar el momento liturgico basado en el titulo o contenido"""
        titulo_lower = titulo.lower()
        
        # Palabras clave por momento
        momentos = {
            'entrada': ['entrada', 'abre', 'puertas', 'luz'],
            'perdon': ['perdon', 'misericordia', 'pecado'],
            'gloria': ['gloria', 'alabanza', 'dios'],
            'salmo': ['salmo', 'salmodia'],
            'aleluya': ['aleluya', 'aleluia'],
            'ofertorio': ['ofertorio', 'ofrenda', 'pan', 'vino'],
            'santo': ['santo', 'sanctus'],
            'padre_nuestro': ['padre nuestro', 'padrenuestro'],
            'paz': ['paz', 'cordero'],
            'comunion': ['comunion', 'cuerpo', 'sangre'],
            'maria': ['maria', 'virgen'],
            'despedida': ['despedida', 'envio', 've']
        }
        
        for momento, palabras in momentos.items():
            for palabra in palabras:
                if palabra in titulo_lower:
                    return momento
        
        return 'general'

def probar_parser():
    """Prueba el parser con texto de ejemplo real"""
    texto_ejemplo = """PREPARAD EL CAMINO
escuchar
    /    
 
volver a lista de canciones
SOL   Lam        Sim                 DO          RE7
PREPARAD EL CAMINO AL SEÑOR
SOL            Lam            Sim        DO   RE7   SOL
Y ESCUCHAD LA PALABRA DE DIOS.(Bis)
Voz que clama en el desierto:
SOL                          
SOL                   Lam  Sim
Abrid los caminos al Señor,
    DO               RE7
enderezad las veredas para nuestro Dios.
SOL               Lam   Sim          DO       RE7    SOL
Y serán enderezados los senderos, los valles serán rellenados,
         Lam         Sim           DO    RE7   SOL
las colinas serán rebajadas, y el mundo entero verá la gloria de Dios."""
    
    parser = AcordesParser()
    resultado = parser.separar_letra_y_acordes(texto_ejemplo)
    
    print("=== PRUEBA DE PARSER CORREGIDO ===")
    print(f"Tono detectado: {parser.detectar_tono(resultado['acordes'])}")
    print(f"Acordes encontrados: {resultado['acordes_lista']}")
    print("\n--- LETRA (sin acordes) ---")
    print(resultado['letra'])
    print("\n--- ACORDES ---")
    print(resultado['acordes'])

if __name__ == "__main__":
    probar_parser()
