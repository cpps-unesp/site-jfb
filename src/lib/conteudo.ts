import { getEmDashCollection, getEmDashEntry, getMenu } from 'emdash';
import type { EditProxy, ImageValue, PortableTextBlock } from 'emdash';
import { IDIOMA_PADRAO, textos, type Idioma } from './i18n';

// Conteúdo editável no EmDash (/_emdash/admin). Os modelos estão em
// seed/seed.json (gerado por seed/gerar-seed.py). Cada função devolve objetos
// simples e já validados para os componentes; um campo vazio ou inválido vira o
// valor padrão, para o site nunca quebrar por causa do que foi digitado no admin.

type Dados = Record<string, unknown>;
type Entrada = { id: string; data: Dados; edit: EditProxy };

const str = (v: unknown, padrao = ''): string => (typeof v === 'string' ? v.trim() : padrao);
const num = (v: unknown): number | null =>
  typeof v === 'number' && Number.isFinite(v)
    ? v
    : typeof v === 'string' && v.trim() && Number.isFinite(Number(v))
      ? Number(v)
      : null;
const blocos = (v: unknown): PortableTextBlock[] => (Array.isArray(v) ? (v as PortableTextBlock[]) : []);

function temImagem(valor: unknown): valor is ImageValue {
  return !!valor && typeof valor === 'object' && !!((valor as ImageValue).id || (valor as ImageValue).src);
}

function grupo(entrada: Entrada): string {
  return str(entrada.data.translationGroup) || str(entrada.data.id) || entrada.id;
}

// Só ganha anotação de edição o que está no idioma da página: um item mostrado
// em pt numa página en/fr (falta tradução) fica sem, para ninguém sobrescrever o
// português a partir dela.
function edicao(entrada: Entrada | null | undefined, lang: Idioma): EditProxy | undefined {
  return entrada && str(entrada.data.locale, lang) === lang ? entrada.edit : undefined;
}

