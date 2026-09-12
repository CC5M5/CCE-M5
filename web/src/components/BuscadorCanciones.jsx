import { useState, useMemo } from 'react';
import { Search } from 'lucide-react';

export default function BuscadorCanciones({ basePath = '/' }) {
  const [query, setQuery] = useState('');

  const handleChange = (e) => {
    const value = e.target.value;
    setQuery(value);
    const url = new URL(window.location.href);
    if (value.trim()) {
      url.searchParams.set('q', value.trim());
    } else {
      url.searchParams.delete('q');
    }
    window.history.replaceState({}, '', url);
    filterList(value, url.searchParams.get('momento') || '');
  };

  const filterList = (q, momento) => {
    const lowerQ = q.toLowerCase().trim();
    const lowerM = momento.toLowerCase().trim();
    const items = document.querySelectorAll('#listado-canciones li');
    items.forEach((li) => {
      const text = li.textContent.toLowerCase();
      const momentoEl = li.querySelector('.bg-liturgia-verde\\/10');
      const momentoText = momentoEl ? momentoEl.textContent.toLowerCase() : '';
      const matchQ = !lowerQ || text.includes(lowerQ);
      const matchM = !lowerM || momentoText.includes(lowerM);
      li.style.display = matchQ && matchM ? '' : 'none';
    });
    document.querySelectorAll('#listado-canciones > div').forEach((div) => {
      const visible = div.querySelectorAll('li:not([style*="display: none"])').length > 0;
      div.style.display = visible ? '' : 'none';
    });
  };

  const handleSubmit = (e) => {
    e.preventDefault();
  };

  return (
    <form onSubmit={handleSubmit} className="w-full" role="search">
      <label htmlFor="buscador-canciones" className="sr-only">Buscar canción</label>
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" aria-hidden="true" />
        <input
          id="buscador-canciones"
          type="search"
          value={query}
          onChange={handleChange}
          placeholder="Buscar canción..."
          className="w-full pl-10 pr-4 py-3 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-liturgia-verde focus:border-transparent bg-white"
          autoComplete="off"
        />
      </div>
    </form>
  );
}
