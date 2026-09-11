#!/usr/bin/env python3
"""
Parser de acordes para el Cancionero Escolapio
Separa letra y acordes, identifica momentos liturgicos
"""

import re
import json

class AcordesParser:
    def __init__(self):
        # Notacion espanola de acordes
        self.acordes_validos = [
            'Do', 'Do#', 'Dom', 'Do7', 'Dom7',
            'Re', 'Re#', 'Rem', 'Re7', 'Rem7',
            'Mi', 'Mim', 'Mi7', 'Mim7',
            'Fa', 'Fa#', 'Fam', 'Fa7', 'Fam7',
            'Sol', 'Sol#', 'Solm', 'Sol7', 'Solm7',
            'La', 'La#', 'Lam', 'La7', 'Lam7',
            'Si', 'Sim', 'Si7', 'Sim7',
            'DoM', 'ReM', 'MiM', 'FaM', 'SolM', 'LaM', 'SiM',  # Mayores explicitos
        ]
    
    def detectar_acordes_en_linea(self, linea):
        """Detecta si una linea contiene solo acordes"""
        palabras = linea.strip().split()
        if not palabras:
            return False
        
        # Contar cuantas palabras son acordes
        acordes_encontrados = 0
        for palabra in palabras:
            # Limpiar parentesis o simbolos
            palabra_limpia = re.sub(r'[\(\)\[\]]', '', palabra)
            if palabra_limpia in self.acordes_validos:
                acordes_encontrados += 1
        
        # Si mas del 50% son acordes, considerar linea de acordes
        return acordes_encontrados / len(palabras) >= 0.5
    
    def separar_letra_y_acordes(self, texto):
        """Separa la letra de los acordes del texto completo"""
        lineas = texto.split('\n')
        
        letra_lineas = []
        acordes_lineas = []
        
        for linea in lineas:
            if self.detectar_acordes_en_linea(linea):
                acordes_lineas.append(linea.strip())
            else:
                letra_lineas.append(linea)
        
        return {
            'letra': '\n'.join(letra_lineas).strip(),
            'acordes': '\n'.join(acordes_lineas).strip(),
            'acordes_lista': list(set(re.findall(r'\b(Do|Re|Mi|Fa|Sol|La|Si)[m#]?[\dM]?\b', texto)))
        }
    
    def detectar_tono(self, acordes_texto):
        """Detecta el tono principal de la cancion"""
        # Contar frecuencia de acordes
        acordes = re.findall(r'\b(Do|Re|Mi|Fa|Sol|La|Si)[m#]?\b', acordes_texto)
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
    """Prueba el parser con texto de ejemplo"""
    texto_ejemplo = """Do    Sol    Lam    Fa
A TU AMPARO Y PROTECCION

Do         Sol    Fa    Sol
MADRE DE DIOS, ACUDIMOS

Do    Sol    Lam    Fa
NO TEMEREMOS, NO DESMAYAREMOS"""
    
    parser = AcordesParser()
    resultado = parser.separar_letra_y_acordes(texto_ejemplo)
    
    print("=== PRUEBA DE PARSER ===")
    print(f"Tono detectado: {parser.detectar_tono(resultado['acordes'])}")
    print(f"Momentos: {parser.detectar_momento_liturgico('A TU AMPARO Y PROTECCION', texto_ejemplo)}")
    print(f"Acordes: {resultado['acordes_lista']}")
    print("\n--- LETRA ---")
    print(resultado['letra'])
    print("\n--- ACORDES ---")
    print(resultado['acordes'])

if __name__ == "__main__":
    probar_parser()
