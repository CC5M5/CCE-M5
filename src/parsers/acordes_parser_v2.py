#!/usr/bin/env python3
"""
Parser de acordes con posicionamiento para el Cancionero Escolapio
Mantiene la posicion exacta de los acordes sobre la letra
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
            # Notacion inglesa
            'C', 'C#', 'Cm', 'C7', 'Cm7', 'CM',
            'D', 'D#', 'Dm', 'D7', 'Dm7', 'DM',
            'E', 'Em', 'E7', 'Em7', 'EM',
            'F', 'F#', 'Fm', 'F7', 'Fm7', 'FM',
            'G', 'G#', 'Gm', 'G7', 'Gm7', 'GM',
            'A', 'A#', 'Am', 'A7', 'Am7', 'AM',
            'B', 'Bm', 'B7', 'Bm7', 'BM',
        ]
        
        # Compilar patron para detectar acordes (case insensitive)
        patron = '|'.join(re.escape(a) for a in self.acordes_variantes)
        self.patron_acordes = re.compile(r'\b(' + patron + r')\b', re.IGNORECASE)
    
    def parsear_linea_con_acordes(self, linea):
        """
        Parsea una linea que contiene acordes y letra.
        Retorna una estructura con la posicion exacta de cada acorde.
        """
        linea_original = linea.rstrip()
        if not linea_original.strip():
            return None
        
        # Encontrar todos los acordes y sus posiciones
        acordes_encontrados = []
        for match in self.patron_acordes.finditer(linea_original):
            acorde = match.group(0)
            posicion = match.start()
            acordes_encontrados.append({
                'acorde': acorde,
                'posicion': posicion
            })
        
        # Si no hay acordes, es solo letra
        if not acordes_encontrados:
            return {
                'tipo': 'letra',
                'texto': linea_original
            }
        
        # Separar acordes de letra
        # Los acordes estan al principio de la linea o entre espacios
        # La letra comienza despues del ultimo acorde
        
        # Determinar si es una linea de acordes (solo acordes) o mixta
        texto_sin_acordes = self.patron_acordes.sub('', linea_original).strip()
        
        # Si queda poco texto (o espacios), es linea de acordes puros
        if len(texto_sin_acordes) < 3:
            return {
                'tipo': 'acordes',
                'acordes': acordes_encontrados
            }
        
        # Si hay texto sustancial, es linea mixta (acordes sobre letra)
        return {
            'tipo': 'mixta',
            'acordes': acordes_encontrados,
            'letra': texto_sin_acordes
        }
    
    def parsear_cancion_completa(self, texto):
        """
        Parsea el texto completo de una cancion.
        Retorna una lista de lineas con acordes posicionados.
        """
        lineas = texto.split('\n')
        resultado = []
        
        for linea in lineas:
            parseada = self.parsear_linea_con_acordes(linea)
            if parseada:
                resultado.append(parseada)
        
        return resultado
    
    def generar_html_visual(self, estructura):
        """
        Genera HTML donde los acordes aparecen encima de la letra,
        manteniendo la posicion relativa.
        """
        html = []
        html.append('<div class="cancion-con-acordes">')
        
        for linea in estructura:
            if linea['tipo'] == 'letra':
                html.append(f'<div class="letra-solo">{linea["texto"]}</div>')
            
            elif linea['tipo'] == 'acordes':
                acordes_html = ' '.join(a['acorde'] for a in linea['acordes'])
                html.append(f'<div class="linea-acordes">{acordes_html}</div>')
            
            elif linea['tipo'] == 'mixta':
                # Para lineas mixtas, necesitamos un formato especial
                # donde los acordes estan sobre la letra
                html.append('<div class="linea-mixta">')
                html.append('  <div class="acordes-superior">')
                
                # Construir la linea de acordes con espaciado
                acordes_linea = []
                pos_actual = 0
                for acorde_info in linea['acordes']:
                    pos = acorde_info['posicion']
                    acorde = acorde_info['acorde']
                    # Agregar espacios para mantener posicion
                    espacios = ' ' * (pos - pos_actual)
                    acordes_linea.append(espacios + acorde)
                    pos_actual = pos + len(acorde)
                
                html.append(''.join(acordes_linea))
                html.append('  </div>')
                html.append(f'  <div class="letra-inferior">{linea["letra"]}</div>')
                html.append('</div>')
        
        html.append('</div>')
        return '\n'.join(html)
    
    def detectar_tono(self, estructura):
        """Detecta el tono principal de la cancion"""
        acordes_totales = []
        for linea in estructura:
            if 'acordes' in linea:
                for acorde_info in linea['acordes']:
                    acordes_totales.append(acorde_info['acorde'])
        
        if not acordes_totales:
            return "No detectado"
        
        from collections import Counter
        contador = Counter(acordes_totales)
        return contador.most_common(1)[0][0]

def probar_parser_posicionado():
    """Prueba el parser con texto de ejemplo"""
    texto_ejemplo = """PREPARAD EL CAMINO
escuchar

SOL   Lam        Sim                 DO          RE7
PREPARAD EL CAMINO AL SEÑOR
SOL            Lam            Sim        DO   RE7   SOL
Y ESCUCHAD LA PALABRA DE DIOS.(Bis)
SOL Mim
Voz que clama en el desierto:"""
    
    parser = AcordesParser()
    estructura = parser.parsear_cancion_completa(texto_ejemplo)
    
    print("=== ESTRUCTURA JSON ===")
    print(json.dumps(estructura, indent=2, ensure_ascii=False))
    print()
    print("=== TONO DETECTADO ===")
    print(parser.detectar_tono(estructura))
    print()
    print("=== HTML VISUAL ===")
    print(parser.generar_html_visual(estructura))

if __name__ == "__main__":
    probar_parser_posicionado()
