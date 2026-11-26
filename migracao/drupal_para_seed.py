#!/usr/bin/env python3
"""Converte o conteúdo do site antigo (Drupal 7) para o seed do EmDash.

Roda uma vez, na migração, a partir da extração somente leitura do Drupal (ver
docs/migracao.md):

  python3 -I migracao/drupal_para_seed.py --extracao <pasta> --espelho <pasta>

<pasta da extração> tem nos.tsv (a lista do /admin/content) e bruto/<nid>.edit.html.gz
(o formulário de edição de cada nó, que traz todos os campos). <pasta do espelho>
é a cópia do site feita com wget, de onde saem as imagens e os arquivos; o que
faltar nela é baixado do site antigo (só funciona dentro da unespNET).

Gera:
  seed/drupal.json               conteúdo das coleções (lido por seed/gerar-seed.py)
  seed/midia/...                 imagens, que o seed sobe para a mídia do EmDash
  public/arquivos/...            PDFs e outros anexos, servidos pelo próprio site
  src/lib/redirecionamentos.json endereços antigos -> novos
  migracao/relatorio.md          o que foi convertido e o que ficou de fora

Só entram os tipos do site (páginas, notícias, verbetes, pesquisadores,
exposições e destaques). O Banco de Dados JFB tem migração própria.
"""
import argparse
import csv
import gzip
import html
import json
import re
import shutil
import ssl
import sys
import unicodedata
import urllib.request
from collections import Counter, defaultdict
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlparse

RAIZ = Path(__file__).resolve().parent.parent
SITE = "jfb.franca.unesp.br"
FILES = "/sites/jfb.franca.unesp.br/files/"

# Tipo do Drupal -> coleção do EmDash.
TIPOS = {
    "Basic page": "paginas",
    "Notícia": "noticias",
    "Verbete": "verbetes",
    "Pesquisador": "pesquisadores",
    "Exposição": "exposicoes",
    "imagem Slideshow home": "destaques",
}
# Páginas internas do Drupal (manual do banco, testes de layout): ficam de fora.
PAGINAS_FORA = {"home", "logos", "administracao", "modelagem", "info"}
# Slugs reservados pelas rotas de lista.
RESERVADOS = {"noticias", "verbetes", "pesquisadores", "exposicoes"}
LIMITE_ESTATICO = 20 * 1024 * 1024
EXT_IMAGEM = {".jpg", ".jpeg", ".png", ".gif", ".webp"}


# ---------- leitura do formulário de edição ----------

def ler_formulario(caminho):
    t = gzip.open(caminho).read().decode("utf-8", "replace")
    inicio = t.find('-node-form"')
    form = t[t.rfind("<form", 0, inicio):] if inicio > 0 else t
    form = form[: form.find("</form>") + 7]
    campos = defaultdict(list)
    for m in re.finditer(r"<(input|textarea|select)\b([^>]*)>(.*?)(?=<(?:input|textarea|select)\b|</form>)", form, re.S):
        tag, attrs, resto = m.groups()
        nome = re.search(r'name="([^"]+)"', attrs)
        if not nome:
            continue
        nome = nome.group(1)
        if tag == "input":
            tipo = (re.search(r'type="([^"]+)"', attrs) or [None, "text"])[1]
            if tipo in ("checkbox", "radio"):
                if "checked" in attrs:
                    campos[nome].append(html.unescape(re.search(r'value="([^"]*)"', attrs).group(1)))
                continue
            if tipo == "submit":
                continue
            v = re.search(r'value="([^"]*)"', attrs)
            campos[nome].append(html.unescape(v.group(1)) if v else "")
        elif tag == "textarea":
            campos[nome].append(html.unescape(resto.split("</textarea>")[0]))
        else:
            campos[nome].extend(html.unescape(x) for x in re.findall(r'<option[^>]*selected[^>]*value="([^"]*)"', resto.split("</select>")[0]))
            campos[nome].extend(html.unescape(x) for x in re.findall(r'<option[^>]*value="([^"]*)"[^>]*selected', resto.split("</select>")[0]))
    return form, campos


def um(campos, nome, padrao=""):
    v = campos.get(nome)
    return v[0].strip() if v else padrao


