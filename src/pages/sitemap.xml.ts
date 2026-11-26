import type { APIRoute } from 'astro';
import { IDIOMAS } from '../lib/i18n';
import { listarItens } from '../lib/conteudo';
import { LISTAS } from '../lib/rota';

// Mapa do site para buscadores: início, páginas, listas e itens, nos três idiomas.
export const GET: APIRoute = async ({ site }) => {
  const caminhos = new Set<string>();
  for (const lang of IDIOMAS) {
    caminhos.add(`/${lang}/`);
    for (const p of await listarItens('paginas', lang)) caminhos.add(`/${lang}/${p.slug}`);
    for (const lista of LISTAS) {
      caminhos.add(`/${lang}/${lista}`);
      for (const item of await listarItens(lista, lang)) caminhos.add(`/${lang}/${lista}/${item.slug}`);
    }
  }
  const urls = [...caminhos].map((c) => `<url><loc>${new URL(c, site).toString()}</loc></url>`).join('');
  return new Response(
    `<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">${urls}</urlset>`,
    { headers: { 'Content-Type': 'application/xml; charset=utf-8' } }
  );
};
