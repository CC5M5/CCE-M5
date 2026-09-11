# Spec 01: Requisitos Funcionales y No Funcionales

## Requisitos Funcionales (RF)

### RF1: Obtención de Lecturas
| ID | Descripción | Prioridad |
|----|-------------|-----------|
| RF1.1 | El sistema debe obtener automáticamente las lecturas del próximo domingo desde servicioskoinonia.org | Alta |
| RF1.2 | Debe extraer: Primera lectura, Salmo, Segunda lectura (si aplica), Evangelio | Alta |
| RF1.3 | Debe incluir citas bíblicas exactas y texto completo | Alta |
| RF1.4 | Debe cachear lecturas en `data/lecturas/YYYY/MM/YYYY-MM-DD.json` | Media |
| RF1.5 | Debe confirmar con usuario antes de proceder | Alta |

### RF2: Base de Datos de Canciones
| ID | Descripción | Prioridad |
|----|-------------|-----------|
| RF2.1 | Migrar TODO el cancionero escolapio desde ccem5music.blogspot.com | Alta |
| RF2.2 | Almacenar letra CON acordes (formato original) | Alta |
| RF2.3 | Almacenar letra SIN acordes (para presentaciones) | Alta |
| RF2.4 | Parsear acordes en estructura JSON posicional | Media |
| RF2.5 | Permitir añadir canciones desde PDFs personales | Media |
| RF2.6 | Sistema de etiquetado temático (perdón, esperanza, comunidad, etc.) | Alta |
| RF2.7 | Sistema de referencias bíblicas por canción | Media |

### RF3: Matching Lecturas-Canciones
| ID | Descripción | Prioridad |
|----|-------------|-----------|
| RF3.1 | Analizar temas de las lecturas (keywords, embeddings semánticos) | Alta |
| RF3.2 | Proponer 2-3 opciones para cada uno de los 12 momentos litúrgicos | Alta |
| RF3.3 | Permitir selección manual/ajuste por parte del usuario | Alta |
| RF3.4 | Guardar historial de selecciones para aprendizaje | Baja |

### RF4: Momentos Litúrgicos Completos
Los 12 momentos a cubrir:
1. Entrada
2. Perdón (Acto penitencial)
3. Gloria
4. Salmo (Responsorial)
5. Aleluya (Aclamación antes del Evangelio)
6. Ofertorio
7. Santo (Santo, santo, santo...)
8. Padre Nuestro
9. Paz (Señor, ten piedad / Cordero de Dios)
10. Comunión
11. Canto a María
12. Despedida (Salida)

### RF5: Generación de Presentaciones (Fieles)
| ID | Descripción | Prioridad |
|----|-------------|-----------|
| RF5.1 | Generar PPTX 16:9 (basado en formato 274 Domingo 21 06 2026) | Alta |
| RF5.2 | Incluir lecturas del día (texto completo, sin acordes) | Alta |
| RF5.3 | Incluir letras de canciones SIN acordes | Alta |
| RF5.4 | Formato visual coherente con presentaciones anteriores | Alta |
| RF5.5 | Exportar a PDF | Alta |
| RF5.6 | Guardar en `presentaciones/YYYY/MM/YYYY-MM-DD_nombre/` | Media |

### RF6: Hoja para Músicos (NUEVO)
| ID | Descripción | Prioridad |
|----|-------------|-----------|
| RF6.1 | Generar documento/vista web con canciones CON acordes | Alta |
| RF6.2 | Ordenar según los 12 momentos litúrgicos | Alta |
| RF6.3 | Posicionar acordes sobre la letra correctamente | Alta |
| RF6.4 | Exportar a PDF descargable | Alta |
| RF6.5 | Una sola pestaña/documento, sin necesidad de navegación | Alta |
| RF6.6 | Formato optimizado para coro (legible, una página continua o paginada) | Media |

### RF7: Publicación Web
| ID | Descripción | Prioridad |
|----|-------------|-----------|
| RF7.1 | Desplegar presentación semanal en web estática | Alta |
| RF7.2 | Migrar TODO el cancionero escolapio a la web | Alta |
| RF7.3 | Pestaña/vista "Músicos" con acordes | Alta |
| RF7.4 | Descarga PPTX/PDF fieles/PDF músicos | Alta |
| RF7.5 | Histórico de presentaciones anteriores | Media |
| RF7.6 | Hosting en GitHub Pages (gratuito) | Alta |

### RF8: Eventos Especiales
| ID | Descripción | Prioridad |
|----|-------------|-----------|
| RF8.1 | Preguntar al usuario sobre eventos especiales semanales | Alta |
| RF8.2 | Adaptar presentación para confirmaciones, bautizos, etc. | Alta |
| RF8.3 | Guardar metadata de eventos en base de datos | Medium |

### RF9: Comentarios y Moderación
| ID | Descripción | Prioridad |
|----|-------------|-----------|
| RF9.1 | Formulario de comentarios en la web | Alta |
| RF9.2 | Backend gratuito (GitHub Issues API o Formspree) | Alta |
| RF9.3 | Notificación automática cada 6 horas a OpenClaw | Alta |
| RF9.4 | Presentar comentarios al usuario para aprobación/rechazo | Alta |
| RF9.5 | Incorporar comentarios aprobados en la presentación | Media |

## Requisitos No Funcionales (RNF)

| ID | Descripción | Métrica |
|----|-------------|---------|
| RNF1 | Escalable para futuros requisitos | Arquitectura modular |
| RNF2 | Directorio específico en PC | `~/proyectos/CCE-M5-Web-Presentaciones/` |
| RNF3 | Formato presentaciones | PPTX 16:9, ODP compatible, PDF |
| RNF4 | Formato hoja músicos | PDF con acordes posicionados |
| RNF5 | Web responsive | Funciona en móvil y desktop |
| RNF6 | Tiempo de generación | < 5 minutos por presentación completa |
| RNF7 | Disponibilidad web | 99% uptime (GitHub Pages) |
| RNF8 | Coste | Mínimo (usar servicios gratuitos) |
| RNF9 | Seguridad | No exponer credenciales en código |
| RNF10 | Documentación | Completa en `/docs/` |

## Flujo de Trabajo Semanal (Resumen)

```
Lunes 9:00 → Trigger automático
├── 1. Obtener lecturas (Koinonia)
├── 2. Confirmar con usuario
├── 3. Seleccionar canciones (matching temático)
├── 4. Confirmar con usuario
├── 5. Preguntar eventos especiales
├── 6. Generar PPTX (fieles, sin acordes)
├── 7. Generar PDF músicos (con acordes)
├── 8. Generar web estática
├── 9. Desplegar en GitHub Pages
└── 10. Notificar a usuario

Cada 6h → Moderación comentarios
```
