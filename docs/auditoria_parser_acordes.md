# Auditoría del Parser de Acordes

## Resumen ejecutivo

El parser actual **falla en el requisito crítico**: los acordes no quedan exactamente sobre la sílaba/letra correspondiente. El problema principal es conceptual: intenta detectar acordes dentro de la misma línea de letra, cuando el formato cancionero típico usa **dos líneas** (acordes arriba, letra abajo). Esto produce falsos positivos (por ejemplo, la palabra "LA" se detecta como acorde `La`) y borra palabras de la letra.

---

## 1. Problemas de parseo de acordes

### 1.1. Falsos positivos catastróficos

La palabra "LA" en "Y ESCUCHAD **LA** PALABRA" coincide con el acorde `La`. El parser la elimina del texto, dejando:

```
Y ESCUCHAD  PALABRA DE DIOS.(Bis)
```

Esto rompe tanto el sentido del verso como el posicionamiento, porque la posición 11 ya no corresponde a ningún carácter real de la letra.

### 1.2. Lista blanca incompleta

- Faltan bemoles: `Reb`, `Lab`, `Solb`, `Sib`, `Mib`, `Fab`.
- Faltan extensiones comunes: `add9`, `sus4`, `sus2`, `dim`, `aug`, `maj7`, `m9`, `11`, `13`, etc.
- Faltan slash chords: `Do/F`, `Sol/Si`, `C/E`, `D/F#`.
- No hay forma de sostener `Do#` y `Reb` a la vez como equivalentes sin duplicar.

### 1.3. Orden de la lista de variantes

`'M'` aparece como variante, lo que hace que `CM`, `DM`, etc. sean válidos, pero en muchos formatos `M` solo se usa como séptima mayor (`Maj7`). Además, `'m'` es válido como `Cm`, `Dm`, etc., pero sin nota base ese patrón no matchea solo, aunque sí puede confundirse con palabras.

### 1.4. Límite de palabra (`\\b`) con `#`

El carácter `#` no es un carácter de palabra en Python (`\\w`), por lo que `\\b` actúa como límite. Funciona para `Do#`, pero no para notaciones como `Re-` o `Do+` si se quisieran soportar.

### 1.5. Sensibilidad a mayúsculas/minúsculas mal manejada

`re.IGNORECASE` hace que `lam`, `LAM`, `Lam` funcionen, pero también que palabras como `la`, `sol`, `re` (sustantivos comunes) encajen. En el ejemplo, `LA` (la palabra) se confunde con `La` (acorde).

---

## 2. Problemas de posicionamiento

### 2.1. Modelo de datos incorrecto para cancionero

El parser intenta poner acordes y letra en la misma línea (`mixta`). En la práctica, el cancionero usa líneas separadas:

```
SOL   Lam        Sim                 DO          RE7
PREPARAD EL CAMINO AL SEÑOR
```

El parser actual separa esto en dos entradas independientes (`acordes` y `letra`), perdiendo la relación entre la posición del acorde y la letra de abajo.

### 2.2. `posicion` no se proyecta sobre la línea de letra

En las líneas `mixtas`, la posición se calcula sobre la línea original (donde el acorde estaba). Pero la letra se extrae con `re.sub('', ...).strip()`, eliminando caracteres iniciales. Por tanto, la posición 11 de `LA` no se corresponde con la letra resultante.

### 2.3. Espaciado con espacios en HTML

El HTML generado usa `" " * (pos - pos_actual)` para alinear. En HTML, los espacios sucesivos se colapsan a menos que se use `white-space: pre` o `pre-wrap`. El resultado visual no conservará la alineación.

### 2.4. No se maneja ancho real de caracteres

Incluso con `white-space: pre`, las letras y los acordes tienen anchos tipográficos distintos. Para un posicionamiento realmente exacto se necesita:
- Fuente monoespaciada, o
- Spans absolutos/relativos con posición calculada por carácter, o
- Medir el texto renderizado en el cliente.

---

## 3. Problemas de robustez

### 3.1. Asunción sobre líneas de acordes puras

```python
if len(texto_sin_acordes) < 3:
    return {'tipo': 'acordes', ...}
```

- El número mágico `3` es frágil.
- Una línea como `"Sol"` (3 caracteres) podría pasar como letra.
- Una línea de acordes con un guion final `"Sol -"` no se detecta como acordes.

### 3.2. `texto_sin_acordes.strip()` elimina espacios significativos

En una línea de acordes, los espacios son la semántica del posicionamiento. Hacer `.strip()` los destruye.

### 3.3. No maneja líneas vacías ni metadatos

