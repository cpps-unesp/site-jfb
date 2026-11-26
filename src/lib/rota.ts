import { textos, type Idioma, type Textos } from './i18n';
import type { Colecao } from './conteudo';

// Coleções que têm página de lista (/pt/noticias) e de item (/pt/noticias/<slug>).
export const LISTAS = ['noticias', 'verbetes', 'pesquisadores', 'exposicoes'] as const;
export type Lista = (typeof LISTAS)[number] & Colecao;

export function ehLista(v: unknown): v is Lista {
  return LISTAS.includes(v as Lista);
}

export function tituloLista(lista: Lista, lang: Idioma): string {
  const t: Textos = textos(lang);
  return { noticias: t.noticias, verbetes: t.verbetes, pesquisadores: t.pesquisadores, exposicoes: t.exposicoes }[lista];
}

// Notícias por página na lista.
export const POR_PAGINA = 15;
