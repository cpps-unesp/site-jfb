import { defineMiddleware } from 'astro:middleware';
import { IDIOMAS } from './lib/i18n';
import antigos from './lib/redirecionamentos.json';

// Endereços do site antigo em Drupal (jfb.franca.unesp.br/noticias/..., /node/123,
// /publicacoes/verbetes) vão para o endereço novo; a lista é gerada na migração
// (migracao/drupal_para_seed.py). Qualquer outro caminho sem idioma vai para a
// versão em português. O admin do EmDash (/_emdash), o OAuth do MCP
// (/.well-known) e os arquivos de public/ (/static, /arquivos) ficam como estão.
const SEM_IDIOMA = /^\/(?!_|\.well-known|static\/|arquivos\/|robots\.txt|favicon|sitemap)/;
const MAPA = antigos as Record<string, string>;

export const onRequest = defineMiddleware((context, next) => {
  const { pathname, search } = context.url;
  const primeiro = pathname.split('/')[1] ?? '';
  if (pathname === '/') return context.redirect(`/pt/${search}`, 302);
  const semBarra = pathname.replace(/\/+$/, '').replace(/^\//, '');
  const destino = MAPA[decodeURIComponent(semBarra)];
  if (destino) return context.redirect(destino, 301);
  if (!IDIOMAS.includes(primeiro as never) && SEM_IDIOMA.test(pathname)) {
    if (pathname === '/admin' || pathname.startsWith('/admin/') || pathname === '/user' || pathname.startsWith('/user/')) {
      return context.redirect('/_emdash/admin', 301);
    }
    return context.redirect(`/pt${pathname}${search}`, 301);
  }
  return next();
});