def arquivos_do_campo(form, campo):
    """URLs dos arquivos de um campo de imagem/arquivo, na ordem dos itens."""
    chave = campo.replace("_", "-")
    inicio = form.find(f'id="edit-{chave}-und-ajax-wrapper"')
    if inicio < 0:
        return []
    fim = form.find('id="edit-field-', form.find(f'id="edit-{chave}-und-ajax-wrapper"') + 10)
    while fim > 0 and form.startswith(f'id="edit-{chave}', fim):
        fim = form.find('id="edit-field-', fim + 10)
    bloco = form[inicio: fim if fim > 0 else len(form)]
    urls = []
    for url in re.findall(r'href="(https?://[^"]*' + re.escape(FILES) + r'(?!styles/)[^"]+)"', bloco):
        if url not in urls:
            urls.append(url)
    alts = [html.unescape(a) for a in re.findall(rf'name="{campo}\[und\]\[\d+\]\[alt\]"[^>]*value="([^"]*)"', bloco)]
    return [(u, alts[i] if i < len(alts) else "") for i, u in enumerate(urls)]


# ---------- arquivos ----------

class Arquivos:
    def __init__(self, espelho, relatorio):
        self.espelho = Path(espelho) / SITE if espelho else None
        self.relatorio = relatorio
        self.ctx = ssl.create_default_context()
        self.ctx.check_hostname = False
        self.ctx.verify_mode = ssl.CERT_NONE

    @staticmethod
    def relativo(url):
        """/sites/.../files/styles/medium/public/images/x.jpg -> images/x.jpg"""
        caminho = unquote(urlparse(url).path)
        if FILES not in caminho:
            return None
        rel = caminho.split(FILES, 1)[1]
        rel = re.sub(r"^styles/[^/]+/public/", "", rel)
        return rel

    def obter(self, rel, destino):
        if destino.exists():
            return True
        destino.parent.mkdir(parents=True, exist_ok=True)
        if self.espelho and (self.espelho / FILES.strip("/") / rel).is_file():
            shutil.copyfile(self.espelho / FILES.strip("/") / rel, destino)
            return True
        url = f"https://{SITE}{FILES}{urllib.request.quote(rel)}"
        try:
            with urllib.request.urlopen(url, context=self.ctx, timeout=120) as r, open(destino, "wb") as f:
                shutil.copyfileobj(r, f)
            return True
        except Exception as erro:  # noqa: BLE001 - registrado no relatório
            self.relatorio["arquivos_faltando"].append(f"{rel} ({erro})")
            return False

    def imagem(self, url, alt=""):
        rel = self.relativo(url)
        if not rel or Path(rel).suffix.lower() not in EXT_IMAGEM:
            return None
        nome = limpar_caminho(rel)
        final = RAIZ / "seed" / "midia" / nome
        webp = final.with_suffix(".webp")
        if webp.exists():
            return {"$midia": f"midia/{Path(nome).with_suffix('.webp')}", "alt": alt}
        if not final.exists():
            bruto = RAIZ / "migracao" / ".cache" / nome
            if not self.obter(rel, bruto):
                return None
            final = reduzir(bruto, final)
        return {"$midia": str(final.relative_to(RAIZ / "seed")), "alt": alt}

    def documento(self, url):
        rel = self.relativo(url)
        if not rel:
            return None
        nome = limpar_caminho(rel)
        destino = RAIZ / "public" / "arquivos" / nome
        grande = RAIZ / "migracao" / ".cache" / "grandes" / nome
        if grande.exists():
            self.relatorio["arquivos_grandes"].append(f"arquivos/{nome} ({destino_mb(grande)} MB)")
            return f"/arquivos/{nome}"
        if not self.obter(rel, destino):
            return None
        # Arquivos estáticos do Worker vão até 25 MiB: os maiores ficam fora do
        # repositório e são servidos do bucket R2 (src/pages/arquivos/[...caminho].ts).
        if destino.stat().st_size > LIMITE_ESTATICO:
            grande.parent.mkdir(parents=True, exist_ok=True)
            shutil.move(destino, grande)
            self.relatorio["arquivos_grandes"].append(f"arquivos/{nome} ({destino_mb(grande)} MB)")
        return f"/arquivos/{nome}"


