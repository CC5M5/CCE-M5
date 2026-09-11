# Spec 08: Migración del Cancionero Escolapio

## Visión

Migrar TODO el contenido del cancionero escolapio desde https://ccem5music.blogspot.com/p/cancionero-escolapio.html hacia la nueva plataforma web, manteniendo:
- Todas las canciones con sus letras y acordes
- Enlaces a versiones alternativas (Betania Music)
- Enlaces a audio (YouTube)
- Posibilidad de añadir nuevas canciones fácilmente

## Fuente Original

| Aspecto | Detalle |
|---------|---------|
| **URL principal** | https://ccem5music.blogspot.com/p/cancionero-escolapio.html |
| **Plataforma** | Blogger/Blogspot |
| **Estructura** | Lista de enlaces a páginas individuales |
| **Formato** | HTML con acordes inline |
| **Canciones estimadas** | 50+ |
| **Idioma** | Español |

## Estructura de la Web Original

```
CCE M5 Music (Blogspot)
├── /p/cancionero-escolapio.html
│   ├── Lista de canciones:
│   │   ├── "A TU AMPARO Y PROTECCIÓN" → /p/a-tu-amparo-y-proteccion.html
│   │   ├── "AL CALOR DE LA PALABRA" → betaniamusic.blogspot.com/...
│   │   ├── "AL ENCUENTRO" → betaniamusic.blogspot.com/...
│   │   ├── ... (50+ enlaces)
│   │
│   └── Cada canción tiene:
│       ├── Título
│       ├── Enlace "escuchar" (YouTube)
│       ├── Enlace "Versión en Re" (alternativa tono)
│       ├── Letra CON acordes en formato:
│       │      Do    Sol   Lam   Fa
│       │      A TU AMPARO Y PROTECCIÓN,
│       │      Do     Sol   Fa    Sol
│       │      MADRE DE DIOS, ACUDIMOS.
│       │   ...
│       └── Botón "volver a lista de canciones"
```

## Estrategia de Scraping

### Paso 1: Obtener Lista de Canciones
```python
# URL: https://ccem5music.blogspot.com/p/cancionero-escolapio.html
# Extraer todos los enlaces <a> dentro del área de canciones
# Cada enlace apunta a /p/[slug].html o a betaniamusic.blogspot.com/...

enlaces = extraer_enlaces("https://ccem5music.blogspot.com/p/cancionero-escolapio.html")
# Resultado: [{"titulo": "A TU AMPARO Y PROTECCIÓN", "url": "..."}, ...]
```

### Paso 2: Scrapear Página Individual
```python
# Para cada URL de canción:
# 1. Obtener HTML
# 2. Extraer:
#    - Título (h1, h2 o h3)
#    - Enlaces YouTube/Betania
#    - Letra completa (texto con acordes)
# 3. Guardar raw HTML + parseado

cancion = {
    "titulo": "A tu amparo y protección",
    "url_fuente": "https://ccem5music.blogspot.com/p/a-tu-amparo-y-proteccion.html",
    "enlace_audio": "https://youtu.be/...",
    "enlace_alternativo": "https://betaniamusic.blogspot.com/...",
    "letra_con_acordes": "Do\tSol\tLam\tFa\nA TU AMPARO Y PROTECCIÓN,...",
    "fuente": "CCE M5 Music"
}
```

### Paso 3: Parsear Acordes
```python
# Separar acordes de letra
# Input: texto con acordes inline
# Output:
#   - letra_sin_acordes
#   - acordes_json (posicionales)

# Ejemplo:
# Input:
#   Do    Sol   Lam   Fa
#   A TU AMPARO Y PROTECCIÓN,
#
# Output letra_sin_acordes:
#   A TU AMPARO Y PROTECCIÓN,
#
# Output acordes_json:
#   {
#     "linea_letra": 2,
#     "acordes": [
#       {"acorde": "Do", "posicion": 0},
#       {"acorde": "Sol", "posicion": 6},
#       {"acorde": "Lam", "posicion": 12},
#       {"acorde": "Fa", "posicion": 18}
#     ]
#   }
```

## Parser de Acordes: Detalle Técnico

### Algoritmo

```python
import re

def parsear_acordes(texto_completo):
    """
    Parsea texto con acordes en formato Blogspot.
    
    Formato típico:
        Do    Sol   Lam   Fa
        A TU AMPARO Y PROTECCIÓN,
    
    O también:
        Do
        A TU AMPARO
        Sol
        Y PROTECCIÓN
    """
    lineas = texto_completo.split('\n')
    
    acordes_lineas = []
    letra_lineas = []
    
    for i, linea in enumerate(lineas):
        linea_strip = linea.strip()
        
        # Detectar si línea es de acordes
        # Patrón: palabras cortas (1-5 chars) separadas por espacios
        palabras = linea_strip.split()
        es_acordes = False
        
        if palabras and all(es_acorde(p) for p in palabras):
            es_acordes = True
            acordes_lineas.append({
                "linea": i,
                "acordes": palabras,
                "texto_original": linea
            })
        elif linea_strip:
            letra_lineas.append({
                "linea": i,
                "texto": linea_strip
            })
    
    # Emparejar acordes con letra siguiente
    estructura = []
    for ac in acordes_lineas:
        # Buscar línea de letra más cercana después
        letra_sig = None
        for ll in letra_lineas:
            if ll["linea"] > ac["linea"]:
                letra_sig = ll
                break
        
        if letra_sig:
            estructura.append({
                "tipo": "acordes+letra",
                "linea_acordes": ac["linea"],
                "linea_letra": letra_sig["linea"],
                "acordes": ac["acordes"],
                "letra": letra_sig["texto"]
            })
    
    return estructura

def es_acorde(palabra):
    """Detecta si una palabra es un acorde musical."""
    # Patrones de acordes:
    # Do, Re, Mi, Fa, Sol, La, Si
    # Do#, Re#, Mib, Sol7, Lam, Fa#m, etc.
    patron = r'^(Do|Re|Mi|Fa|Sol|La|Si)[#b]?(m|M|7|maj7|sus4|add9)?$'
    return bool(re.match(patron, palabra, re.IGNORECASE))
```

