#!/usr/bin/env python3
"""Gera seed/seed.json: os modelos de conteúdo do EmDash e o conteúdo inicial.

O conteúdo inicial vem do site antigo em Drupal: seed/drupal.json, gerado uma vez
por migracao/drupal_para_seed.py a partir da extração (ver docs/migracao.md). As
imagens ficam em seed/midia/ e entram no banco pelo jsDelivr, como no site do
CPPS; por isso o seed aponta para uma versão publicada do repositório (REF).

O seed só vale para banco novo (primeira subida ou `npx emdash seed`). Depois
disso, o conteúdo é editado no admin (/_emdash/admin). Para mudar um modelo num
banco que já existe, use o admin (Content types) ou o MCP; ver docs/conteudo.md.

Uso: python3 seed/gerar-seed.py [ref]   (ref padrão: REF_PADRAO, abaixo)
"""
import json
import sys
from pathlib import Path
from urllib.parse import quote

AQUI = Path(__file__).parent
REPO = "cpps-unesp/site-jfb"
# Versão do repositório de onde o jsDelivr serve seed/midia/. Para fixar num
# commit, troque pelo SHA e rode o script (o CI confere que o seed bate com ele).
REF_PADRAO = "main"
REF = sys.argv[1] if len(sys.argv) > 1 else REF_PADRAO
IDIOMAS = ["pt", "en", "fr"]


def campo(slug, label, tipo, **extra):
    f = {"slug": slug, "label": label, "type": tipo}
    f.update(extra)
    return f


FIXO = {"translatable": False}


def colecao(slug, label, singular, descricao, icone, ordem, campos, **extra):
    c = {
        "slug": slug,
        "label": label,
        "labelSingular": singular,
        "description": descricao,
        "icon": icone,
        "group": "Conteúdo",
        "sortOrder": ordem,
        "supports": ["drafts", "revisions", "preview", "search"],
        "titleField": "title",
        "fields": campos,
    }
    c.update(extra)
    return c


colecoes = [
    colecao(
        "paginas", "Páginas", "Página",
        "Textos fixos do site. O slug vira o endereço (/pt/<slug>): apresentacao, publicacoes, banco-de-dados, creditos... "
        "A página apresentacao também aparece na página inicial. Não use os slugs noticias, verbetes, pesquisadores e exposicoes.",
        "file-text", 1,
        [
            campo("title", "Título", "string", required=True, searchable=True),
            campo("resumo", "Resumo (para buscadores e redes; vazio: o primeiro parágrafo)", "text"),
            campo("imagem", "Imagem de abertura", "image", **FIXO),
            campo("conteudo", "Texto", "portableText", searchable=True),
        ],
        urlPattern="/pt/{slug}",
    ),
    colecao(
        "noticias", "Notícias", "Notícia",
        "Notícias e eventos do projeto, da mais recente para a mais antiga. A imagem aparece no topo da notícia.",
        "newspaper", 2,
        [
            campo("title", "Título", "string", required=True, searchable=True),
            campo("data", "Data", "datetime", required=True, indexed=True, **FIXO),
            campo("autor", "Autor ou linha fina", "string", searchable=True),
            campo("resumo", "Resumo (vazio: o primeiro parágrafo)", "text"),
            campo("imagem", "Imagem", "image", **FIXO),
            campo("conteudo", "Texto", "portableText", searchable=True),
        ],
        dateField="data",
        urlPattern="/pt/noticias/{slug}",
        admin={"listColumns": ["data"]},
    ),
    colecao(
        "verbetes", "Verbetes", "Verbete",
        "Verbetes e textos de referência sobre periódicos, editores e fontes.",
        "book-open", 3,
        [
            campo("title", "Título", "string", required=True, searchable=True),
            campo("subtitulo", "Subtítulo", "string", searchable=True),
            campo("autor", "Autor", "string", searchable=True),
            campo("data", "Data", "datetime", indexed=True, **FIXO),
            campo("resumo", "Resumo (vazio: o primeiro parágrafo)", "text"),
            campo("conteudo", "Texto", "portableText", searchable=True),
        ],
        dateField="data",
        urlPattern="/pt/verbetes/{slug}",
        admin={"listColumns": ["autor", "data"]},
    ),
    colecao(
        "pesquisadores", "Pesquisadores", "Pesquisador",
        "Equipe do projeto. A lista segue o campo Ordem e, no empate, o nome.",
        "users", 4,
        [
            campo("title", "Nome", "string", required=True, searchable=True),
            campo("foto", "Foto", "image", **FIXO),
            campo("ordem", "Ordem na lista", "integer", **FIXO),
            campo("conteudo", "Apresentação", "portableText", searchable=True),
        ],
        urlPattern="/pt/pesquisadores/{slug}",
        admin={"listColumns": ["ordem"]},
    ),
    colecao(
        "exposicoes", "Exposições", "Exposição",
        "Exposições virtuais: um texto com galeria de imagens.",
        "image", 5,
        [
            campo("title", "Título", "string", required=True, searchable=True),
            campo("data", "Data", "datetime", indexed=True, **FIXO),
            campo("resumo", "Resumo (vazio: o primeiro parágrafo)", "text"),
            campo("imagem", "Imagem de capa", "image", **FIXO),
            campo("conteudo", "Texto e galeria", "portableText", searchable=True),
        ],
        dateField="data",
        urlPattern="/pt/exposicoes/{slug}",
    ),
    colecao(
        "destaques", "Destaques da página inicial", "Destaque",
        "Imagens no topo da página inicial, na ordem do campo Ordem.",
        "star", 6,
        [
            campo("title", "Título (texto alternativo da imagem)", "string", required=True),
            campo("imagem", "Imagem (sem imagem, o destaque não aparece)", "image", **FIXO),
            campo("link", "Link (opcional)", "string", **FIXO),
            campo("ordem", "Ordem", "integer", **FIXO),
        ],
        group="Configurações",
    ),
    colecao(
        "aparencia", "Aparência", "Aparência",
        "Nome do site, chamada e contato: um único item, \"site\".",
        "palette", 7,
        [
            campo("title", "Nome do site", "string", required=True),
            campo("chamada", "Descrição curta (buscadores e redes)", "text"),
            campo("contato_email", "E-mail de contato", "string", **FIXO),
            campo("contato_endereco", "Endereço", "text"),
        ],
        group="Configurações",
        supports=["drafts", "revisions"],
    ),
]


