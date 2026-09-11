# Spec 09: Vista para Músicos con Acordes

## Visión

Cada semana, junto con la presentación para fieles, se generará automáticamente una **hoja para músicos** que contenga:
- Todas las canciones seleccionadas CON acordes
- Ordenadas según los 12 momentos litúrgicos
- En un solo documento (una pestaña web + PDF descargable)
- Formato optimizado para lectura a distancia (coro)

## Formatos de Salida

| Formato | Uso | Orientación | Tamaño fuente |
|---------|-----|-------------|---------------|
| **Web** (`/musicos/YYYY-MM-DD/`) | Vista previa, tablet en atril | Vertical | 16-18px |
| **PDF** (`hoja_musicos.pdf`) | Impresión, tablet, pantalla | Vertical A4 | 12-14pt |

## Estructura del Documento

```
═══════════════════════════════════════════════════════════════════════
           COMUNIDAD CRISTIANA ESCOLAPIA MONTEQUINTO
              Hoja de Músicos — Domingo XXIV T.O.
                    13 de Septiembre de 2026
═══════════════════════════════════════════════════════════════════════

NOTAS PREVIAS:
• Tono general: Do
• Evento especial: Confirmación de Pedro (modificar Gloria y Comunión)
• Ensayo: Sábado 19:00h

───────────────────────────────────────────────────────────────────────

1. ENTRADA — "Al encuentro" (Do)
═══════════════════════════════════════════════════════════════════════

Do      Sol      Lam     Fa
AL ENCUENTRO VOY, CAMINANDO VOY,
Do              Sol     Fa      Sol
BUSCANDO LA VERDAD QUE HABITA EN TI.

[... estrofas ...]

───────────────────────────────────────────────────────────────────────

2. PERDÓN — "Perdónanos, Señor" (Re)
═══════════════════════════════════════════════════════════════════════

Re      La7      Sol     La
PERDÓNANOS, SEÑOR, PERDÓNANOS,
Sol             La
SIENDO TÚ MARGINADO SE NOS OLVIDÓ.

[...]

───────────────────────────────────────────────────────────────────────

3. GLORIA — "Gloria de Nazaret" (Mi)
═══════════════════════════════════════════════════════════════════════

Mi      Si       Do#m
GLORIA A DIOS EN LO ALTO DEL CIELO,
Mi      Si       Do#m
Y EN LA TIERRA A LOS HOMBRES QUE AMA EL SEÑOR.

[...]

───────────────────────────────────────────────────────────────────────

[... CONTINÚA HASTA ...]

12. DESPEDIDA — "Cristo vive" (Do)
═══════════════════════════════════════════════════════════════════════

Do      Sol
CRISTO VIVE, CRISTO REINA,
La      Mi      Fa
CRISTO ES EL SEÑOR DE MI VIDA.

[...]

═══════════════════════════════════════════════════════════════════════
                         FIN DE LA CELEBRACIÓN
═══════════════════════════════════════════════════════════════════════
```

## Especificaciones de Formato

### PDF para Coro