### Acordes Soportados

| Notación | Ejemplos | Descripción |
|----------|----------|-------------|
| Básica | Do, Re, Mi, Fa, Sol, La, Si | Acordes mayores |
| Sostenido | Do#, Re#, Fa#, Sol#, La#, Si# | Sostenidos |
| Bemol | Reb, Mib, Solb, Lab, Sib | Bemoles |
| Menor | Lam, Mim, Fam, Solm, Rem | Menores (m) |
| Séptima | Do7, Sol7, La7 | Dominantes |
| Séptima mayor | DoMaj7 | Mayores séptima |
| Suspendido | Solsus4 | Suspendidos |
| Añadido | Readd9 | Añadidos |

## Proceso de Migración

### Fase 1: Scraping Inicial (Semana 2)
```bash
# Ejecutar scraper
python src/scrapers/blogspot_scraper.py \
  --url https://ccem5music.blogspot.com/p/cancionero-escolapio.html \
  --output data/canciones/raw/ \
  --format json

# Resultado: data/canciones/raw/cancionero_backup.json
```

### Fase 2: Parseo y Limpieza (Semana 2)
```bash
# Parsear acordes
python src/parsers/acordes_parser.py \
  --input data/canciones/raw/ \
  --output data/canciones/canciones.json

# Resultado: data/canciones/canciones.json
```

### Fase 3: Importación a Base de Datos (Semana 2)
```bash
# Importar a SQLite
python src/db/import_canciones.py \
  --input data/canciones/canciones.json \
  --db data/db.sqlite3

# Resultado: Base de datos poblada
```

### Fase 4: Validación (Semana 2-3)
- Revisar canciones parseadas correctamente
- Comprobar acordes sin errores
- Verificar enlaces YouTube activos
- Usuario valida calidad de migración

## Estructura de Datos Post-Migración

```
data/canciones/
├── raw/                          # Backup original
│   ├── cancionero_backup.json    # Scraping crudo
│   └── html/                     # HTML individuales
├── clean/                        # Letras sin acordes
│   ├── a-tu-amparo.txt
│   └── ...
├── parsed/                       # JSON estructurado
│   ├── a-tu-amparo.json
│   └── ...
└── canciones.json                # Dataset maestro
```

## Añadir Nuevas Canciones (Post-Migración)

### Método 1: Desde Blogspot (automático)
```python
# Si se añade canción al Blogspot:
# Re-ejecutar scraper incremental
python src/scrapers/blogspot_scraper.py --incremental
```

### Método 2: Desde PDF personal
```python
# Extraer texto de PDF
# El usuario proporciona PDF con canciones
python src/parsers/pdf_canciones.py \
  --input nuevas_canciones.pdf \
  --output data/canciones/nuevas/
```

### Método 3: Manual (formulario web)
```
Formulario en /admin (protegido):
- Título
- Letra con acordes
- Tono
- Momento litúrgico
- Enlaces audio
- Temas (tags)
```

## Mantenimiento del Cancionero

| Tarea | Frecuencia | Responsable |
|-------|-----------|-------------|
| Re-scraping Blogspot | Mensual | Automático (cron) |
| Verificar enlaces rotos | Mensual | Automático |
| Añadir canciones nuevas | Bajo demanda | Usuario + OpenCode |
| Actualizar acordes | Bajo demanda | Usuario |
| Backup | Semanal | Automático (git) |

## Comparativa: Web Original vs. Nueva

| Característica | Blogspot Original | Nueva Plataforma |
|----------------|-------------------|------------------|
| Navegación | Lista simple | Buscable, filtrable |
| Acordes | Solo con acordes | Toggle con/sin |
| Audio | Solo enlaces | Reproductor embebido |
| Responsive | Limitado | Mobile-first |
| Descargas | No | PPTX/PDF/Web |
| Comentarios | Blogger | Moderados |
| Lecturas | No | Integradas |
| Búsqueda | No | Por título/tema/momento |

## Métricas de Éxito de Migración

1. **Completitud**: 100% de canciones migradas
2. **Precisión**: > 95% de acordes parseados correctamente
3. **Disponibilidad**: Web 24/7 en GitHub Pages
4. **Velocidad**: < 2s carga página cancionero
5. **Usabilidad**: Usuario puede encontrar canción en < 30s