def reduzir(origem, destino, lado=1600, limite=300_000):
    """Copia a imagem para seed/midia; as maiores que 300 KB viram WebP de no
    máximo 1600 px de lado (ImageMagick). Devolve o caminho gravado."""
    destino.parent.mkdir(parents=True, exist_ok=True)
    if origem.stat().st_size <= limite or not shutil.which("magick") or origem.suffix.lower() == ".gif":
        shutil.copyfile(origem, destino)
        return destino
    import subprocess
    webp = destino.with_suffix(".webp")
    feito = subprocess.run(["magick", str(origem), "-auto-orient", "-resize", f"{lado}x{lado}>", "-strip", "-quality", "80", str(webp)], check=False)
    if feito.returncode != 0 or not webp.exists():
        shutil.copyfile(origem, destino)
        return destino
    return webp


def destino_mb(caminho):
    return f"{caminho.stat().st_size / 1048576:.1f}".replace(".", ",")


def limpar_caminho(rel):
    partes = []
    for p in rel.split("/"):
        p = unicodedata.normalize("NFKD", p).encode("ascii", "ignore").decode()
        p = re.sub(r"[^A-Za-z0-9._-]+", "-", p).strip("-") or "arquivo"
        partes.append(p.lower())
    return "/".join(partes)


# ---------- HTML -> Portable Text ----------

