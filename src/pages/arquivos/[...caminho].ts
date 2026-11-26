import type { APIRoute } from 'astro';
import { env } from 'cloudflare:workers';

// Arquivos do site antigo grandes demais para os arquivos estáticos do Worker
// (limite de 25 MiB por arquivo): ficam no bucket R2 do site, com a chave
// arquivos/<caminho>. Os demais saem direto de public/arquivos/ e nem chegam aqui.
// Como subir: docs/migracao.md.
const TIPOS: Record<string, string> = {
  pdf: 'application/pdf',
  doc: 'application/msword',
  docx: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
};

export const GET: APIRoute = async ({ params }) => {
  const caminho = params.caminho ?? '';
  if (!caminho || caminho.includes('..')) return new Response(null, { status: 404 });
  const bucket = (env as unknown as { MEDIA?: R2Bucket }).MEDIA;
  const objeto = await bucket?.get(`arquivos/${caminho}`);
  if (!objeto) return new Response(null, { status: 404 });
  const extensao = caminho.split('.').pop()?.toLowerCase() ?? '';
  return new Response(objeto.body, {
    headers: {
      'Content-Type': objeto.httpMetadata?.contentType || TIPOS[extensao] || 'application/octet-stream',
      'Content-Length': String(objeto.size),
      'Cache-Control': 'public, max-age=86400',
    },
  });
};
