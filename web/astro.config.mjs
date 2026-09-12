import { defineConfig } from 'astro/config';
import react from '@astrojs/react';
import tailwind from '@astrojs/tailwind';
import sitemap from '@astrojs/sitemap';
import { getAllCancionesSlugs, getAllPresentacionesFechas } from './src/lib/db.js';

const basePath = process.env.BASE_PATH || '/';
const siteUrl = process.env.SITE_URL || undefined;

function buildSitemapEntries() {
  if (!siteUrl) return [];
  const base = basePath.endsWith('/') ? basePath : `${basePath}/`;
  const entries = [];

  for (const { slug } of getAllCancionesSlugs()) {
    entries.push(`${siteUrl}${base}cancionero/${encodeURI(slug)}/`);
  }

  for (const fecha of getAllPresentacionesFechas()) {
    entries.push(`${siteUrl}${base}presentacion/${fecha}/`);
    entries.push(`${siteUrl}${base}lecturas/${fecha}/`);
    entries.push(`${siteUrl}${base}musicos/${fecha}/`);
  }

  return entries;
}

export default defineConfig({
  output: 'static',
  site: siteUrl,
  base: basePath,
  integrations: [
    react(),
    tailwind({
      applyBaseStyles: false,
    }),
    sitemap({
      customPages: buildSitemapEntries(),
    }),
  ],
  vite: {
    ssr: {
      external: ['better-sqlite3'],
    },
  },
});