class Conversor(HTMLParser):
    """HTML do Drupal (CKEditor) -> blocos Portable Text do EmDash.

    Parágrafos, títulos, listas, citações, links, negrito/itálico, imagens
    (blocos de imagem), iframes (vídeos) e tabelas (bloco HTML). Estilos inline
    e classes do editor antigo são descartados.
    """

    BLOCOS = {"p": "normal", "h1": "h2", "h2": "h2", "h3": "h3", "h4": "h4", "h5": "h4", "h6": "h4", "blockquote": "blockquote"}
    MARCAS = {"strong": "strong", "b": "strong", "em": "em", "i": "em", "u": "underline", "s": "strike-through", "strike": "strike-through"}

    def __init__(self, arquivos, mapa_links, prefixo):
        super().__init__(convert_charrefs=True)
        self.arquivos = arquivos
        self.mapa = mapa_links
        self.prefixo = prefixo
        self.saida = []
        self.n = 0
        self.atual = None
        self.estilo = "normal"
        self.marcas = []
        self.links = []
        self.listas = []
        self.tabela = None
        self.ignorar = 0

    def chave(self):
        self.n += 1
        return f"{self.prefixo}-{self.n}"

    # blocos de texto
    def abrir(self, estilo=None, lista=None):
        self.fechar()
        self.atual = {"_type": "block", "_key": self.chave(), "style": estilo or self.estilo, "markDefs": [], "children": []}
        if lista:
            self.atual["listItem"] = lista
            self.atual["level"] = len(self.listas)

    def fechar(self):
        b = self.atual
        self.atual = None
        if not b:
            return
        # junta espaços e descarta bloco vazio
        for c in b["children"]:
            c["text"] = re.sub(r"[ \t\r\n\xa0]+", " ", c["text"])
        while b["children"] and not b["children"][0]["text"].strip():
            b["children"].pop(0)
        if b["children"]:
            b["children"][0]["text"] = b["children"][0]["text"].lstrip()
            # Itens de lista que repetiam o marcador à mão ("- Verbetes").
            if b.get("listItem"):
                b["children"][0]["text"] = re.sub(r"^[-–•]\s+", "", b["children"][0]["text"])
            b["children"][-1]["text"] = b["children"][-1]["text"].rstrip()
        b["children"] = [c for c in b["children"] if c["text"]]
        if not b["children"]:
            return
        usados = {m for c in b["children"] for m in c["marks"]}
        b["markDefs"] = [d for d in b["markDefs"] if d["_key"] in usados]
        self.saida.append(b)

    def texto(self, t):
        if self.ignorar:
            return
        if self.tabela is not None:
            self.tabela.append(html.escape(t))
            return
        if not t.strip() and self.atual is None:
            return
        if self.atual is None:
            self.abrir()
        marcas = list(dict.fromkeys(self.marcas + [l for l in self.links if l]))
        filhos = self.atual["children"]
        if filhos and filhos[-1]["marks"] == marcas:
            filhos[-1]["text"] += t
        else:
            filhos.append({"_type": "span", "_key": self.chave(), "text": t, "marks": marcas})

    def handle_data(self, data):
        self.texto(data)

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag in ("script", "style"):
            self.ignorar += 1
            return
        if self.tabela is not None:
            if tag in ("table", "thead", "tbody", "tr", "th", "td", "caption"):
                extra = "".join(f' {k}="{html.escape(v)}"' for k, v in attrs if k in ("colspan", "rowspan") and v)
                self.tabela.append(f"<{tag}{extra}>")
            elif tag == "br":
                self.tabela.append("<br>")
            elif tag == "a" and a.get("href"):
                self.tabela.append(f'<a href="{html.escape(self.link(a["href"]))}">')
            elif tag in ("strong", "b", "em", "i"):
                self.tabela.append(f"<{tag}>")
            return
        if tag == "table":
            self.fechar()
            self.tabela = ["<table>"]
        elif tag in self.BLOCOS:
            self.estilo = self.BLOCOS[tag]
            self.abrir(self.estilo)
        elif tag in ("ul", "ol"):
            self.fechar()
            self.listas.append("bullet" if tag == "ul" else "number")
        elif tag == "li":
            self.abrir("normal", self.listas[-1] if self.listas else "bullet")
        elif tag == "br":
            if self.atual is not None:
                self.texto("\n")
        elif tag in self.MARCAS:
            self.marcas.append(self.MARCAS[tag])
        elif tag == "a":
            href = self.link(a.get("href", ""))
            if href and self.atual is None:
                self.abrir()
            if href:
                k = self.chave()
                self.atual["markDefs"].append({"_type": "link", "_key": k, "href": href})
                self.links.append(k)
            else:
                self.links.append(None)
        elif tag == "img":
            self.imagem(a)
        elif tag == "iframe" and a.get("src"):
            self.fechar()
            src = a["src"]
            if src.startswith("//"):
                src = "https:" + src
            self.saida.append({"_type": "iframe", "_key": self.chave(), "src": src, "title": a.get("title") or "Vídeo", "allowFullscreen": True})
        elif tag in ("div", "section", "center"):
            self.fechar()

    def handle_endtag(self, tag):
        if tag in ("script", "style"):
            self.ignorar = max(0, self.ignorar - 1)
            return
        if self.tabela is not None:
            if tag in ("table", "thead", "tbody", "tr", "th", "td", "caption", "a", "strong", "b", "em", "i"):
                self.tabela.append(f"</{tag}>")
            if tag == "table":
                self.saida.append({"_type": "htmlBlock", "_key": self.chave(), "html": "".join(self.tabela)})
                self.tabela = None
            return
        if tag in self.BLOCOS or tag == "li":
            self.fechar()
            self.estilo = "normal"
        elif tag in ("ul", "ol"):
            self.fechar()
            if self.listas:
                self.listas.pop()
        elif tag in self.MARCAS and self.MARCAS[tag] in self.marcas:
            self.marcas.reverse()
            self.marcas.remove(self.MARCAS[tag])
            self.marcas.reverse()
        elif tag == "a" and self.links:
            self.links.pop()
        elif tag in ("div", "section", "center"):
            self.fechar()

    def imagem(self, a):
        src = a.get("src", "")
        if not src:
            return
        url = src if src.startswith("http") else f"https://{SITE}{src}" if src.startswith("/") else src
        midia = self.arquivos.imagem(url, a.get("alt", "")) if SITE in url else None
        estava = self.atual
        if estava is not None:
            self.fechar()
        if midia:
            self.saida.append({"_type": "image", "_key": self.chave(), "asset": midia, **({"alt": midia["alt"]} if midia.get("alt") else {})})
        elif url.startswith("https://"):
            self.arquivos.relatorio["imagens_externas"].append(url)
        if estava is not None:
            self.abrir(estava["style"], estava.get("listItem"))

    def link(self, href):
        href = (href or "").strip()
        if not href or href.startswith(("javascript:", "#")):
            return ""
        if href.startswith("mailto:"):
            return href
        u = urlparse(href)
        if u.netloc and u.netloc not in (SITE, "www." + SITE, "pjf.w20.com.br"):
            return href if u.scheme in ("http", "https") else ""
        caminho = unquote(u.path)
        if FILES in caminho:
            return self.arquivos.documento(href) or href
        novo = self.mapa.get(caminho.strip("/"))
        if novo:
            return novo
        self.arquivos.relatorio["links_internos_sem_destino"].append(href)
        return f"/pt/{caminho.strip('/')}" if caminho.strip("/") else "/pt/"

    def resultado(self):
        self.fechar()
        return self.saida


