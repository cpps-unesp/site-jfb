# Deploy

O site roda inteiro na Cloudflare, como um **Worker**, com a mesma arquitetura do site do CPPS (ver `docs/deploy-e-redirects.md` no repositório `cpps-unesp/site-cpps`).

| Recurso | Nome | Binding | Para quê |
|---|---|---|---|
| Worker | `jfb-site` | — | Páginas, admin (`/_emdash/admin`) e MCP |
| Banco D1 | `jfb-site` (região ENAM) | `DB` | Conteúdo, usuários e traduções |
| Bucket R2 | `jfb-site-media` | `MEDIA` | Imagens e arquivos enviados pelo admin |
| KV (criado pelo adapter) | — | `SESSION` | Sessões do admin |
| Images (criado pelo adapter) | — | `IMAGES` | Redimensiona as imagens |
| Cron (a cada minuto) | — | — | Publicação agendada e manutenção do EmDash |
| Arquivos estáticos | — | `ASSETS` | CSS, fonte, logos e os PDFs de `public/arquivos/` |

## Antes de começar: conta da Cloudflare

Os limites do plano gratuito são por conta: 5 crons, 10 bancos D1, 10 ms de CPU por requisição. A conta do CPPS já tem o site do CPPS e o ambiente de teste dele, e há outros sites de grupos a caminho (TransfoPress, FoMerco). Decida em qual conta o JFB fica e se vale o Workers Paid (US$ 5/mês por conta).

## Primeira publicação

Num terminal com o repositório, logado na conta escolhida (`npx wrangler login`):

1. Crie o banco e copie o `database_id` para o `wrangler.jsonc`, com commit (não é segredo):
   ```bash
   npx wrangler d1 create jfb-site --location enam
   ```
2. Confira se `seed/seed.json` aponta para uma versão do repositório que já está no GitHub: as imagens do conteúdo migrado são baixadas de lá pelo jsDelivr. Para fixar num commit, troque `REF_PADRAO` em `seed/gerar-seed.py` pelo SHA, rode `python3 seed/gerar-seed.py` e faça commit dos dois.
3. Faça o build e publique **trancado**, com um endereço que o navegador recusa, para ninguém criar o administrador antes de você. Na primeira vez, o Wrangler cria o bucket e o KV.
   ```bash
   npm run build
   npx wrangler deploy --var EMDASH_SITE_URL:https://jfb-site.invalid
   ```
4. Abra uma página do endereço workers.dev e espere: o primeiro acesso aplica as migrações do banco.
5. Destranque com `npx wrangler deploy` (sem o `--var`) e conclua logo a configuração em `https://jfb-site.<subdomínio>.workers.dev/_emdash/admin`: título, **Sample content** (importa páginas, notícias, verbetes, pesquisadores, exposição, destaques, aparência e menu de `seed/seed.json`), conta e passkey. Use uma passkey **sincronizada** (gerenciador de senhas do Google ou da Apple), não uma presa a um aparelho.
6. Confira se nenhuma imagem ficou para trás: se um download falha, o EmDash grava o campo vazio sem avisar. Compare a Mídia do admin com o número de arquivos em `seed/midia/` e veja os destaques sem imagem (eles não aparecem no site):
   ```bash
   find seed/midia -type f | wc -l
   npx wrangler d1 execute jfb-site --remote --command "SELECT slug FROM ec_destaques WHERE imagem IS NULL OR imagem = ''"
   ```
7. Gere a chave de criptografia, guarde uma cópia num cofre de senhas e cadastre:
   ```bash
   npx emdash secrets generate
   npx wrangler secret put EMDASH_ENCRYPTION_KEY
   ```
8. Convide pelo menos mais um administrador (Usuários → Convidar). No plano gratuito o site não manda e-mail: copie o link do convite e envie à pessoa.

## Domínio jfb.franca.unesp.br

O domínio é da Unesp, e hoje aponta para o servidor Drupal dentro da unespNET. A troca depende da TI de Franca:

- **Custom hostname (Cloudflare for SaaS)**, como o CPPS faz com `cppsunesp.org`: a TI cria um CNAME de `jfb.franca.unesp.br` para o endereço indicado pela Cloudflare e um registro TXT de validação.
- Depois, no admin: Settings → General → **Change domain** → `jfb.franca.unesp.br`. Cada pessoa, ainda logada no workers.dev, usa **Continue on jfb.franca.unesp.br** e cria uma passkey no domínio. Quando todos entrarem pelo domínio, acrescente `"workers_dev": false` ao `wrangler.jsonc`.

Os caminhos do site antigo (`/apresentacao`, `/noticias/<nome>`, `/node/<número>`, `/publicacoes/verbetes`) já são redirecionados no site novo, pela lista em `src/lib/redirecionamentos.json`.

## Deploys seguintes (Workers Builds)

No painel: Workers & Pages → `jfb-site` → Settings → Builds → conectar `cpps-unesp/site-jfb`:

- **Build command:** `npm run build`
- **Deploy command:** `npx wrangler deploy`
- **Production branch:** `main`
- **Builds de outras branches: desligados.** Um preview usaria o mesmo banco da produção.
- Enquanto o site estiver só no workers.dev, defina a variável de build `EMDASH_SITE_URL` com esse endereço, para as imagens serem otimizadas.

Deploys não mexem no conteúdo. Mudar `seed/seed.json` não altera um banco que já existe: um campo ou coleção nova no site no ar é criado pelo admin (Content types) ou pelo MCP, e levado também para o `seed/gerar-seed.py`, como no guia [Evolving a Deployed Site](https://docs.emdashcms.com/deployment/schema-evolution/).

## Atualizar o EmDash

Numa branch, rode `npx upgrade-emdash@latest` e leia o `.emdash/UPGRADE.md` que ele gera. As migrações do banco rodam sozinhas no primeiro acesso e só andam para frente: antes, anote o ponto de restauração (`npx wrangler d1 time-travel info jfb-site`).
