// Idiomas do site e textos fixos da interface. O conteúdo (páginas, notícias,
// verbetes...) é editado no EmDash, um item por idioma; o que ainda não foi
// traduzido aparece em português.

export const IDIOMAS = ['pt', 'en', 'fr'] as const;
export type Idioma = (typeof IDIOMAS)[number];
export const IDIOMA_PADRAO: Idioma = 'pt';

export function ehIdioma(valor: unknown): valor is Idioma {
  return IDIOMAS.includes(valor as Idioma);
}

export const LOCALE: Record<Idioma, { html: string; og: string; nome: string; sigla: string }> = {
  pt: { html: 'pt-BR', og: 'pt_BR', nome: 'Português', sigla: 'PT' },
  en: { html: 'en', og: 'en_US', nome: 'English', sigla: 'EN' },
  fr: { html: 'fr', og: 'fr_FR', nome: 'Français', sigla: 'FR' },
};

const pt = {
  pular: 'Pular para o conteúdo',
  paginaInicial: 'página inicial',
  menuPrincipal: 'Principal',
  idioma: 'Idioma',
  inicio: 'Início',
  apresentacao: 'Apresentação',
  publicacoes: 'Publicações',
  verbetes: 'Verbetes',
  noticias: 'Notícias',
  exposicoes: 'Exposições',
  pesquisadores: 'Pesquisadores',
  bancoDeDados: 'Banco de dados',
  creditos: 'Créditos',
  ultimasNoticias: 'Últimas notícias',
  verTodasNoticias: 'Ver todas as notícias',
  lerMais: 'Ler mais',
  por: 'Por',
  anexos: 'Arquivos',
  imagens: 'Imagens',
  semItens: 'Ainda não há nada publicado aqui.',
  anterior: 'Anteriores',
  proxima: 'Mais recentes',
  paginaDe: (n: number, total: number) => `Página ${n} de ${total}`,
  naoEncontrada: 'Página não encontrada',
  naoEncontradaTexto: 'O endereço pode ter mudado com a nova versão do site. Comece pela página inicial.',
  voltarInicio: 'Voltar ao início',
  areaRestrita: 'Área restrita',
  apoio: 'Apoio',
  nomeCompleto: 'Jornais Franceses no Brasil',
  descricaoSite:
    'Jornais Franceses no Brasil: projeto de pesquisa sobre a circulação de periódicos franceses no Brasil e as transferências culturais na imprensa, séculos XIX e XX.',
};

export type Textos = typeof pt;

const en: Textos = {
  pular: 'Skip to content',
  paginaInicial: 'home page',
  menuPrincipal: 'Main',
  idioma: 'Language',
  inicio: 'Home',
  apresentacao: 'About',
  publicacoes: 'Publications',
  verbetes: 'Entries',
  noticias: 'News',
  exposicoes: 'Exhibitions',
  pesquisadores: 'Researchers',
  bancoDeDados: 'Database',
  creditos: 'Credits',
  ultimasNoticias: 'Latest news',
  verTodasNoticias: 'See all news',
  lerMais: 'Read more',
  por: 'By',
  anexos: 'Files',
  imagens: 'Images',
  semItens: 'Nothing has been published here yet.',
  anterior: 'Older',
  proxima: 'Newer',
  paginaDe: (n, total) => `Page ${n} of ${total}`,
  naoEncontrada: 'Page not found',
  naoEncontradaTexto: 'The address may have changed with the new version of the site. Start from the home page.',
  voltarInicio: 'Back to home',
  areaRestrita: 'Restricted area',
  apoio: 'Support',
  nomeCompleto: 'French Newspapers in Brazil',
  descricaoSite:
    'French Newspapers in Brazil: a research project on the circulation of French periodicals in Brazil and cultural transfers in the press, 19th and 20th centuries.',
};

const fr: Textos = {
  pular: 'Aller au contenu',
  paginaInicial: "page d'accueil",
  menuPrincipal: 'Principal',
  idioma: 'Langue',
  inicio: 'Accueil',
  apresentacao: 'Présentation',
  publicacoes: 'Publications',
  verbetes: 'Notices',
  noticias: 'Actualités',
  exposicoes: 'Expositions',
  pesquisadores: 'Chercheurs',
  bancoDeDados: 'Base de données',
  creditos: 'Crédits',
  ultimasNoticias: 'Dernières actualités',
  verTodasNoticias: 'Toutes les actualités',
  lerMais: 'Lire la suite',
  por: 'Par',
  anexos: 'Fichiers',
  imagens: 'Images',
  semItens: "Rien n'a encore été publié ici.",
  anterior: 'Plus anciennes',
  proxima: 'Plus récentes',
  paginaDe: (n, total) => `Page ${n} sur ${total}`,
  naoEncontrada: 'Page introuvable',
  naoEncontradaTexto: "L'adresse a peut-être changé avec la nouvelle version du site. Commencez par la page d'accueil.",
  voltarInicio: "Retour à l'accueil",
  areaRestrita: 'Accès réservé',
  apoio: 'Soutien',
  nomeCompleto: 'Journaux français au Brésil',
  descricaoSite:
    'Journaux français au Brésil : projet de recherche sur la circulation des périodiques français au Brésil et les transferts culturels dans la presse, XIXe et XXe siècles.',
};

const TEXTOS: Record<Idioma, Textos> = { pt, en, fr };

export function textos(lang: Idioma): Textos {
  return TEXTOS[lang];
}

// "19 de novembro de 2026", "November 19, 2026", "19 novembre 2026".
export function formatarData(iso: string | Date | null | undefined, lang: Idioma): string {
  if (!iso) return '';
  const texto = iso instanceof Date ? iso.toISOString() : String(iso);
  const [a, m, d] = texto.slice(0, 10).split('-').map(Number);
  if (!a || !m) return '';
  const data = new Date(Date.UTC(a, m - 1, d || 1));
  const opcoes: Intl.DateTimeFormatOptions = d
    ? { day: 'numeric', month: 'long', year: 'numeric', timeZone: 'UTC' }
    : { month: 'long', year: 'numeric', timeZone: 'UTC' };
  return new Intl.DateTimeFormat(LOCALE[lang].html, opcoes).format(data);
}