def desmontar_tabelas_de_layout(texto):
    """Tabelas usadas para dividir a página em colunas (células com <div>, <p> ou
    <br>) viram blocos em sequência; a primeira linha curta de cada célula vira
    título. Tabelas de dados (células só com texto) ficam como tabela."""
    def trocar(m):
        tabela = m.group(0)
        if not re.search(r"<t[dh][^>]*>\s*(?:<(?:div|p)\b|[^<]*<br)", tabela, re.I):
            return tabela

        def celula(mc):
            corpo = mc.group(1)
            primeira = re.match(r"^\s*<(div|p)[^>]*>(.*?)</\1>", corpo, flags=re.S | re.I)
            if primeira and 0 < len(re.sub(r"<[^>]+>|\s+", " ", primeira.group(2)).strip()) <= 60:
                corpo = f"<h2>{primeira.group(2)}</h2>" + corpo[primeira.end():]
            return f"<div>{corpo}</div>"

        tabela = re.sub(r"<t[dh][^>]*>(.*?)</t[dh]>", celula, tabela, flags=re.S | re.I)
        return re.sub(r"</?(table|tbody|thead|tr)[^>]*>", "", tabela, flags=re.I)

    return re.sub(r"<table\b.*?</table>", trocar, texto or "", flags=re.S | re.I)


def portable_text(html_texto, arquivos, mapa, prefixo):
    c = Conversor(arquivos, mapa, prefixo)
    c.feed(desmontar_tabelas_de_layout(html_texto))
    c.close()
    return c.resultado()


def galeria(imagens, prefixo):
    return {
        "_type": "gallery",
        "_key": f"{prefixo}-galeria",
        "images": [{"_type": "image", "_key": f"{prefixo}-g{i}", "asset": m, **({"alt": m["alt"]} if m.get("alt") else {})} for i, m in enumerate(imagens)],
    }


def lista_anexos(anexos, prefixo):
    blocos = []
    for i, (nome, href) in enumerate(anexos):
        k = f"{prefixo}-a{i}"
        blocos.append({
            "_type": "block", "_key": k, "style": "normal", "listItem": "bullet", "level": 1,
            "markDefs": [{"_type": "link", "_key": f"{k}l", "href": href}],
            "children": [{"_type": "span", "_key": f"{k}s", "text": nome, "marks": [f"{k}l"]}],
        })
    return blocos


# ---------- datas e slugs ----------

