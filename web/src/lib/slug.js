// Helper único para generar slugs de canciones.
// Debe coincidir con la lógica usada en db.js para getCancionBySlug / getAllCancionesSlugs.
export function slugify(text) {
  if (!text) return '';
  return text
    .toLowerCase()
    .trim()
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .replace(/[^a-z0-9\s-]/g, '')
    .replace(/\s+/g, '-')
    .replace(/-+/g, '-')
    .replace(/^-+|-+$/g, '');
}
