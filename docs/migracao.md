# Migração do Drupal

O site antigo rodava em Drupal 7.59, PHP 5.4 e Debian 7, só dentro da unespNET. Não havia módulo de backup, então o conteúdo foi extraído pela própria interface, **somente com leitura**, numa máquina da unespNET:

1. **Espelho público** com `wget` (páginas e arquivos de `/sites/jfb.franca.unesp.br/files/`), uma requisição por vez.
2. **Lista de todos os nós** pelo `/admin/content`, com o login de administrador: `nos.tsv` (nid, título, tipo, autor, status, data, idioma). Eram 3.036 nós, 138 do site e 2.898 do Banco de Dados JFB.
3. **Formulário de edição de cada nó** (`GET /node/<nid>/edit`, sem salvar), guardado como `bruto/<nid>.edit.html.gz`. O formulário traz todos os campos, inclusive o texto em HTML, o endereço (alias), a data, as imagens e os anexos.

Essa extração fica fora do repositório (tem dados do banco e e-mails de usuários). Com ela em mãos, o conteúdo do site é convertido por:

```bash
python3 -I migracao/drupal_para_seed.py --extracao <pasta da extração> --espelho <pasta do espelho>
python3 seed/gerar-seed.py
```

## O que o script faz

| Drupal | EmDash |
|---|---|
| Basic page | Páginas (o alias vira o slug) |
| Notícia | Notícias (campo Autor vira "Autor ou linha fina"; a primeira imagem vira a capa, as demais uma galeria no fim do texto) |
| Verbete | Verbetes |
| Pesquisador | Pesquisadores (na ordem da página antiga de pesquisadores) |
| Exposição | Exposições (imagens em galeria) |
| imagem Slideshow home | Destaques da página inicial |
| Presentation / Présentation | Traduções em inglês e francês da página `apresentacao` |

- O HTML do editor antigo vira Portable Text: parágrafos, títulos, listas, citações, links, negrito e itálico. Imagens viram blocos de imagem, vídeos do YouTube viram blocos de iframe. Tabelas usadas só para dividir a página em colunas (como a das últimas notícias e publicações da Apresentação) viram texto corrido; tabelas de dados viram blocos HTML. Estilos inline (cores, justificação, tamanhos) são descartados.
- Imagens vão para `seed/midia/` (as maiores que 300 KB viram WebP de até 1.600 px) e entram na mídia do EmDash quando o seed é aplicado. Anexos e PDFs linkados vão para `public/arquivos/`, menos os maiores que 20 MB (abaixo).
- Links internos para endereços antigos são trocados pelos novos; os que não têm destino conhecido apontam para `/pt/<caminho antigo>`.
- Ficam de fora: nós não publicados, as páginas internas do Drupal (Home, Logos, Administração, Modelagem, Info), os Painéis (todos não publicados) e o Manual do banco (Página de livro), que documenta o cadastro no sistema antigo.

O resultado de cada execução, com tudo o que ficou de fora, está em [migracao/relatorio.md](../migracao/relatorio.md).

## Curadoria: o que saiu do site

O site JFB fica só com o que é do acervo de jornais franceses no Brasil (decisão de 25/11/2026). O resto do Drupal não entrou, e cada item tem um destino em `migracao/curadoria.json`, listado no relatório:

| Destino | O quê |
|---|---|
| TransfoPress (site do grupo) | Encontros, chamadas e livros da rede Transfopress e o congresso A imprensa francófona das Américas (28 notícias) |
| Repositório Invenio | XIX Semana de História (anais, programação, caderno de resumos, vídeos), cadernos de resumos e o dossiê da revista ArtCultura (6 itens) |
| Fora do escopo | Agenda acadêmica sem relação direta com o acervo e o verbete sobre a revista Floreal (17 itens) |
| Página vazia | Contato, Glossário e Artigos, que só tinham texto provisório (3 páginas) |

Para mudar a seleção, edite `migracao/curadoria.json` e rode a migração de novo. Quando um item ganhar endereço novo (no site do TransfoPress ou no Invenio), acrescente o redirecionamento do endereço antigo em `src/lib/redirecionamentos.json`.

## Arquivos grandes

Os arquivos estáticos do Worker vão até 25 MiB cada. Os anexos maiores que 20 MB (os dois Livros de Registro da Biblioteca Pública de São Paulo, do verbete homônimo) ficam fora do repositório, em `migracao/.cache/grandes/` na máquina da migração, e são servidos do bucket R2 pela rota `src/pages/arquivos/[...caminho].ts`, no mesmo endereço `/arquivos/...`. Depois de criar o bucket, suba cada um com a chave `arquivos/<caminho>`:

```bash
npx wrangler r2 object put jfb-site-media/arquivos/bma_livro_registro_001_0.pdf --file migracao/.cache/grandes/bma_livro_registro_001_0.pdf --content-type application/pdf --remote
npx wrangler r2 object put jfb-site-media/arquivos/bma_livro_registro_002.pdf --file migracao/.cache/grandes/bma_livro_registro_002.pdf --content-type application/pdf --remote
```

Os Livros de Registro são fontes digitalizadas: o lugar definitivo deles é o repositório de dados (InvenioRDM ou Zenodo), junto com o Banco JFB.