def data_iso(texto):
    """'2025-09-01 11:57:14 -0300' -> '2025-09-01T14:57:14.000Z'"""
    m = re.match(r"(\d{4})-(\d\d)-(\d\d) (\d\d):(\d\d):(\d\d) ([+-])(\d\d)(\d\d)", texto or "")
    if not m:
        return None
    from datetime import datetime, timedelta, timezone
    a, mes, d, h, mi, s, sinal, oh, om = m.groups()
    fuso = timezone((1 if sinal == "+" else -1) * timedelta(hours=int(oh), minutes=int(om)))
    dt = datetime(int(a), int(mes), int(d), int(h), int(mi), int(s), tzinfo=fuso).astimezone(timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%S.000Z")


def slug_de(alias, titulo, usados):
    base = alias.rstrip("/").split("/")[-1] if alias else ""
    if not base:
        base = unicodedata.normalize("NFKD", titulo).encode("ascii", "ignore").decode().lower()
    base = re.sub(r"[^a-z0-9]+", "-", base.lower()).strip("-")[:80].strip("-") or "item"
    slug, i = base, 2
    while slug in usados:
        slug, i = f"{base}-{i}", i + 1
    usados.add(slug)
    return slug


# ---------- principal ----------

def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--extracao", required=True, help="pasta com nos.tsv e bruto/")
    ap.add_argument("--espelho", help="pasta do espelho wget (com jfb.franca.unesp.br/)")
    args = ap.parse_args()
    ext = Path(args.extracao)

    relatorio = defaultdict(list)
    # Conteúdo que sai do site JFB (decisão de curadoria de 25/11/2026): fica só o
    # que é do acervo de jornais franceses no Brasil. Ver migracao/curadoria.json.
    global CURADORIA
    CURADORIA = json.loads((RAIZ / "migracao" / "curadoria.json").read_text(encoding="utf-8"))
    arquivos = Arquivos(args.espelho, relatorio)
    nos = [r for r in csv.DictReader(open(ext / "nos.tsv", encoding="utf-8"), delimiter="\t") if r["tipo"] in TIPOS and r["nid"]]

    # 1a passada: lê os formulários, decide slug e endereço novo de cada nó.
    lidos = []
    usados = defaultdict(set)
    for r in nos:
        caminho = ext / "bruto" / f"{r['nid']}.edit.html.gz"
        if not caminho.exists():
            relatorio["sem_extracao"].append(f"{r['nid']} {r['tipo']}: {r['titulo']}")
            continue
        form, campos = ler_formulario(caminho)
        colecao = TIPOS[r["tipo"]]
        alias = um(campos, "path[alias]")
        titulo = um(campos, "title") or r["titulo"]
        publicado = "1" in campos.get("status", [])
        slug_base = alias.rstrip("/").split("/")[-1] if alias else ""
        if colecao == "paginas" and slug_base in PAGINAS_FORA:
            relatorio["fora"].append(f"{r['nid']} página interna: {titulo} ({alias})")
            continue
        if not publicado:
            relatorio["fora"].append(f"{r['nid']} não publicado ({r['tipo']}): {titulo}")
            continue
        if r["nid"] in CURADORIA:
            cur = CURADORIA[r["nid"]]
            relatorio["curadoria"].append((cur["destino"], f"{r['nid']} · {titulo} · {cur['motivo']} · antigo /{alias or 'node/' + r['nid']}"))
            continue
        slug = slug_de(alias, titulo, usados[colecao])
        if colecao == "paginas" and slug in RESERVADOS:
            slug = slug_de(f"{slug}-pagina", titulo, usados[colecao])
        lidos.append({"nid": r["nid"], "tipo": r["tipo"], "colecao": colecao, "form": form, "campos": campos,
                      "alias": alias, "titulo": titulo, "slug": slug, "idioma": r["idioma"]})

    # Traduções da Apresentação: páginas separadas no Drupal, viram en/fr da mesma.
    TRADUCOES = {"presentation": "en", "presentation-2": "fr", "presentation-0": "fr"}
    destino_de = {}
    for n in lidos:
        if n["colecao"] == "destaques":
            continue
        lang = TRADUCOES.get(n["slug"]) if n["colecao"] == "paginas" else None
        if lang:
            n["lang"], n["slug"] = lang, "apresentacao"
        url = f"/{n.get('lang', 'pt')}/{n['slug']}" if n["colecao"] == "paginas" else f"/pt/{n['colecao']}/{n['slug']}"
        n["url"] = url
        destino_de[f"node/{n['nid']}"] = url
        if n["alias"]:
            destino_de[n["alias"].strip("/")] = url
    # Listas do site antigo.
    destino_de.update({
        "noticias": "/pt/noticias", "publicacoes/verbetes": "/pt/verbetes", "pesquisadores": "/pt/pesquisadores",
        "exposicoes": "/pt/exposicoes", "exposicao": "/pt/exposicoes",
    })

    # Ordem dos pesquisadores: a da página /pesquisadores do site antigo.
    ordem_pesquisadores = {}
    lista_antiga = Path(args.espelho or "/nao-existe") / SITE / "pesquisadores.html"
    if lista_antiga.exists():
        for href in re.findall(r'href="(?:https?://[^/"]+)?/(pesquisadores/[^"#?]+)"', lista_antiga.read_text(encoding="utf-8", errors="replace")):
            ordem_pesquisadores.setdefault(href.strip("/"), (len(ordem_pesquisadores) + 1) * 10)

    # 2a passada: monta as entradas.
    conteudo = defaultdict(list)
    for n in lidos:
        c, campos, form, nid = n["colecao"], n["campos"], n["form"], n["nid"]
        pref = f"n{nid}"
        corpo_html = um(campos, "field_corpo[und][0][value]") or um(campos, "body[und][0][value]")
        corpo = portable_text(corpo_html, arquivos, destino_de, pref)
        if c == "verbetes":
            texto_verbete = um(campos, "field_verbete[und][0][value]")
            if texto_verbete:
                corpo = portable_text(texto_verbete, arquivos, destino_de, pref + "v") + corpo
        imagens = []
        for campo in ("field_imagem", "field_foto"):
            for url, alt in arquivos_do_campo(form, campo):
                m = arquivos.imagem(url, alt or n["titulo"])
                if m:
                    imagens.append(m)
        anexos = []
        for url, _ in arquivos_do_campo(form, "field_anexo"):
            href = arquivos.documento(url)
            if href:
                anexos.append((Path(href).name, href))
        data = data_iso(um(campos, "date"))
        dados = {"title": n["titulo"]}
        if c == "destaques":
            if not imagens:
                relatorio["fora"].append(f"{nid} destaque sem imagem: {n['titulo']}")
                continue
            dados.update({"imagem": imagens[0], "link": "", "ordem": len(conteudo[c]) + 1})
        else:
            capa = None
            if c in ("noticias", "exposicoes", "pesquisadores", "paginas") and imagens:
                capa, imagens = imagens[0], imagens[1:]
            if imagens:
                corpo.append(galeria(imagens, pref))
            if anexos:
                corpo.append({"_type": "block", "_key": f"{pref}-anexos", "style": "h3", "markDefs": [],
                              "children": [{"_type": "span", "_key": f"{pref}-anexos-s", "text": "Arquivos", "marks": []}]})
                corpo += lista_anexos(anexos, pref)
            dados["conteudo"] = corpo
            if c == "pesquisadores":
                if capa:
                    dados["foto"] = capa
                dados["ordem"] = ordem_pesquisadores.get(n["alias"].strip("/"), 100)
            else:
                if capa:
                    dados["imagem"] = capa
            if c in ("noticias", "verbetes", "exposicoes") and data:
                dados["data"] = data
            if c in ("noticias", "verbetes"):
                autor = um(campos, "field_autor[und][0][value]")
                if autor:
                    dados["autor"] = autor
            if c == "verbetes":
                sub = um(campos, "field_subtitulo[und][0][value]")
                if sub:
                    dados["subtitulo"] = sub
        lang = n.get("lang", "pt")
        entrada = {"id": f"{c}-{nid}", "slug": n["slug"] if c != "destaques" else f"destaque-{nid}", "locale": lang,
                   "status": "published", "data": dados}
        if lang != "pt":
            orig = next((x for x in lidos if x["colecao"] == "paginas" and x["slug"] == "apresentacao" and x.get("lang", "pt") == "pt"), None)
            if orig:
                entrada["translationOf"] = f"paginas-{orig['nid']}"
        conteudo[c].append(entrada)

    # pt antes das traduções, para o translationOf achar a origem.
    for itens in conteudo.values():
        itens.sort(key=lambda e: e["locale"] != "pt")

    (RAIZ / "seed" / "drupal.json").write_text(
        json.dumps({"origem": f"https://{SITE} (Drupal 7), extraído em 25/11/2026", "conteudo": conteudo}, ensure_ascii=False, indent=1) + "\n",
        encoding="utf-8")
    (RAIZ / "src" / "lib" / "redirecionamentos.json").write_text(
        json.dumps(dict(sorted(destino_de.items())), ensure_ascii=False, indent=1) + "\n", encoding="utf-8")

    contagem = Counter(n["colecao"] for n in lidos)
    linhas = ["# Relatório da migração do conteúdo do site", "",
              "Gerado por `migracao/drupal_para_seed.py`. Contagem por coleção:", ""]
    linhas += [f"- {c}: {k}" for c, k in sorted(contagem.items())]
    curadoria = defaultdict(list)
    for destino, linha in relatorio.get("curadoria", []):
        curadoria[destino].append(linha)
    if curadoria:
        linhas += ["", f"## Saem do site por curadoria ({sum(len(v) for v in curadoria.values())})", "",
                   "Só fica o que é do acervo de jornais franceses no Brasil. Cada item vai para o lugar indicado (migracao/curadoria.json).", ""]
        for destino, itens in sorted(curadoria.items()):
            linhas += [f"### {destino} ({len(itens)})", ""] + [f"- {x}" for x in sorted(itens)] + [""]
    for chave, titulo in [("fora", "Ficaram de fora"), ("sem_extracao", "Sem extração"),
                          ("arquivos_grandes", "Arquivos grandes demais para o repositório: subir no R2 (ver docs/migracao.md)"),
                          ("arquivos_faltando", "Arquivos que não foram encontrados"),
                          ("imagens_externas", "Imagens de outros sites (não copiadas)"),
                          ("links_internos_sem_destino", "Links internos sem destino conhecido (apontados para /pt/<caminho>)")]:
        itens = sorted(set(relatorio.get(chave, [])))
        if itens:
            linhas += ["", f"## {titulo} ({len(itens)})", ""] + [f"- {x}" for x in itens]
    (RAIZ / "migracao" / "relatorio.md").write_text("\n".join(linhas) + "\n", encoding="utf-8")
    print("\n".join(linhas[:12]))


if __name__ == "__main__":
    sys.exit(main())