| Parámetro | Valor |
|-----------|-------|
| **Formato** | A4 |
| **Orientación** | Vertical (portrait) |
| **Márgenes** | Superior 2cm, Inferior 2cm, Izquierdo 2.5cm, Derecho 2cm |
| **Fuente acordes** | Courier New Bold, 11pt |
| **Fuente letra** | Times New Roman, 12pt |
| **Interlineado acordes-letra** | 1.3 |
| **Interlineado entre canciones** | 1.5 |
| **Color acordes** | Negro (#000000) |
| **Color letra** | Negro (#000000) |
| **Encabezado** | "CCE M5 — [Fecha]" en cada página |
| **Número de página** | Pie de página |

### Web Responsive

```css
/* Desktop/tablet (atríl) */
.hoja-musicos {
  font-family: 'Courier New', monospace;
  font-size: 18px;
  line-height: 1.6;
  max-width: 800px;
  margin: 0 auto;
  padding: 20px;
}

.acordes {
  font-weight: bold;
  color: #2c3e50;
  letter-spacing: 0.05em;
}

/* Mobile */
@media (max-width: 640px) {
  .hoja-musicos {
    font-size: 16px;
    padding: 10px;
  }
}
```

## Posicionamiento de Acordes

### Método: Tabulación por espacios

Los acordes en el Blogspot usan tabulación/espaciado para posicionarse sobre las sílabas. El parser debe:

1. **Calcular posición relativa**: `posición = índice del carácter en la línea`
2. **Mapear a sílaba**: Encontrar qué sílaba de la letra corresponde
3. **Generar estructura**: JSON con coordenadas

```json
{
  "linea_acordes": "Do    Sol   Lam   Fa",
  "linea_letra": "A TU AMPARO Y PROTECCIÓN,",
  "mapeo": [
    {"acorde": "Do", "posicion_caracter": 0, "sila_letra": "A"},
    {"acorde": "Sol", "posicion_caracter": 6, "sila_letra": "AM"},
    {"acorde": "Lam", "posicion_caracter": 12, "sila_letra": "PRO"},
    {"acorde": "Fa", "posicion_caracter": 18, "sila_letra": "CCIÓN"}
  ]
}
```

### Visualización en Web

```html
<!-- Versión con tabulación preformateada -->
<pre class="hoja-musicos">
Do      Sol      Lam      Fa
A TU AMPARO Y PROTECCIÓN,
</pre>

<!-- Versión con acordes posicionados sobre sílabas -->
<div class="linea-cancion">
  <span class="sila-con-acorde">
    <span class="acorde">Do</span>
    <span class="sila">A</span>
  </span>
  <span class="sila-con-acorde">
    <span class="acorde">Sol</span>
    <span class="sila">TU</span>
  </span>
  ...
</div>
```

## Generación Automática

### Flujo

```
1. Usuario selecciona canciones (12 momentos)
        │
        ▼
2. Sistema consulta base de datos
   - Obtiene letra_con_acordes de cada canción
        │
        ▼
3. Parser procesa cada canción
   - Extrae acordes posicionados
   - Genera formato preformateado
        │
        ▼
4. Generador PDF (ReportLab/WeasyPrint)
   - Compila documento completo
   - Añade encabezados, notas, numeración
        │
        ▼
5. Generador HTML (Astro)
   - Página /musicos/YYYY-MM-DD/
   - Toggle acordes on/off
   - Botón descarga PDF
        │
        ▼
6. Despliegue
   - PDF en presentaciones/YYYY/MM/
   - Web en GitHub Pages
```

### Librerías Recomendadas

| Propósito | Librería | Notas |
|-----------|----------|-------|
| PDF | ReportLab | Bajo nivel, control total |
| PDF | WeasyPrint | HTML→PDF, más fácil |
| PDF | fpdf2 | Simple, buen soporte UTF-8 |
| HTML | Astro + pre/code | Preformateado con <pre> |
| Print CSS | @media print | Optimizado para impresión |

## Ejemplo Completo: Vista Web

```
┌─────────────────────────────────────────────────────────────────┐
│  🎵 CCE M5 Music    [Inicio] [Cancionero] [Músicos] [Sobre]     │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  🎼 Hoja de Músicos — Domingo XXIV T.O.                         │
│  13 de Septiembre de 2026                                       │
│                                                                  │
│  [🖨️ Imprimir] [⬇️ Descargar PDF] [🔲 Mostrar/Ocultar acordes] │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  NOTAS: Celebración normal. Tono general: Do.            │   │
│  │                                                           │   │
│  │  ══════════════════════════════════════════════════════ │   │
│  │  1. ENTRADA — "Al encuentro" (Do)                         │   │
│  │  ══════════════════════════════════════════════════════ │   │
│  │                                                           │   │
│  │  Do       Sol      Lam       Fa                          │   │
│  │  AL ENCUENTRO VOY, CAMINANDO VOY,                          │   │
│  │                                                           │   │
│  │  Do               Sol       Fa      Sol                   │   │
│  │  BUSCANDO LA VERDAD QUE HABITA EN TI.                      │   │
│  │                                                           │   │
│  │  [...]                                                     │   │
│  │                                                           │   │
│  │  ══════════════════════════════════════════════════════ │   │
│  │  2. GLORIA — "Gloria de Nazaret" (Mi)                    │   │
│  │  ══════════════════════════════════════════════════════ │   │
│  │                                                           │   │
│  │  Mi        Si        Do#m                                  │   │
│  │  GLORIA A DIOS EN LO ALTO DEL CIELO,                       │   │
│  │                                                           │   │
│  │  [...]                                                     │   │
│  │                                                           │   │
│  │  [Continúa hasta la Despedida...]                          │   │
│  │                                                           │   │
│  │  ══════════════════════════════════════════════════════ │   │
│  │  12. DESPEDIDA — "Cristo vive" (Do)                     │   │
│  │  ══════════════════════════════════════════════════════ │   │
│  │                                                           │   │
│  │  Do       Sol                                             │   │
│  │  CRISTO VIVE, CRISTO REINA,                                 │   │
│  │                                                           │   │
│  │  La       Mi        Fa                                      │   │
│  │  CRISTO ES EL SEÑOR DE MI VIDA.                             │   │
│  │                                                           │   │
│  │  ══════════════════════════════════════════════════════ │   │
│  │              FIN DE LA CELEBRACIÓN                          │   │
│  │  ══════════════════════════════════════════════════════ │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Requisitos Específicos

1. **Un solo documento**: Todas las canciones en secuencia, sin paginación forzada
2. **Numeración clara**: Cada momento litúrgico numerado (1-12)
3. **Tono visible**: Indicado al inicio de cada canción
4. **Notas al inicio**: Eventos especiales, cambios de tono, instrucciones
5. **Print-friendly**: Sin colores de fondo, texto negro sobre blanco
6. **Toggle web**: Posibilidad de ocultar/mostrar acordes en la vista web
7. **Responsive**: Legible en tablet (iPad) para uso en atril

## Testing de la Vista

| Test | Descripción | Criterio de éxito |
|------|-------------|-------------------|
| Visual | Revisar alineación acordes-letra | Acordes sobre sílaba correcta |
| Print | Imprimir a PDF y en papel | Legible a 2 metros |
| Tablet | Probar en iPad 10" | Todo visible sin scroll horizontal |
| Mobile | Probar en iPhone | Scroll vertical fluido, legible |
| Descarga | Descargar PDF | Archivo < 500KB, abre correctamente |
