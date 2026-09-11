# Spec 06: Especificaciones Web

## Visión General

La web es el punto central de acceso para:
1. **Comunidad**: Ver presentaciones semanales y descargarlas
2. **Músicos**: Acceder a hojas con acordes
3. **Visitantes**: Explorar el cancionero escolapio completo
4. **Comentaristas**: Sugerir canciones o reportar errores

## Tecnología

| Capa | Tecnología | Justificación |
|------|------------|---------------|
| Framework | Astro 4.x | SSG rápido, islands architecture |
| Estilos | Tailwind CSS | Utilidades, responsive, customizable |
| Interactividad | React (islands) | Componentes dinámicos donde se necesite |
| Fuentes | Google Fonts | Montserrat (títulos), Merriweather (lecturas) |
| Iconos | Lucide React | Livianos, modernos |
| Hosting | GitHub Pages | Gratuito, CI/CD integrado |
| Analytics | Plausible (opcional) | Respeto a la privacidad |

## Estructura de Rutas

```
/
├── /                           # Página principal: presentación semanal
├── /presentacion/
│   └── /[fecha]/               # Presentación específica (ej: /presentacion/2026-09-13/)
│       ├── /                   # Vista general
│       └── /descargas          # Centro de descargas
├── /cancionero/
│   ├── /                       # Listado completo (alfabético)
│   ├── /momento/[momento]/     # Filtrar por momento litúrgico
│   ├── /tema/[tema]/           # Filtrar por tema
│   └── /[slug]/               # Detalle de canción
├── /musicos/
│   └── /[fecha]/              # Hoja de músicos de esa semana
├── /lecturas/
│   └── /[fecha]/              # Lecturas de esa fecha
├── /comentarios/             # Formulario y listado
└── /sobre/                    # Sobre el proyecto, contacto
```

## Diseño de Pantallas

### 1. Página Principal (/)

```
┌─────────────────────────────────────────────────────────────────┐
│  🎵 CCE M5 Music    [Inicio] [Cancionero] [Músicos] [Sobre]     │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                                                          │   │
│  │     DOMINGO XXIV DE TIEMPO ORDINARIO                     │   │
│  │     13 de Septiembre de 2026                             │   │
│  │                                                          │   │
│  │     [▶️ Ver presentación]  [⬇️ Descargar PPTX]           │   │
│  │     [⬇️ Descargar PDF]  [🎵 Hoja músicos (PDF)]          │   │
│  │                                                          │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  📖 Lecturas del día:                                            │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Primera lectura: Eclo 27,30-28,7                        │   │
│  │  Salmo: Sal 102(103) — "El Señor es compasivo..."        │   │
│  │  Evangelio: Mt 18,21-35 — "Perdonad setenta veces..."  │   │
│  │  [Ver lecturas completas →]                              │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  🎶 Selección musical:                                           │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Entrada: "Al encuentro"                                   │   │
│  │  Gloria: "Gloria de Nazaret"                              │   │
│  │  ...                                                       │   │
│  │  [Ver hoja completa de músicos →]                         │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  📅 Semanas anteriores:                                          │
│  [6 Sep] [30 Ago] [23 Ago] [...]                                  │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 2. Cancionero (/cancionero/)

```
┌─────────────────────────────────────────────────────────────────┐
│  🎵 CCE M5 Music    [Inicio] [Cancionero] [Músicos] [Sobre]     │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  🔍 Buscar canción...                                           │
│                                                                  │
│  Filtrar por momento: [Todos] [Entrada] [Gloria] [Aleluya] ... │
│                                                                  │
│  Ordenar: [Alfabético ▼] [Momento litúrgico] [Tono]            │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  A                                                     A │   │
│  │  ─────────────────────────────────────────────────────── │   │
│  │  • A tu amparo y protección          [Entrada]   [Do]   │   │
│  │  • Al encuentro                      [Entrada]   [Do]   │   │
│  │  • Al calor de la palabra            [Entrada]   [Re]  │   │
│  │                                                          │   │
│  │  C                                                     C │   │
│  │  ─────────────────────────────────────────────────────── │   │
│  │  • Como Tus brazos                   [Comunión]  [Sol]  │   │
│  │  • Cristo vive                       [Despedida] [Do]   │   │
│  │                                                          │   │
│  │  ...                                                     │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  Total: 53 canciones en el cancionero                           │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 3. Detalle de Canción (/cancionero/[slug]/)

