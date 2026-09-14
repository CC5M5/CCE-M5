import { useState, useMemo } from 'react';
import { Eye, EyeOff, Play, ArrowLeft } from 'lucide-react';

/**
 * Sanitiza HTML del contenido de canciones con acordes.
 * Evita inyección de scripts, estilos y handlers inline.
 * Permite solo las etiquetas/estilos de presentación necesarios para las letras.
 */
function sanitizarHtml(html) {
  if (!html) return '';

  const temp = document.createElement('div');
  temp.innerHTML = html;

  const tagsPermitidas = ['BR', 'P', 'DIV', 'SPAN', 'B', 'STRONG', 'I', 'EM', 'U', 'SUP', 'SUB', 'H1', 'H2', 'H3', 'H4', 'H5', 'H6', 'UL', 'OL', 'LI'];
  const atributosPermitidos = ['class', 'style'];

  const walk = (node) => {
    if (node.nodeType === Node.ELEMENT_NODE) {
      const tag = node.tagName.toUpperCase();
      if (!tagsPermitidas.includes(tag)) {
        node.replaceWith(...node.childNodes);
        return;
      }

      for (const attr of Array.from(node.attributes)) {
        const name = attr.name.toLowerCase();
        if (!atributosPermitidos.includes(name)) {
          node.removeAttribute(attr.name);
          continue;
        }
        if (name === 'style') {
          const value = attr.value
            .replace(/expression\s*\(/gi, '')
            .replace(/javascript\s*:/gi, '')
            .replace(/data\s*:/gi, '')
            .replace(/behavior\s*:/gi, '');
          node.setAttribute(attr.name, value);
        }
      }

      if (/^on\w+/i.test(tag)) {
        node.replaceWith(...node.childNodes);
        return;
      }
    }

    for (const child of Array.from(node.childNodes)) {
      walk(child);
    }
  };

  for (const child of Array.from(temp.childNodes)) {
    walk(child);
  }

  return temp.innerHTML;
}

export default function VisorAcordes({ htmlVisual, titulo, slug, tono, enlaceAudio, compact = false }) {
  const [conAcordes, setConAcordes] = useState(true);

  const htmlSeguro = useMemo(() => {
    if (typeof document === 'undefined') {
      // SSR: sanitización básica con regex (sin DOM)
      return (htmlVisual || '')
        .replace(/<script\b[^\<]*(?:(?!<\/script>)<[^\<]*)*<\/script>/gi, '')
        .replace(/javascript:/gi, '')
        .replace(/on\w+\s*=/gi, '');
    }
    return sanitizarHtml(htmlVisual || '');
  }, [htmlVisual]);

  const handleToggle = () => {
    setConAcordes((prev) => !prev);
  };

  const className = conAcordes
    ? 'cancion-con-acordes'
    : 'cancion-con-acordes sin-acordes';

  return (
    <div className={`bg-white rounded-xl border border-slate-200 ${compact ? 'p-4' : 'p-6 md:p-8'} font-mono leading-relaxed`}>
      {!compact && (
        <div className="flex flex-wrap items-center gap-3 mb-4 no-print">
          <button
            type="button"
            onClick={handleToggle}
            className="btn-secondary text-sm"
            aria-pressed={conAcordes}
          >
            {conAcordes ? (
              <>
                <EyeOff className="w-4 h-4" /> Sin acordes
              </>
            ) : (
              <>
                <Eye className="w-4 h-4" /> Con acordes
              </>
            )}
          </button>

          {tono && (
            <span className="inline-flex items-center px-3 py-1.5 rounded-lg bg-slate-100 text-slate-700 text-sm font-medium">
              Tono: {tono}
            </span>
          )}

          {enlaceAudio ? (
            <a
              href={enlaceAudio}
              target="_blank"
              rel="noopener noreferrer"
              className="btn-secondary text-sm"
            >
              <Play className="w-4 h-4" /> Escuchar
            </a>
          ) : (
            <button
              type="button"
              disabled
              className="btn-secondary text-sm opacity-50 cursor-not-allowed"
              title="Audio no disponible"
            >
              <Play className="w-4 h-4" /> Audio no disponible
            </button>
          )}

          <a
            href="/cancionero/"
            className="btn-secondary text-sm"
          >
            <ArrowLeft className="w-4 h-4" /> Volver al cancionero
          </a>
        </div>
      )}

      <div
        className={className}
        dangerouslySetInnerHTML={{ __html: htmlSeguro }}
        aria-label={`Letra ${conAcordes ? 'con acordes' : 'sin acordes'} de ${titulo}`}
      />
    </div>
  );
}
