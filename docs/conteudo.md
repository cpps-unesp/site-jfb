# Conteúdo: o que fica onde

Tudo é editado no admin do EmDash, em `https://jfb.franca.unesp.br/_emdash/admin`. Um rascunho não aparece no site; só o que está **publicado**.

## Coleções

| Coleção | Para quê | Onde aparece |
|---|---|---|
| **Páginas** | Textos fixos: `apresentacao`, `publicacoes`, `banco-de-dados`, `creditos` e as demais. O slug vira o endereço | `/pt/<slug>`. A `apresentacao` aparece também na página inicial |
| **Notícias** | Notícias e eventos, com data, autor ou linha fina, imagem e texto | `/pt/noticias` (15 por página) e na página inicial (as 5 mais recentes) |
| **Verbetes** | Verbetes e textos de referência | `/pt/verbetes` |
| **Pesquisadores** | Equipe: nome, foto, ordem e apresentação | `/pt/pesquisadores` |
| **Exposições** | Exposições virtuais, com texto e galeria | `/pt/exposicoes` |
| **Destaques da página inicial** | Imagens no topo da página inicial, com link opcional | Página inicial |
| **Aparência** (item `site`) | Nome do site, descrição curta, e-mail e endereço de contato | Cabeçalho, rodapé e buscadores |

O menu lateral é o menu **principal** (Menus, no admin), um por idioma.

Não use como slug de página `noticias`, `verbetes`, `pesquisadores` nem `exposicoes`: esses endereços são as listas.

## Imagens e arquivos

Imagens entram pela biblioteca de mídia do admin. Para um PDF dentro de um texto, envie-o em Mídia e cole o link. Os PDFs que vieram do site antigo ficam em `/arquivos/...`, servidos pelo próprio site, e continuam valendo.

## Traduções (pt, en, fr)

O português é o idioma principal: `/pt/`, `/en/` e `/fr/` mostram a versão de cada idioma e, quando falta tradução, o português. Para traduzir um item, abra-o no admin e crie a versão em inglês ou francês pelo seletor de idioma do editor. No site antigo só a Apresentação tinha versões em inglês e francês, e elas vieram como traduções da página `apresentacao`. Os textos fixos da interface (menu padrão, rótulos, rodapé) estão em `src/lib/i18n.ts`.

## Pelo assistente de IA (MCP)

O EmDash tem um servidor MCP em `https://jfb.franca.unesp.br/_emdash/api/mcp`, configurado no `.mcp.json` deste repositório. Peça ao assistente para criar como rascunho e confira no admin antes de publicar. Mais detalhes no guia `docs/mcp-e-skills.md` do repositório do site do CPPS, que vale igual aqui.