```
┌─────────────────────────────────────────────────────────────────┐
│  🎵 CCE M5 Music    [Inicio] [Cancionero] [Músicos] [Sobre]     │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  🎵 A tu amparo y protección                                    │
│  ─────────────────────────────────────────────────────────────   │
│                                                                  │
│  Momento: Entrada    |    Tono: Do    |    Tempo: Moderado       │
│                                                                  │
│  Temas: María, protección, esperanza                             │
│  Referencias: Lc 1,28-33                                         │
│                                                                  │
│  🎧 Escuchar: [▶️ YouTube] [🔗 Versión alternativa]               │
│                                                                  │
│  [Con acordes] [Sin acordes]                                    │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Do     Sol     Lam    Fa                                 │   │
│  │  A TU AMPARO Y PROTECCIÓN,                                 │   │
│  │                                                           │   │
│  │  Do           Sol    Fa    Sol                             │   │
│  │  MADRE DE DIOS, ACUDIMOS.                                  │   │
│  │                                                           │   │
│  │  Lam    Mim    Fa                                          │   │
│  │  NO DESOIGUES NUESTROS RUEGOS                              │   │
│  │                                                           │   │
│  │  Sol    Do                                                 │   │
│  │  Y DE TODOS LOS PELIGROS,                                    │   │
│  │                                                           │   │
│  │  Fa     Sol                                                │   │
│  │  VIRGEN GLORIOSA Y BENDITA,                                  │   │
│  │                                                           │   │
│  │  Sol7   Do                                                 │   │
│  │  DEFIENDE SIEMPRE A TUS HIJOS                                │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  [🖨️ Imprimir] [📋 Copiar] [📤 Compartir]                       │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 4. Vista Músicos (/musicos/[fecha]/)

```
┌─────────────────────────────────────────────────────────────────┐
│  🎵 CCE M5 Music    [Inicio] [Cancionero] [Músicos] [Sobre]     │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  🎼 Hoja de Músicos                                              │
│  Domingo XXIV de Tiempo Ordinario — 13 Septiembre 2026          │
│                                                                  │
│  [🖨️ Imprimir] [⬇️ Descargar PDF] [📧 Compartir]               │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  1. ENTRADA — "Al encuentro" (Do)                         │   │
│  │  ─────────────────────────────────────────────────────── │   │
│  │  Do      Sol      Lam     Fa                             │   │
│  │  AL ENCUENTRO VOY, CAMINANDO VOY,                          │   │
│  │                                                         │   │
│  │  ...                                                     │   │
│  │                                                         │   │
│  │  2. GLORIA — "Gloria de Nazaret" (Mi)                    │   │
│  │  ─────────────────────────────────────────────────────── │   │
│  │  Mi      Si       Do#m                                   │   │
│  │  GLORIA A DIOS EN LO ALTO DEL CIELO...                    │   │
│  │                                                         │   │
│  │  ... (continúa con los 12 momentos) ...                  │   │
│  │                                                         │   │
│  │  12. DESPEDIDA — "Cristo vive" (Do)                    │   │
│  │  ─────────────────────────────────────────────────────── │   │
│  │  Do      Sol                                             │   │
│  │  CRISTO VIVE, CRISTO REINA,                               │   │
│  │                                                         │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  📝 Notas: Celebración normal. Sin eventos especiales.           │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 5. Comentarios (/comentarios/)

