import { useState } from 'react';
import { Send, Loader2 } from 'lucide-react';

const TIPOS = [
  { id: 'sugerencia', label: '🎵 Sug. musical', color: 'bg-purple-100 text-purple-800 border-purple-200' },
  { id: 'correccion', label: '✏️ Corrección', color: 'bg-orange-100 text-orange-800 border-orange-200' },
  { id: 'otro', label: '💬 Otro', color: 'bg-slate-100 text-slate-800 border-slate-200' },
];

const MAX_MENSAJE = 2000;
const MAX_NOMBRE = 100;
const MAX_PRESENTACION = 30;

export default function FormularioComentarios({ basePath = '/' }) {
  const [form, setForm] = useState({ nombre: '', email: '', tipo: 'sugerencia', presentacion: '', mensaje: '' });
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState('');

  const handleChange = (e) => {
    const { name, value } = e.target;
    setForm((f) => ({ ...f, [name]: value }));
  };

  const handleTipoClick = (tipo) => {
    setForm((f) => ({ ...f, tipo }));
  };

  const escapeMarkdown = (str) => (str || '').replace(/[\r\n]/g, ' ').trim();

  const validateEmail = (email) => {
    if (!email) return false;
    // RFC 5322 simplificado, suficiente para front-end
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError('');

    try {
      const nombre = escapeMarkdown(form.nombre.slice(0, MAX_NOMBRE));
      const email = form.email.trim().slice(0, 254);
      const presentacion = escapeMarkdown(form.presentacion.slice(0, MAX_PRESENTACION));
      const mensaje = form.mensaje.trim().slice(0, MAX_MENSAJE);

      if (!nombre) {
        throw new Error('Por favor, introduce tu nombre.');
      }
      if (!validateEmail(email)) {
        throw new Error('Por favor, introduce un email válido.');
      }
      if (!mensaje) {
        throw new Error('Por favor, escribe un mensaje.');
      }

      const tipoLabel = TIPOS.find((t) => t.id === form.tipo)?.label || 'Otro';
      const title = `[Comentario] ${tipoLabel.replace(/[^a-zA-Z0-9áéíóúñüÁÉÍÓÚÑÜ\s]/g, '').trim()}${presentacion ? ` - Domingo ${presentacion}` : ''}`.slice(0, 256);
      const body = `**Autor**: ${nombre || 'Anónimo'}\n**Email**: ${email || 'No proporcionado'}\n**Tipo**: ${tipoLabel}\n**Presentación**: ${presentacion || 'No especificada'}\n**Mensaje**:\n${mensaje}`;

      const owner = import.meta.env.PUBLIC_GITHUB_REPO_OWNER || 'cce-m5';
      const repo = import.meta.env.PUBLIC_GITHUB_REPO_NAME || 'cce-m5-music';
      // El token debe viajar desde una variable de entorno PÚBLICA porque este es un sitio
      // estático que se ejecuta en el navegador. Para evitar exposición permanente, la app
      // puede apuntar a un proxy/edge function en el futuro. Hasta entonces, usamos la
      // variable pública documentada en la spec.
      const token = import.meta.env.PUBLIC_GITHUB_TOKEN;

      if (!token) {
        throw new Error('No está configurado el token de GitHub para enviar comentarios.');
      }

      const res = await fetch(`https://api.github.com/repos/${owner}/${repo}/issues`, {
        method: 'POST',
        headers: {
          'Accept': 'application/vnd.github+json',
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          title,
          body,
          labels: ['web-comment', 'pendiente'],
        }),
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.message || `Error ${res.status} al enviar el comentario.`);
      }

      setSuccess(true);
      setForm({ nombre: '', email: '', tipo: 'sugerencia', presentacion: '', mensaje: '' });
    } catch (err) {
      setError(err.message || 'Ocurrió un error al enviar el comentario.');
    } finally {
      setLoading(false);
    }
  };

  if (success) {
    return (
      <div className="card bg-green-50 border-green-200">
        <h2 className="text-lg font-heading font-bold text-green-800 mb-2">¡Gracias por tu comentario!</h2>
        <p className="text-green-700 mb-4">Lo hemos recibido y será revisado pronto.</p>
        <button type="button" onClick={() => setSuccess(false)} className="btn-secondary">
          Enviar otro
        </button>
      </div>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="card space-y-5" noValidate>
      <div>
        <label htmlFor="nombre" className="block text-sm font-medium text-slate-700 mb-1">Tu nombre</label>
        <input
          id="nombre"
          name="nombre"
          type="text"
          value={form.nombre}
          onChange={handleChange}
          required
          maxLength={MAX_NOMBRE}
          className="w-full px-3 py-2 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-liturgia-verde focus:border-transparent"
          placeholder="María García"
        />
      </div>

      <div>
        <label htmlFor="email" className="block text-sm font-medium text-slate-700 mb-1">Email</label>
        <input
          id="email"
          name="email"
          type="email"
          value={form.email}
          onChange={handleChange}
          required
          maxLength={254}
          className="w-full px-3 py-2 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-liturgia-verde focus:border-transparent"
          placeholder="maria@email.com"
        />
      </div>

      <div>
        <span className="block text-sm font-medium text-slate-700 mb-2">Tipo de comentario</span>
        <div className="flex flex-wrap gap-2" role="group" aria-label="Tipo de comentario">
          {TIPOS.map((tipo) => (
            <button
              key={tipo.id}
              type="button"
              onClick={() => handleTipoClick(tipo.id)}
              className={`px-3 py-2 rounded-lg border text-sm font-medium transition ${
                form.tipo === tipo.id
                  ? `${tipo.color} ring-2 ring-offset-1 ring-liturgia-verde`
                  : 'bg-white text-slate-600 border-slate-300 hover:bg-slate-50'
              }`}
              aria-pressed={form.tipo === tipo.id}
            >
              {tipo.label}
            </button>
          ))}
        </div>
      </div>

      <div>
        <label htmlFor="presentacion" className="block text-sm font-medium text-slate-700 mb-1">Presentación (opcional)</label>
        <input
          id="presentacion"
          name="presentacion"
          type="text"
          value={form.presentacion}
          onChange={handleChange}
          maxLength={MAX_PRESENTACION}
          className="w-full px-3 py-2 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-liturgia-verde focus:border-transparent"
          placeholder="2026-09-13"
        />
      </div>

      <div>
        <label htmlFor="mensaje" className="block text-sm font-medium text-slate-700 mb-1">Mensaje</label>
        <textarea
          id="mensaje"
          name="mensaje"
          value={form.mensaje}
          onChange={handleChange}
          required
          rows={5}
          maxLength={MAX_MENSAJE}
          className="w-full px-3 py-2 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-liturgia-verde focus:border-transparent"
          placeholder="Escribe aquí tu sugerencia o corrección..."
        />
        <p className="text-xs text-slate-500 mt-1" aria-live="polite">{form.mensaje.length}/{MAX_MENSAJE}</p>
      </div>

      {error && (
        <div className="p-3 rounded-lg bg-red-50 text-red-800 text-sm" role="alert">{error}</div>
      )}

      <button
        type="submit"
        disabled={loading}
        className="btn-primary w-full sm:w-auto disabled:opacity-60 disabled:cursor-not-allowed"
      >
        {loading ? (
          <>
            <Loader2 className="w-4 h-4 animate-spin" /> Enviando...
          </>
        ) : (
          <>
            <Send className="w-4 h-4" /> Enviar comentario
          </>
        )}
      </button>
    </form>
  );
}
