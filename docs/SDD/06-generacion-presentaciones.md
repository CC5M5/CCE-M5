# 6. Generación de Presentaciones

## 6.1. Pipeline de generación

```
1. Leer presentacion_slides para la fecha (ordenadas por numero, activo=1).
2. Leer lecturas del domingo.
3. Para cada slide:
   - Si es lectura/salmo/evangelio: reemplazar contenido con texto real de la lectura.
   - Si es canción: usar letra sin acordes.
   - Aplicar color litúrgico.
   - Expandir `--- DIAPOSITIVA ---` en N slides numeradas.
4. Escribir JSON intermedio.
5. Renderizar HTML Reveal.js 4:3.
6. Renderizar PPTX 4:3 (33,87 cm × 25,4025 cm).
7. Renderizar PDF fieles desde PPTX (LibreOffice) o directamente.
8. Actualizar presentaciones con rutas y estado.
```

## 6.2. Formato 4:3

- **PPTX:** `Cm(33.87)` × `Cm(25.4025)`.
- **HTML:** contenedor 4:3 con tarjeta de contenido centrada, márgenes reservados para logo.
- **PDF:** generado desde PPTX o directamente a A4 según destino.

## 6.3. Reglas de contenido

- **Letra de canciones:** sin acordes, líneas unidas, estribillos en negrita.
- **Salmo:** compactado, uniendo frases de cada verso.
- **Lecturas:** texto completo; si son muy largas se dividen en varias slides con `(1/N, 2/N...)`.
- **Textos litúrgicos fijos:** acto penitencial, gloria, credo, santo, padre nuestro, paz, maría. Se toman del catálogo si no hay canción asignada.
- **Momentos sin canción asignada:** se muestra el título + "Rellenar a mano" o el texto litúrgico fijo si aplica.

## 6.4. JSON intermedio

Ubicación: `presentaciones_html/YYYY-MM-DD_presentacion/YYYY-MM-DD_presentacion.json`

Estructura mínima:
```json
{
  "fecha": "2026-09-13",
  "celebracion": "Domingo XXIV de Tiempo Ordinario",
  "color_liturgico": "verde",
  "slides": [
    {
      "numero": 1,
      "tipo": "portada",
      "titulo": "...",
      "contenido": "...",
      "cita": "",
      "subtitulo": "",
      "imagen": "..."
    }
  ]
}
```

## 6.5. Hoja de músicos

- Formato A4 vertical.
- Fuente monoespaciada Courier New para acordes y letra.
- Acordes posicionados exactamente sobre la letra.
- Una canción por momento litúrgico asignado.
- Encabezado con fecha y pie con número de página.