```
┌─────────────────────────────────────────────────────────────────┐
│  🎵 CCE M5 Music    [Inicio] [Cancionero] [Músicos] [Sobre]     │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  💬 Comentarios y Sugerencias                                    │
│                                                                  │
│  ¿Tienes una sugerencia para la liturgia? ¿Has encontrado un    │
│  error? Cuéntanos:                                               │
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  Tu nombre: [________________]                            │   │
│  │  Email:     [________________]                            │   │
│  │  Tipo:      [🎵 Sug. musical] [✏️ Corrección] [💬 Otro] │   │
│  │  Mensaje:                                                 │   │
│  │  ┌─────────────────────────────────────────────────────┐  │   │
│  │  │                                                     │  │   │
│  │  └─────────────────────────────────────────────────────┘  │   │
│  │                                                           │   │
│  │  [Enviar comentario]                                     │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
│  📋 Comentarios recientes:                                      │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │  María G. — hace 2 días                                  │   │
│  │  "Para la próxima semana sugiero 'Como el Padre me amó'   │   │
│  │   para comunión, va muy bien con el Evangelio."          │   │
│  │  [✅ Aprobado]                                             │   │
│  │  ──────────────────────────────────────────────────────  │   │
│  │  Juan P. — hace 5 días                                    │   │
│  │  "Hay un error en el salmo de la semana pasada."         │   │
│  │  [✅ Aprobado] [✏️ Corregido]                            │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Especificaciones Técnicas Web

### Performance
- **Lighthouse score**: > 90 en todas las categorías
- **Tiempo de carga**: < 3s en 3G
- **Tamaño página inicial**: < 500KB
- **Imágenes**: WebP con fallback JPEG, lazy loading

### SEO
- Meta tags por página
- Open Graph para compartir
- Sitemap.xml automático
- robots.txt

### Accesibilidad
- Contraste WCAG AA
- Navegación por teclado
- ARIA labels en componentes interactivos
- Skip links

### Responsive Breakpoints
| Nombre | Ancho | Dispositivo |
|--------|-------|-------------|
| sm | 640px | Móvil grande |
| md | 768px | Tablet |
| lg | 1024px | Desktop pequeño |
| xl | 1280px | Desktop |
| 2xl | 1536px | Desktop grande |

## Backend de Comentarios (GitHub Issues API)

### Flujo

```
Usuario envía comentario
        │
        ▼
┌─────────────────┐
│ Formulario web  │
│ (HTML + JS)     │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ GitHub Issues   │
│ API (fetch)     │
│ POST /repos/... │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Issue creado    │
│ Label: "web-    │
│ comment"        │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ OpenClaw agent  │
│ (cada 6h)       │
│ GET issues con  │
│ label "pendiente"│
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Usuario decide  │
│ aprobar/rechazar│
└─────────────────┘
```

### Estructura de Issues

```yaml
Title: "[Comentario] Sugerencia musical - Domingo 13 Sep"
Labels: ["web-comment", "pendiente"]
Body: |
  **Autor**: María García
  **Email**: maria@email.com
  **Tipo**: Sugerencia musical
  **Presentación**: 2026-09-13
  **Mensaje**:
  Para la próxima semana sugiero "Como el Padre me amó" 
  para comunión, va muy bien con el Evangelio.
```

## Despliegue

### GitHub Actions Workflow

```yaml
name: Deploy to GitHub Pages

on:
  push:
    branches: [main]
  workflow_dispatch:

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: 20
      - run: npm ci
      - run: npm run build
      - uses: actions/upload-pages-artifact@v3
        with:
          path: ./dist

  deploy:
    needs: build
    runs-on: ubuntu-latest
    permissions:
      pages: write
      id-token: write
    steps:
      - uses: actions/deploy-pages@v4
```

### Dominio Personalizado (Opcional)
- Configurar CNAME: `cancionero.ccem5.org` o similar
- DNS: CNAME → `usuario.github.io`
