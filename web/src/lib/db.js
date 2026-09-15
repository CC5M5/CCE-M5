import Database from 'better-sqlite3';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import { slugify } from './slug.js';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const DB_PATH = path.resolve(__dirname, '../../../data/db.sqlite3');

let db = null;

function getDb() {
  if (!db) {
    db = new Database(DB_PATH, { readonly: true });
    db.pragma('journal_mode = OFF');
  }
  return db;
}

export function getLatestPresentacion() {
  const row = getDb()
    .prepare(
      `SELECT p.*, l.domingo, l.temporada, l.ciclo, l.color_liturgico,
        l.primera_lectura_cita, l.primera_lectura_texto,
        l.salmo_cita, l.salmo_antifona, l.salmo_texto,
        l.segunda_lectura_cita, l.segunda_lectura_texto,
        l.evangelio_cita, l.evangelio_texto,
        l.fuente_scraping
      FROM presentaciones p
      LEFT JOIN lecturas l ON p.lectura_id = l.id
      WHERE p.estado IN ('publicado', 'generado')
      ORDER BY p.fecha_domingo DESC
      LIMIT 1`
    )
    .get();
  return row || null;
}

export function getPresentacionByFecha(fecha) {
  const row = getDb()
    .prepare(
      `SELECT p.*, l.domingo, l.temporada, l.ciclo, l.color_liturgico,
        l.primera_lectura_cita, l.primera_lectura_texto,
        l.salmo_cita, l.salmo_antifona, l.salmo_texto,
        l.segunda_lectura_cita, l.segunda_lectura_texto,
        l.evangelio_cita, l.evangelio_texto,
        l.fuente_scraping
      FROM presentaciones p
      LEFT JOIN lecturas l ON p.lectura_id = l.id
      WHERE p.fecha_domingo = ?
      LIMIT 1`
    )
    .get(fecha);
  return row || null;
}

export function getRecentPresentaciones(limit = 6) {
  return getDb()
    .prepare(
      `SELECT p.id, p.fecha_domingo, l.domingo, l.temporada, l.color_liturgico
      FROM presentaciones p
      LEFT JOIN lecturas l ON p.lectura_id = l.id
      WHERE p.estado IN ('publicado', 'generado')
      ORDER BY p.fecha_domingo DESC
      LIMIT ?`
    )
    .all(limit);
}

export function getAllPresentacionesFechas() {
  return getDb()
    .prepare(`SELECT fecha_domingo FROM presentaciones WHERE estado IN ('publicado', 'generado') ORDER BY fecha_domingo DESC`)
    .all()
    .map(r => r.fecha_domingo);
}

export function getCanciones() {
  return getDb()
    .prepare(
      `SELECT id, titulo, titulo_url, tono, momento_liturgico, temas, referencias_biblicas,
        html_visual, letra_sin_acordes
      FROM canciones
      WHERE titulo IS NOT NULL AND titulo != ''
      ORDER BY titulo COLLATE NOCASE`
    )
    .all();
}

export function getCancionBySlug(slug) {
  const rows = getDb()
    .prepare(
      `SELECT id, titulo, titulo_url, tono, momento_liturgico, temas, referencias_biblicas,
        html_visual, letra_con_acordes, letra_sin_acordes, acordes_json, estructura_json
      FROM canciones
      WHERE titulo IS NOT NULL AND titulo != ''`
    )
    .all();
  return rows.find(r => slugify(r.titulo) === slug) || null;
}

export function getCancionesByMomento(momento) {
  return getDb()
    .prepare(
      `SELECT id, titulo, titulo_url, tono, momento_liturgico, temas, referencias_biblicas, html_visual
      FROM canciones
      WHERE lower(momento_liturgico) = lower(?)
      ORDER BY titulo COLLATE NOCASE`
    )
    .all(momento);
}

export function getAllMomentos() {
  return getDb()
    .prepare(
      `SELECT DISTINCT momento_liturgico as momento
      FROM canciones
      WHERE momento_liturgico IS NOT NULL AND momento_liturgico != ''
      ORDER BY momento COLLATE NOCASE`
    )
    .all()
    .map(r => r.momento);
}

export function getAllCancionesSlugs() {
  const rows = getDb()
    .prepare(`SELECT id, titulo FROM canciones WHERE titulo IS NOT NULL AND titulo != ''`)
    .all();
  return rows.map(r => ({ id: r.id, slug: slugify(r.titulo) }));
}

export function getComentariosAprobados(limit = 20) {
  return getDb()
    .prepare(
      `SELECT c.*, p.fecha_domingo
      FROM comentarios c
      LEFT JOIN presentaciones p ON c.presentacion_id = p.id
      WHERE c.estado IN ('aprobado', 'corregido')
      ORDER BY c.fecha_creacion DESC
      LIMIT ?`
    )
    .all(limit);
}

export function getCancionesPresentacion(fecha) {
  const presentacion = getPresentacionByFecha(fecha);
  if (!presentacion || !presentacion.canciones_json) return [];
  try {
    const parsed = JSON.parse(presentacion.canciones_json);
    // Puede ser un array [id1, id2, ...] o un objeto {momento: id, ...}
    const ids = Array.isArray(parsed) ? parsed : Object.values(parsed);
    if (!ids.length) return [];
    
    // Eliminar duplicados manteniendo orden
    const uniqueIds = [...new Set(ids)];
    
    const rows = getDb()
      .prepare(
        `SELECT id, titulo, momento_liturgico, tono, html_visual
        FROM canciones
        WHERE id IN (${uniqueIds.map(() => '?').join(',')})`
      )
      .all(...uniqueIds);
    
    // Ordenar según el orden original de ids (SQLite no tiene FIELD())
    const orderMap = new Map(ids.map((id, idx) => [id, idx]));
    rows.sort((a, b) => (orderMap.get(a.id) || 0) - (orderMap.get(b.id) || 0));
    
    return rows;
  } catch {
    return [];
  }
}

export function getLatestPresentacionFecha() {
  const row = getDb()
    .prepare(`SELECT fecha_domingo FROM presentaciones WHERE estado IN ('publicado', 'generado') ORDER BY fecha_domingo DESC LIMIT 1`)
    .get();
  return row ? row.fecha_domingo : null;
}

export function closeDb() {
  if (db) {
    db.close();
    db = null;
  }
}