// Links digitados no admin: só do próprio site, https ou mailto.
export function urlSegura(url: unknown): string {
  const u = str(url);
  return /^(\/(?!\/)|https:\/\/|mailto:|#)/i.test(u) ? u : '';
}

export function ehExterno(url: string): boolean {
  return /^https?:/i.test(url);
}

// Lista a coleção no idioma pedido; o que ainda não foi traduzido aparece em pt.
async function listar(colecao: string, lang: Idioma, orderBy: Record<string, 'asc' | 'desc'>): Promise<Entrada[]> {
  const filtro = { locale: IDIOMA_PADRAO, orderBy, limit: 1000 };
  const padrao = await getEmDashCollection<string, Dados>(colecao, filtro as never);
  if (padrao.error) throw padrao.error;
  const base = padrao.entries as unknown as Entrada[];
  if (lang === IDIOMA_PADRAO) return base;

  const traduzidas = await getEmDashCollection<string, Dados>(colecao, { ...filtro, locale: lang } as never);
  if (traduzidas.error) throw traduzidas.error;
  const porGrupo = new Map((traduzidas.entries as unknown as Entrada[]).map((e) => [grupo(e), e]));
  return base.map((e) => porGrupo.get(grupo(e)) ?? e);
}

// getEmDashEntry já cai para pt quando falta a tradução.
async function buscar(colecao: string, slug: string, lang: Idioma): Promise<Entrada | null> {
  const { entry, error } = await getEmDashEntry<string, Dados>(colecao, slug, { locale: lang } as never);
  if (error) throw error;
  return (entry as unknown as Entrada | null) ?? null;
}

// ---------- Aparência ----------

export type Aparencia = {
  nome: string;
  chamada: string;
  email: string;
  endereco: string;
  edit?: EditProxy;
};

export async function getAparencia(lang: Idioma): Promise<Aparencia> {
  const t = textos(lang);
  const padrao: Aparencia = { nome: t.nomeCompleto, chamada: t.descricaoSite, email: '', endereco: '' };
  let e: Entrada | null = null;
  try {
    e = await buscar('aparencia', 'site', lang);
  } catch {
    // Coleção ainda não criada neste banco: fica o padrão.
  }
  if (!e) return padrao;
  const d = e.data;
  return {
    nome: str(d.title) || padrao.nome,
    chamada: str(d.chamada) || padrao.chamada,
    email: /^[^\s@<>"]+@[^\s@<>"]+$/.test(str(d.contato_email)) ? str(d.contato_email) : '',
    endereco: str(d.contato_endereco),
    edit: edicao(e, lang),
  };
}

// ---------- Menu ----------

export type ItemMenu = { rotulo: string; url: string; externo: boolean };

export function menuPadrao(lang: Idioma): ItemMenu[] {
  const t = textos(lang);
  const itens: [string, string][] = [
    [t.apresentacao, 'apresentacao'],
    [t.publicacoes, 'publicacoes'],
    [t.verbetes, 'verbetes'],
    [t.noticias, 'noticias'],
    [t.exposicoes, 'exposicoes'],
    [t.pesquisadores, 'pesquisadores'],
    [t.bancoDeDados, 'banco-de-dados'],
    [t.creditos, 'creditos'],
  ];
  return itens.map(([rotulo, caminho]) => ({ rotulo, url: `/${lang}/${caminho}`, externo: false }));
}

export async function getMenuPrincipal(lang: Idioma): Promise<ItemMenu[]> {
  try {
    const menu = await getMenu('principal', { locale: lang });
    if (menu && menu.items.length > 0) {
      return menu.items
        .map((item) => {
          const url = urlSegura(item.url);
          return { rotulo: item.label, url, externo: ehExterno(url) };
        })
        .filter((item) => item.url);
    }
  } catch {
    // Sem o menu no banco: fica o padrão.
  }
  return menuPadrao(lang);
}

// ---------- Itens (páginas, notícias, verbetes, pesquisadores, exposições) ----------

export const COLECOES = ['paginas', 'noticias', 'verbetes', 'pesquisadores', 'exposicoes'] as const;
export type Colecao = (typeof COLECOES)[number];

export type Item = {
  slug: string;
  titulo: string;
  subtitulo: string;
  autor: string;
  data: string;
  resumo: string;
  imagem: ImageValue | null;
  conteudo: PortableTextBlock[];
  ordem: number;
  edit?: EditProxy;
};

function montar(e: Entrada, lang: Idioma): Item {
  const d = e.data;
  return {
    slug: str(d.slug) || e.id,
    titulo: str(d.title),
    subtitulo: str(d.subtitulo),
    autor: str(d.autor),
    data: str(d.data),
    resumo: str(d.resumo),
    imagem: temImagem(d.imagem) ? d.imagem : temImagem(d.foto) ? d.foto : null,
    conteudo: blocos(d.conteudo),
    ordem: num(d.ordem) ?? 0,
    edit: edicao(e, lang),
  };
}

const ORDEM: Record<Colecao, Record<string, 'asc' | 'desc'>> = {
  paginas: { title: 'asc' },
  noticias: { data: 'desc' },
  verbetes: { data: 'desc' },
  pesquisadores: { ordem: 'asc' },
  exposicoes: { data: 'desc' },
};

export async function listarItens(colecao: Colecao, lang: Idioma): Promise<Item[]> {
  const itens = (await listar(colecao, lang, ORDEM[colecao])).map((e) => montar(e, lang));
  // Pesquisadores: pela ordem e, no empate, pelo nome.
  if (colecao === 'pesquisadores') {
    itens.sort((a, b) => a.ordem - b.ordem || a.titulo.localeCompare(b.titulo, 'pt-BR'));
  }
  return itens;
}

export async function getItem(colecao: Colecao, slug: string, lang: Idioma): Promise<Item | null> {
  const e = await buscar(colecao, slug, lang);
  return e ? montar(e, lang) : null;
}

// ---------- Destaques da página inicial ----------

export type Destaque = { titulo: string; imagem: ImageValue; link: string; edit?: EditProxy };

export async function getDestaques(lang: Idioma): Promise<Destaque[]> {
  try {
    const itens = await listar('destaques', lang, { ordem: 'asc' });
    return itens.flatMap((e) =>
      temImagem(e.data.imagem)
        ? [{ titulo: str(e.data.title), imagem: e.data.imagem, link: urlSegura(e.data.link), edit: edicao(e, lang) }]
        : []
    );
  } catch {
    return [];
  }
}

// Primeiro parágrafo de texto, para resumos e meta description.
export function resumoDe(item: Item, max = 220): string {
  if (item.resumo) return item.resumo;
  for (const b of item.conteudo) {
    const filhos = (b as { children?: { text?: string }[] }).children;
    if (b._type !== 'block' || !Array.isArray(filhos)) continue;
    const texto = filhos.map((c) => c.text ?? '').join('').replace(/\s+/g, ' ').trim();
    if (texto.length > 20) return texto.length > max ? `${texto.slice(0, max).replace(/\s\S*$/, '')}…` : texto;
  }
  return '';
}