# ---------- conteúdo inicial ----------

def midia_url(caminho):
    return f"https://cdn.jsdelivr.net/gh/{REPO}@{REF}/seed/{quote(caminho)}"


def resolver_midia(valor):
    """Troca {"$midia": "midia/..."} por {"$media": {"url": jsDelivr, ...}}."""
    if isinstance(valor, list):
        return [resolver_midia(v) for v in valor]
    if isinstance(valor, dict):
        if "$midia" in valor:
            # REF "local": lê os arquivos de seed/midia/ (só no `npm run dev`,
            # para testar sem publicar o repositório). Não faça commit assim.
            origem = {"file": valor["$midia"]} if REF == "local" else {"url": midia_url(valor["$midia"])}
            m = {**origem, "filename": Path(valor["$midia"]).name}
            if valor.get("alt"):
                m["alt"] = valor["alt"]
            return {"$media": m}
        return {k: resolver_midia(v) for k, v in valor.items()}
    return valor


drupal = json.loads((AQUI / "drupal.json").read_text(encoding="utf-8"))
conteudo = {nome: resolver_midia(itens) for nome, itens in drupal["conteudo"].items()}

NOMES = {"pt": "Jornais Franceses no Brasil", "en": "French Newspapers in Brazil", "fr": "Journaux français au Brésil"}
CHAMADA = {
    "pt": "Projeto de pesquisa sobre a circulação de periódicos franceses no Brasil e as transferências culturais na imprensa, séculos XIX e XX.",
    "en": "Research project on the circulation of French periodicals in Brazil and cultural transfers in the press, 19th and 20th centuries.",
    "fr": "Projet de recherche sur la circulation des périodiques français au Brésil et les transferts culturels dans la presse, XIXe et XXe siècles.",
}
conteudo["aparencia"] = [
    {
        "id": f"aparencia-site-{lang}", "slug": "site", "locale": lang, "status": "published",
        "data": {"title": NOMES[lang], "chamada": CHAMADA[lang], "contato_email": "", "contato_endereco": ""},
        **({} if lang == "pt" else {"translationOf": "aparencia-site-pt"}),
    }
    for lang in IDIOMAS
]

MENU = {
    "pt": [("apresentacao", "Apresentação"), ("publicacoes", "Publicações"), ("verbetes", "Verbetes"), ("noticias", "Notícias"),
           ("exposicoes", "Exposições"), ("pesquisadores", "Pesquisadores"), ("banco-de-dados", "Banco de dados"), ("creditos", "Créditos")],
    "en": [("apresentacao", "About"), ("publicacoes", "Publications"), ("verbetes", "Entries"), ("noticias", "News"),
           ("exposicoes", "Exhibitions"), ("pesquisadores", "Researchers"), ("banco-de-dados", "Database"), ("creditos", "Credits")],
    "fr": [("apresentacao", "Présentation"), ("publicacoes", "Publications"), ("verbetes", "Notices"), ("noticias", "Actualités"),
           ("exposicoes", "Expositions"), ("pesquisadores", "Chercheurs"), ("banco-de-dados", "Base de données"), ("creditos", "Crédits")],
}
menus = []
for lang in IDIOMAS:
    itens = []
    for chave, rotulo in MENU[lang]:
        item = {"id": f"item:principal:{chave}:{lang}", "type": "custom", "label": rotulo, "url": f"/{lang}/{chave}", "locale": lang}
        if lang != "pt":
            item["translationOf"] = f"item:principal:{chave}:pt"
        itens.append(item)
    menu = {"id": f"menu:principal:{lang}", "name": "principal", "label": "Menu principal", "locale": lang, "items": itens}
    if lang != "pt":
        menu["translationOf"] = "menu:principal:pt"
    menus.append(menu)

seed = {
    "$schema": "https://emdashcms.com/seed.schema.json",
    "version": "1",
    "defaultLocale": "pt",
    "meta": {
        "name": "Jornais Franceses no Brasil",
        "description": "Conteúdo do site Jornais Franceses no Brasil, migrado do Drupal",
        "author": "Jornais Franceses no Brasil",
    },
    "settings": {"title": "Jornais Franceses no Brasil", "tagline": "Imprensa francesa no Brasil, séculos XIX e XX", "timezone": "America/Sao_Paulo"},
    "collections": colecoes,
    "menus": menus,
    "content": {c["slug"]: conteudo.get(c["slug"], []) for c in colecoes},
}

destino = AQUI / "seed.json"
destino.write_text(json.dumps(seed, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(f"Gravado {destino} (mídia em {REPO}@{REF})")
