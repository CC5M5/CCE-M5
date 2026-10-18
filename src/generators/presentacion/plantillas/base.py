"""Plantilla base HTML para presentaciones Reveal.js."""

TEMPLATE = """<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{titulo}</title>
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/reveal.js@4.5.0/dist/reveal.css">
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/reveal.js@4.5.0/dist/theme/white.css">
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Fredoka:wght@400;600&family=Nunito:wght@400;600;700&display=swap');

    :root {{
      --liturgia-from: {from_color};
      --liturgia-to: {to_color};
      --liturgia-acento: {acento};
      --oro: #A16207;
      --morado: #7C3AED;
      --blanco-tarjeta: rgba(255,255,255,0.94);
    }}

    .reveal {{
      font-family: 'Nunito', 'Open Sans', sans-serif;
      font-size: 40px;
      color: #2c3e50;
    }}

    .reveal {{
      aspect-ratio: 4 / 3;
      max-width: 100vw;
      max-height: 100vh;
      margin: auto;
    }}

    .reveal .slides {{
      text-align: left;
      aspect-ratio: 4 / 3;
    }}

    .reveal .slides section {{
      aspect-ratio: 4 / 3;
      width: 100%;
      height: 100%;
    }}

    .reveal .slides section {{
      padding: 0;
      background: linear-gradient(135deg, #FAF5FF 0%, #F5F3FF 50%, #F0F4F8 100%);
    }}

    .slide-wrapper {{
      width: 100%;
      height: 100%;
      display: flex;
      flex-direction: column;
      justify-content: center;
      align-items: flex-start;
      position: relative;
      overflow: hidden;
      box-sizing: border-box;
    }}

    .reveal .slides section::before {{
      content: '';
      position: absolute;
      top: 0;
      left: 0;
      right: 0;
      height: 8px;
      background: linear-gradient(90deg, var(--liturgia-acento), var(--oro), var(--liturgia-acento));
      z-index: 20;
    }}

    .reveal h1, .reveal h2, .reveal h3 {{
      font-family: 'Fredoka', 'Montserrat', sans-serif;
      color: var(--liturgia-acento);
      text-transform: uppercase;
      margin-bottom: 0.3em;
      line-height: 1.15;
      font-weight: 600;
      letter-spacing: -0.01em;
    }}

    .reveal h1 {{ font-size: 1.35em; }}
    .reveal h2 {{ font-size: 0.95em; font-weight: 400; text-transform: none; color: #555; }}
    .reveal h3 {{ font-size: 0.72em; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em; opacity: 0.85; }}

    .reveal .lectura .tarjeta,
    .reveal .primera_lectura .tarjeta,
    .reveal .segunda_lectura .tarjeta,
    .reveal .salmo .tarjeta,
    .reveal .evangelio .tarjeta {{
      max-width: 92%;
      margin: 30px 40px 110px 40px;
      max-height: 70%;
    }}

    .reveal .lectura .ilustracion,
    .reveal .primera_lectura .ilustracion,
    .reveal .segunda_lectura .ilustracion,
    .reveal .salmo .ilustracion,
    .reveal .evangelio .ilustracion {{
      display: none;
    }}

    .reveal p, .reveal li {{
      line-height: 1.5;
      margin-bottom: 0.5em;
    }}

    .reveal .tarjeta {{
      background: var(--blanco-tarjeta);
      border-radius: 24px;
      padding: 24px 32px;
      margin: 30px 40px 110px 40px;
      box-shadow: 0 20px 60px rgba(124, 58, 237, 0.12);
      backdrop-filter: blur(10px);
      border: 1px solid rgba(124, 58, 237, 0.12);
      max-height: 70%;
      overflow: auto;
      position: relative;
      z-index: 5;
    }}

    .reveal .tarjeta::after {{
      content: '';
      position: absolute;
      bottom: 0;
      left: 0;
      width: 100%;
      height: 6px;
      background: linear-gradient(90deg, var(--liturgia-acento), var(--oro));
      border-radius: 0 0 24px 24px;
    }}

    .reveal .cita {{
      font-size: 0.85em;
      font-weight: 700;
      margin-bottom: 0.6em;
      padding: 0.25em 0.7em;
      display: inline-block;
      background: linear-gradient(90deg, var(--liturgia-acento), var(--oro));
      color: white;
      border-radius: 8px;
    }}

    .reveal .contenido {{
      white-space: pre-wrap;
      max-height: none;
      overflow: visible;
      font-size: 0.9em;
      line-height: 1.22;
    }}

    .reveal .primera_lectura .contenido,
    .reveal .segunda_lectura .contenido,
    .reveal .evangelio .contenido {{
      font-size: 1em;
      line-height: 1.18;
    }}

    .reveal .salmo .contenido {{
      font-size: 0.95em;
      line-height: 1.22;
    }}

    .reveal .primera_lectura .tarjeta,
    .reveal .segunda_lectura .tarjeta,
    .reveal .salmo .tarjeta,
    .reveal .evangelio .tarjeta {{
      padding: 18px 24px;
      max-width: 95%;
      margin: 20px 30px 110px 30px;
    }}

    .reveal .logo-lema {{
      position: absolute;
      bottom: 22px;
      right: 30px;
      height: 55px;
      width: auto;
      max-width: 180px;
      z-index: 10;
      filter: drop-shadow(0 2px 4px rgba(0,0,0,0.1));
    }}

    .reveal .ilustracion {{
      position: absolute;
      top: auto;
      bottom: 90px;
      right: 70px;
      max-width: 280px;
      max-height: 280px;
      opacity: 0.98;
      z-index: 6;
      border-radius: 20px;
      box-shadow: 0 12px 40px rgba(0,0,0,0.12);
      object-fit: contain;
    }}

    section:has(.ilustracion) .tarjeta {{
      margin-right: 320px;
    }}

    .reveal .portada .slide-wrapper {{
      text-align: center;
      justify-content: center;
      align-items: center;
      background: linear-gradient(135deg, var(--liturgia-acento) 0%, #6D28D9 40%, #7C3AED 70%, var(--oro) 100%);
    }}

    .reveal .portada .tarjeta {{
      background: rgba(255,255,255,0.96);
      max-width: 760px;
      margin: 0 auto;
      text-align: center;
    }}

    .reveal .portada h1 {{
      text-align: center;
      font-size: 1.8em;
      margin-top: 0;
    }}

    .reveal .portada h2 {{
      text-align: center;
      font-size: 1.1em;
      color: #555;
      text-transform: none;
      font-weight: 400;
      margin-top: 0.5em;
    }}

    .reveal .portada .ilustracion {{
      position: relative;
      top: auto;
      right: auto;
      bottom: auto;
      max-width: 320px;
      max-height: 320px;
      margin: 0 auto 1em;
    }}

    .reveal .transicion .slide-wrapper,
    .reveal .paso .slide-wrapper {{
      justify-content: center;
      align-items: center;
    }}

    .reveal .transicion .tarjeta,
    .reveal .paso .tarjeta {{
      text-align: center;
      display: flex;
      flex-direction: column;
      justify-content: center;
      align-items: center;
      min-height: 55%;
      max-width: 78%;
      background: rgba(255,255,255,0.96);
      border-radius: 32px;
      padding: 36px 44px;
      box-shadow: 0 24px 70px rgba(0,0,0,0.22);
    }}

    .reveal .transicion h1,
    .reveal .paso h1 {{
      text-align: center;
      font-size: 2.4em;
      letter-spacing: 0.02em;
      color: var(--liturgia-acento);
      margin-bottom: 0.2em;
    }}

    .reveal .transicion h2,
    .reveal .paso h2 {{
      text-align: center;
      font-size: 1.1em;
      color: #555;
      font-weight: 400;
      margin-bottom: 0.8em;
    }}

    .reveal .transicion .contenido,
    .reveal .paso .contenido {{
      font-size: 1.0em;
      color: #2c3e50;
      text-align: center;
    }}

    .reveal .transicion .ilustracion,
    .reveal .paso .ilustracion {{
      position: relative;
      top: auto;
      right: auto;
      bottom: auto;
      max-width: 220px;
      max-height: 220px;
      margin: 0 auto 1em;
      border-radius: 20px;
      box-shadow: 0 12px 40px rgba(0,0,0,0.18);
    }}

    .reveal .cancion .tarjeta {{
      background: linear-gradient(135deg, rgba(255,255,255,0.96) 0%, rgba(250,245,255,0.96) 100%);
    }}

    .reveal .cancion .contenido {{
      font-size: 0.88em;
      line-height: 1.25;
    }}

    .reveal .cancion .contenido br {{
      display: block;
      content: "";
      margin-bottom: 0.05em;
    }}

    .reveal .salmo .contenido {{
      font-size: 0.95em;
      line-height: 1.18;
    }}

    .reveal .salmo .contenido br {{
      display: block;
      content: "";
      margin-bottom: 0.02em;
    }}

    @keyframes fadeInUp {{
      from {{ opacity: 0; transform: translateY(20px); }}
      to {{ opacity: 1; transform: translateY(0); }}
    }}

    .reveal .slides section.present {{
      animation: fadeInUp 0.5s ease-out;
    }}

    .reveal .contenido::-webkit-scrollbar {{
      width: 6px;
    }}
    .reveal .contenido::-webkit-scrollbar-thumb {{
      background: var(--liturgia-acento);
      border-radius: 3px;
    }}

    @media print {{
      .reveal .slides section {{
        page-break-after: always;
        height: 100vh;
      }}
      .reveal .slides section .slide-wrapper {{
        height: 100vh;
      }}
      .reveal .logo-lema {{
        position: fixed;
        bottom: 20px;
        right: 30px;
      }}
      .slide-wrapper:has(.ilustracion) .tarjeta {{
        margin-right: 340px;
      }}
      .reveal .tarjeta {{
        margin: 30px 40px;
      }}
    }}
  </style>
</head>
<body>
  <div class="reveal">
    <div class="slides">
      {slides_html}
    </div>
  </div>
  <img class="logo-lema" src="assets/lema_somos_uno.jpg" alt="Somos uno" style="display:none;">
  <script src="https://cdn.jsdelivr.net/npm/reveal.js@4.5.0/dist/reveal.js"></script>
  <script>
    Reveal.initialize({{
      hash: true,
      slideNumber: 'c/t',
      transition: 'slide',
      width: 1280,
      height: 960,
      center: true,
      margin: 0.04,
      minScale: 0.2,
      maxScale: 2.0,
    }});

    // Ajustar tamaño de fuente de la tarjeta para llenar la diapositiva sin cortar
    function ajustarTexto(slide) {{
      const tarjeta = slide.querySelector('.tarjeta');
      if (!tarjeta) return;
      const wrapper = slide.querySelector('.slide-wrapper');
      const logo = slide.querySelector('.logo-lema');
      const ilustracion = slide.querySelector('.ilustracion');

      const esLectura = slide.classList.contains('primera_lectura')
                       || slide.classList.contains('segunda_lectura')
                       || slide.classList.contains('salmo')
                       || slide.classList.contains('evangelio')
                       || slide.classList.contains('lectura');

      // Lecturas: un poco mas grande para mejor legibilidad
      let fontSize = esLectura ? 48 : 48;
      tarjeta.style.fontSize = fontSize + 'px';

      const logoHeight = logo ? logo.offsetHeight + 36 : 90;
      const topMargin = 30;
      const bottomSafety = 20;
      const maxHeight = wrapper.clientHeight - topMargin - logoHeight - bottomSafety;

      const ilustracionWidth = ilustracion ? ilustracion.offsetWidth + 60 : 0;
      const maxWidth = wrapper.clientWidth - 80 - ilustracionWidth;

      tarjeta.style.maxHeight = maxHeight + 'px';

      // Reducir hasta que el texto quepa; para lecturas permitimos bajar hasta 28px
      const minSize = esLectura ? 28 : 16;
      while ((tarjeta.scrollHeight > maxHeight || tarjeta.scrollWidth > maxWidth) && fontSize > minSize) {{
        fontSize -= 0.5;
        tarjeta.style.fontSize = fontSize + 'px';
      }}
    }}
    Reveal.on('ready', event => ajustarTexto(event.currentSlide));
    Reveal.on('slidechanged', event => {{
      ajustarTexto(event.currentSlide);
      if (event.previousSlide) {{
        const prevTarjeta = event.previousSlide.querySelector('.tarjeta');
        if (prevTarjeta) prevTarjeta.style.fontSize = '';
      }}
    }});
  </script>
</body>
</html>"""
