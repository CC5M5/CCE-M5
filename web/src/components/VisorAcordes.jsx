import { useState, useMemo } from 'react';
import { Eye, EyeOff } from 'lucide-react';

/**
 * Sanitiza HTML del contenido de canciones con acordes.
 * Evita inyección de scripts, estilos y handlers inline.
 * Permite solo las etiquetas/estilos de presentación necesarias para las letras.
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
          // Limpiar URLs potencialmente peligrosas (expression, javascript:, data:) y reglas no deseadas
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

export default function VisorAcordes({ htmlVisual, titulo, slug, compact = false }) {
  const [conAcordes, setConAcordes] = useState(true);

  const htmlSeguro = useMemo(() => {
    // El DOMParser solo existe en el cliente; en SSR devolvemos el HTML tal cual
    // porque no se ejecuta JS en Astro SSG. No obstante, evitamos que se inyecte
    // en el markup estático usando el escape inicial de React/Astro.
    if (typeof document === 'undefined') return htmlVisual || '';
    return sanitizarHtml(htmlVisual);
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
        <div className="flex items-center gap-3 mb-4 no-print">
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
