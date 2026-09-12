import { useState, useMemo } from 'react';
import { Eye, EyeOff } from 'lucide-react';

function sanitizarHtml(html) {
  if (!html) return '';
  return html
    .replace(/<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi, '')
    .replace(/<style\b[^<]*(?:(?!<\/style>)<[^<]*)*<\/style>/gi, '')
    .replace(/on\w+\s*=/gi, '');
}

export default function VisorAcordes({ htmlVisual, titulo, slug, compact = false }) {
  const [conAcordes, setConAcordes] = useState(true);

  const htmlSeguro = useMemo(() => sanitizarHtml(htmlVisual), [htmlVisual]);

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