- Líneas vacías se ignoran (`return None`).
- No hay soporte para secciones `[Estribillo]`, `Verso 1`, etc.
- No hay soporte para comentarios o indicaciones de ritmo.

### 3.4. No normaliza acordes

`SOL`, `Sol`, `sol`, `G` pueden aparecer mezclados. El detectar tono hace `Counter` sobre el texto literal, así que `SOL` y `Sol` se consideran acordes distintos.

### 3.5. Detección de tono ingenua

`most_common(1)[0][0]` devuelve el acorde más frecuente, no necesariamente la tónica. Por ejemplo, en muchas canciones en `Do` mayor, `Sol` (dominante) aparece más que `Do`.

---

## 4. Problemas de seguridad

### 4.1. XSS en la generación de HTML

```python
html.append(f'<div class="letra-solo">{linea["texto"]}</div>')
```

Si el texto de entrada contiene `<script>alert(1)</script>`, se inyecta directamente en el HTML. El parser debe escapar con `html.escape`.

### 4.2. ReDoS potencial

El patrón `r'\b(' + patron + r')\b'` con una lista larga y alternancias no es catastrófico en este caso concreto, pero el orden de alternancias (`Do|Do#|...`) es ineficiente. Un atacante podría enviar entradas largas con muchas palabras similares para forzar backtracking si se amplía la lista sin cuidado.

### 4.3. Sin validación de entrada

`parsear_cancion_completa` acepta cualquier string, incluidos inputs enormes. No hay límite de tamaño.

---

## 5. Problemas de rendimiento

### 5.1. Reconstrucción del patrón en cada instancia

Cada `AcordesParser()` recompila la misma expresión regular. Si se instancia muchas veces (por ejemplo, una por petición HTTP), se pierde tiempo.

### 5.2. `re.sub` + `finditer` sobre la misma línea

Se recorre la línea dos veces con regex. Para inputs pequeños no importa, pero es evitable.

### 5.3. Espaciado con strings gigantes

```python
espacios = ' ' * (pos - pos_actual)
```

En una línea muy larga podría generar strings enormes inútiles si hay posiciones negativas (ver punto 6).

---

## 6. Errores de lógica / bugs concretos

### 6.1. Posición negativa posible

Si dos acordes se solapan o el segundo empieza antes de que termine el primero (imposible con regex no solapante, pero posible si se manipulan posiciones), `pos - pos_actual` podría ser negativo, generando `' ' * -3` → string vacío y desplazando mal.

### 6.2. Línea "mixta" nunca se usa correctamente

En el ejemplo de prueba, las líneas reales son de acordes puros seguidas de letra. El parser no las empareja, así que el tipo `mixta` es un caso degenerado producido por un falso positivo.

### 6.3. La letra se corrompe

El uso de `re.sub` para quitar acordes en una línea mixta borra subcadenas que pueden ser palabras normales, como ya se ha demostrado con "LA".

---

## 7. Mejores prácticas no seguidas

- No hay tests unitarios.
- No hay tipado.
- No hay docstrings descriptivas de los tipos de retorno.
- Se usa `from collections import Counter` dentro de la función; mejor importar arriba.
- El script mezcla lógica de parseo, generación HTML y demo en un mismo archivo.
- No hay separación entre modelo de datos (`Line`, `Song`) y representación.
- Nombres de métodos y variables mezclan español y técnicas; no es un problema grave, pero conviene ser consistente.

---

## 8. Recomendación de rediseño

La solución robusta es asumir el formato cancionero de **dos líneas**:

1. **Línea de acordes**: contiene acordes separados por espacios.
2. **Línea de letra**: contiene el texto, alineado con los acordes por posición de carácter.

Algoritmo:
- Leer el texto línea a línea.
- Para cada línea, determinar si es línea de acordes o línea de letra.
- Si es línea de acordes, guardarla y esperar la siguiente línea de letra.
- Al encontrar la línea de letra, proyectar cada acorde sobre la letra usando la posición de carácter.
- Emitir un bloque `{acordes: [...], letra: "..."}`.

Ventajas:
- Elimina falsos positivos con palabras comunes.
- Preserva la letra exacta.
- Permite posicionamiento exacto con `white-space: pre` y fuente monoespaciada.
- Facilita la generación de HTML con spans posicionados.

---

## 9. Veredicto

El parser actual **no es usable en producción** para el requisito crítico de posicionamiento exacto. Necesita un rediseño conceptual (trabajar por parejas de líneas) y correcciones de seguridad (XSS), robustez (palabras comunes, acordes con bemoles y extensiones) y rendimiento (patrón compilado una sola vez).
