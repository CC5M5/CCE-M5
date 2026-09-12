import { useState, useEffect } from 'react';
import { Filter } from 'lucide-react';

export default function FiltroMomentos({ momentos = [], basePath = '/' }) {
  const [selected, setSelected] = useState('');

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    setSelected(params.get('momento') || '');
  }, []);

  const handleChange = (e) => {
    const value = e.target.value;
    setSelected(value);
    const url = new URL(window.location.href);
    if (value) {
      url.searchParams.set('momento', value);
    } else {
      url.searchParams.delete('momento');
    }
    window.history.replaceState({}, '', url);
    filterList(url.searchParams.get('q') || '', value);
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

  return (
    <div className="flex items-center gap-2 min-w-[12rem]">
      <Filter className="w-5 h-5 text-slate-400 flex-shrink-0" aria-hidden="true" />
      <label htmlFor="filtro-momentos" className="sr-only">Filtrar por momento litúrgico</label>
      <select
        id="filtro-momentos"
        value={selected}
        onChange={handleChange}
        className="w-full px-3 py-3 rounded-lg border border-slate-300 focus:outline-none focus:ring-2 focus:ring-liturgia-verde focus:border-transparent bg-white"
      >
        <option value="">Todos los momentos</option>
        {momentos.map((m) => (
          <option key={m} value={m}>{m}</option>
        ))}
      </select>
    </div>
  );
}
