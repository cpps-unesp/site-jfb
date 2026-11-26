# Site Jornais Franceses no Brasil

Site do projeto **Jornais Franceses no Brasil** (JFB), coordenado por Valéria Guimarães (Unesp, FCHS Franca), sobre a circulação de periódicos franceses no Brasil e as transferências culturais na imprensa, séculos XIX e XX. Endereço: https://jfb.franca.unesp.br.

É a versão em [EmDash](https://emdashcms.com) do site que estava em Drupal 7 (PHP 5.4), acessível só pela unespNET. A base técnica é a mesma dos sites do CPPS ([cpps-unesp/site-cpps](https://github.com/cpps-unesp/site-cpps)) e do FoMerco: Astro no Cloudflare Workers, banco D1 e mídia no R2. O visual retoma o do site antigo (fundo preto, pinceladas vinho e verde-azulado, Josefin Sans), com mais contraste.

Este repositório cobre o **site institucional**: apresentação, publicações, verbetes, notícias, exposições, pesquisadores e créditos. O **Banco de Dados JFB** (fontes, suportes, entidades, acervos, mediadores, produtores, títulos e cadastros de pesquisa) tem migração própria.

## Para quem edita o conteúdo

Tudo é editado em `/_emdash/admin` (link "Área restrita" no rodapé), com login por passkey. O que fica onde e como traduzir: [docs/conteudo.md](docs/conteudo.md).

## Para quem mexe no código

Precisa de Node 22.23 ou mais novo (ou o LTS do `.nvmrc`).

```bash
npm install
npm run dev        # http://localhost:4321 (o admin local tem um atalho sem passkey, mostrado no terminal)
npm run ci         # valida o seed, checa os tipos e faz o build
```

No primeiro `npm run dev` o banco local é criado com os modelos de `seed/seed.json`. Para ter também o conteúdo migrado, conclua a configuração em `/_emdash/admin` marcando **Sample content**; as imagens são baixadas deste repositório pelo jsDelivr.

| Onde | O quê |
|---|---|
| `src/pages/[lang]/` | Início, páginas de texto (`[slug]`), listas e itens das coleções (`[colecao]/[slug]`) |
| `src/lib/conteudo.ts` | Leitura e validação do conteúdo do EmDash |
| `src/lib/i18n.ts` | Idiomas e textos fixos da interface (pt, en, fr) |
| `src/lib/redirecionamentos.json` | Endereços do site antigo e para onde vão (gerado na migração) |
| `src/middleware.ts` | Redirecionamentos e prefixo de idioma |
| `src/layouts/Base.astro` | Coluna lateral com menu, seletor de idioma e rodapé |
| `public/static/` | CSS, fonte Josefin Sans, pinceladas e logos do site antigo |
| `public/arquivos/` | PDFs e anexos do site antigo, servidos nos mesmos links das páginas migradas |
| `seed/gerar-seed.py` → `seed/seed.json` | Modelos de conteúdo e conteúdo inicial. Edite o script e rode `python3 seed/gerar-seed.py` |
| `seed/drupal.json`, `seed/midia/` | Conteúdo e imagens migrados do Drupal |
| `migracao/` | Script da migração e relatório do que entrou e do que ficou de fora ([docs/migracao.md](docs/migracao.md)) |
| `wrangler.jsonc` | Worker, banco, bucket e cron |

Deploy, domínio e atualização do EmDash: [docs/deploy.md](docs/deploy.md).
