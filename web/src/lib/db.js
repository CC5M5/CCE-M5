import { readFileSync } from 'node:fs';
import path from 'node:path';
import { slugify } from './slug.js';

// Astro build runs from the web/ directory, so data files live in ./data
const DATA_DIR = path.resolve(process.cwd(), 'data');

let cache = null;

function loadData() {
  if (cache) return cache;
  const read = (name) => JSON.parse(readFileSync(path.join(DATA_DIR, name), 'utf-8'));
  cache = {
    canciones: read('canciones.json'),
    cancionMomentos: read('cancion_momentos.json'),
    presentaciones: read('presentaciones.json'),
    comentarios: read('comentarios.json'),
  };
  return cache;
}

function enrichCancion(row) {
  const data = loadData();
  const momentos = data.cancionMomentos
    .filter((cm) => cm.cancion_id === row.id)
    .map((cm) => cm.momento_liturgico);
  return {
    ...row,
    momentos: momentos.length ? momentos : (row.momento_liturgico ? [row.momento_liturgico] : []),
  };
}

function enrichPresentacion(row) {
  return row;
}

export function getLatestPresentacion() {
  const data = loadData();
  const row = data.presentaciones[0] || null;
  return row ? enrichPresentacion(row) : null;
}

export function getPresentacionByFecha(fecha) {
  const data = loadData();
  const row = data.presentaciones.find((p) => p.fecha_domingo === fecha) || null;
  return row ? enrichPresentacion(row) : null;
}

export function getRecentPresentaciones(limit = 6) {
  const data = loadData();
  return data.presentaciones.slice(0, limit).map(enrichPresentacion);
}

export function getAllPresentacionesFechas() {
  const data = loadData();
  return data.presentaciones.map((p) => p.fecha_domingo);
}

export function getCanciones() {
  const data = loadData();
  return data.canciones.map(enrichCancion);
}

export function getCancionBySlug(slug) {
  const data = loadData();
  const row = data.canciones.find((c) => slugify(c.titulo) === slug) || null;
  return row ? enrichCancion(row) : null;
}

export function getCancionesByMomento(momento) {
  const data = loadData();
  const ids = new Set(
    data.cancionMomentos
      .filter((cm) => cm.momento_liturgico && cm.momento_liturgico.toLowerCase() === momento.toLowerCase())
      .map((cm) => cm.cancion_id)
  );
  return data.canciones
    .filter((c) => ids.has(c.id))
    .map(enrichCancion);
}

export function getAllMomentos() {
  const data = loadData();
  const set = new Set(data.cancionMomentos.map((cm) => cm.momento_liturgico).filter(Boolean));
  return Array.from(set).sort((a, b) => a.localeCompare(b, undefined, { sensitivity: 'base' }));
}

export function getAllCancionesSlugs() {
  const data = loadData();
  return data.canciones
    .filter((c) => c.titulo)
    .map((c) => ({ id: c.id, slug: slugify(c.titulo) }));
}

export function getComentariosAprobados(limit = 20) {
  const data = loadData();
  return data.comentarios.slice(0, limit);
}

export function getCancionesPresentacion(fecha) {
  const presentacion = getPresentacionByFecha(fecha);
  if (!presentacion || !presentacion.canciones_json) return [];
  try {
    const parsed = JSON.parse(presentacion.canciones_json);
    const ids = Array.isArray(parsed) ? parsed : Object.values(parsed);
    if (!ids.length) return [];
    const uniqueIds = [...new Set(ids)];
    const data = loadData();
    const rows = data.canciones
      .filter((c) => uniqueIds.includes(c.id))
      .map(enrichCancion);
    const orderMap = new Map(ids.map((id, idx) => [id, idx]));
    rows.sort((a, b) => (orderMap.get(a.id) || 0) - (orderMap.get(b.id) || 0));
    return rows;
  } catch {
    return [];
  }
}

export function getLatestPresentacionFecha() {
  const data = loadData();
  const row = data.presentaciones[0];
  return row ? row.fecha_domingo : null;
}

export function closeDb() {
  cache = null;
}
