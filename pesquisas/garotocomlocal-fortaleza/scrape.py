"""Coleta os perfis de Fortaleza em garotocomlocal.com.br e filtra por região.

Uso (dentro do .venv do projeto):
    python pesquisas/garotocomlocal-fortaleza/scrape.py [--offline]

Saídas (mesmo diretório deste script):
    perfis_fortaleza.csv   -> todos os perfis com bairro/zona/contato
    perfis_fortaleza.json  -> mesmo conteúdo, com o texto do anúncio
    resultado.md           -> apenas os perfis que batem no filtro
                              (zona sul, Aeroporto, Varjota)
    cache/                 -> HTML bruto de cada página (evita rebaixar)
"""

from __future__ import annotations

import argparse
import csv
import html
import json
import re
import sys
import time
import unicodedata
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import httpx

BASE = "https://garotocomlocal.com.br"
LISTING_URL = f"{BASE}/fortaleza/"
HERE = Path(__file__).resolve().parent
CACHE_DIR = HERE / "cache"
UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/128.0 Safari/537.36"
)
WORKERS = 4
DELAY_S = 0.25

# Bairros da Regional VI (Messejana) — a "zona sul" propriamente dita.
ZONA_SUL = {
    "aerolandia", "alto da balanca", "ancuri", "barroso", "boa vista",
    "castelao", "cajazeiras", "cambeba", "cidade dos funcionarios", "coacu",
    "conjunto palmeiras", "curio", "dias macedo", "edson queiroz", "guajeru",
    "jangurussu", "jardim das oliveiras", "jose de alencar", "lagoa redonda",
    "messejana", "parque dois irmaos", "parque iracema", "parque manibura",
    "parque santa maria", "passare", "paupina", "pedras", "sabiaguaba",
    "sao bento", "sapiranga", "coite", "agua fria", "alagadico novo",
    "mata galinha", "lagoa sapiranga", "parque alvorada",
}

# Bairros da Regional V — periferia sul/sudoeste. Ficam em seção separada
# porque "sul de Fortaleza" é ambíguo e o usuário pode querer incluí-los.
ZONA_SUDOESTE = {
    "bom jardim", "granja portugal", "mondubim", "conjunto ceara",
    "conjunto ceara i", "conjunto ceara ii", "siqueira", "canindezinho",
    "parque sao jose", "prefeito jose walter", "planalto ayrton senna",
    "genibau", "granja lisboa", "maraponga", "manoel satiro",
    "vila manoel satiro", "parque santa rosa", "novo mondubim", "aracape",
    "conjunto esperanca", "jardim cearense", "parque presidente vargas",
    "itaperi", "dende", "passare",
}

BAIRROS_ALVO = {"aeroporto", "varjota"}

# Palavras-chave procuradas no texto do anúncio (para perfis sem endereço).
KEYWORDS_TEXTO = sorted(ZONA_SUL | BAIRROS_ALVO, key=len, reverse=True)


def slugify(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = re.sub(r"[^a-z0-9]+", " ", text.lower())
    return text.strip()


def strip_tags(fragment: str) -> str:
    fragment = re.sub(r"<br\s*/?>", "\n", fragment, flags=re.I)
    fragment = re.sub(r"<[^>]+>", "", fragment)
    fragment = html.unescape(fragment)
    return re.sub(r"\n\s*\n+", "\n", fragment).strip()


def fetch(client: httpx.Client, url: str, cache_name: str, offline: bool) -> str:
    path = CACHE_DIR / cache_name
    if path.exists():
        return path.read_text(encoding="utf-8")
    if offline:
        raise FileNotFoundError(f"sem cache para {url}")
    for attempt in range(4):
        try:
            r = client.get(url)
            r.raise_for_status()
            path.write_text(r.text, encoding="utf-8")
            time.sleep(DELAY_S)
            return r.text
        except httpx.HTTPError as exc:
            if attempt == 3:
                raise
            time.sleep(2 ** attempt)
            print(f"  retry {attempt + 1} {url}: {exc}", file=sys.stderr)
    raise RuntimeError("unreachable")


def listing_urls(listing_html: str) -> list[str]:
    urls = re.findall(
        r'href="(https://garotocomlocal\.com\.br/acompanhante-masculino/[^"#?]+/)"',
        listing_html,
    )
    seen: dict[str, None] = {}
    for u in urls:
        seen.setdefault(u, None)
    return list(seen)


def parse_bairro(address: str) -> str:
    """'Av. X - Messejana, Fortaleza - CE, Brasil' -> 'Messejana'."""
    if not address:
        return ""
    head = address.split(", Fortaleza")[0].strip()
    if head.lower().startswith("fortaleza"):
        return ""
    if " - " in head:
        head = head.rsplit(" - ", 1)[-1]
    head = head.strip()
    # Plus codes do Google ("7FGH+8JW Fortaleza - Zone 1") não têm bairro.
    if re.fullmatch(r"zone \d+", head.lower()):
        return ""
    return head


def classify(bairro: str, texto: str) -> tuple[str, list[str]]:
    """Retorna (zona, bairros_mencionados_no_texto)."""
    b = slugify(bairro)
    zona = "outra"
    if not b:
        zona = "nao informado"
    elif b in BAIRROS_ALVO:
        zona = b
    elif b in ZONA_SUL:
        zona = "sul"
    elif b in ZONA_SUDOESTE:
        zona = "sudoeste"
    t = slugify(texto)
    mencoes = [k for k in KEYWORDS_TEXTO if re.search(rf"\b{k}\b", t)]
    return zona, mencoes


def parse_profile(url: str, page: str) -> dict:
    name = re.search(r'<h1 itemprop="name"[^>]*>(.*?)</h1>', page, re.S)
    address = re.search(r'itemprop="streetAddress">(.*?)</span>', page, re.S)
    phone = re.search(r'class="whatsapp-phone">(.*?)</span>', page, re.S)
    since = re.search(r"Anunciante desde\s*([\d/]+)", page)
    text = re.search(r'<div id="text"[^>]*>(.*?)</div>\s*</div>', page, re.S)
    texto = strip_tags(text.group(1)) if text else ""
    nome = strip_tags(name.group(1)) if name else url.rstrip("/").split("/")[-1]
    endereco = strip_tags(address.group(1)) if address else ""
    bairro = parse_bairro(endereco)
    zona, mencoes = classify(bairro, texto)

    def grab(label: str) -> str:
        m = re.search(rf"{label}\s*:?\s*([^\n•|]+)", texto, re.I)
        return m.group(1).strip() if m else ""

    return {
        "nome": nome,
        "url": url,
        "endereco": endereco,
        "bairro": bairro,
        "zona": zona,
        "bairros_no_texto": ", ".join(mencoes),
        "sem_local": "sem local" in slugify(nome) or "sem local" in slugify(texto),
        "whatsapp": strip_tags(phone.group(1)) if phone else "",
        "anunciante_desde": since.group(1) if since else "",
        "documentos_verificados": "Documentos verificados" in page,
        "tem_video": "<video" in page,
        "idade": grab("Idade"),
        "altura": grab("Altura"),
        "peso": grab("Peso"),
        "texto": texto,
    }


def matches(p: dict) -> bool:
    if p["zona"] in {"sul", "aeroporto", "varjota"}:
        return True
    # Sem bairro no endereço, mas o texto cita um bairro-alvo.
    return p["zona"] == "nao informado" and bool(p["bairros_no_texto"])


def write_outputs(perfis: list[dict]) -> None:
    perfis.sort(key=lambda p: (p["zona"], p["bairro"], p["nome"]))
    fields = [k for k in perfis[0] if k != "texto"]
    with (HERE / "perfis_fortaleza.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(perfis)
    (HERE / "perfis_fortaleza.json").write_text(
        json.dumps(perfis, ensure_ascii=False, indent=1), encoding="utf-8"
    )

    selecionados = [p for p in perfis if matches(p)]
    sudoeste = [p for p in perfis if p["zona"] == "sudoeste"]
    sem_bairro = [p for p in perfis if p["zona"] == "nao informado" and not p["bairros_no_texto"]]

    def table(rows: list[dict]) -> str:
        out = ["| Nome | Bairro | Endereço | WhatsApp | Desde | Local | Vídeo | Perfil |",
               "|---|---|---|---|---|---|---|---|"]
        for p in rows:
            local = "sem local" if p["sem_local"] else "com local"
            bairro = p["bairro"] or f"(texto: {p['bairros_no_texto']})"
            out.append(
                f"| {p['nome']} | {bairro} | {p['endereco']} | {p['whatsapp']} | "
                f"{p['anunciante_desde']} | {local} | {'sim' if p['tem_video'] else 'não'} | "
                f"[abrir]({p['url']}) |"
            )
        return "\n".join(out)

    def group(rows: list[dict], key: str) -> str:
        parts = []
        for k in sorted({p[key] for p in rows}):
            sub = [p for p in rows if p[key] == k]
            parts.append(f"\n### {k or '(sem bairro no endereço)'} ({len(sub)})\n\n{table(sub)}")
        return "\n".join(parts)

    md = [
        "# Fortaleza — perfis na zona sul, Aeroporto ou Varjota",
        "",
        f"Fonte: {LISTING_URL} — coletado em {time.strftime('%d/%m/%Y %H:%M UTC', time.gmtime())}.",
        f"Total de perfis na cidade: **{len(perfis)}**. Selecionados: **{len(selecionados)}**.",
        "",
        "Critério: bairro do endereço na Regional VI (Messejana e entorno), em Aeroporto ou em Varjota;",
        "perfis sem bairro no endereço entram quando o texto do anúncio cita um desses bairros.",
        "",
        "## Selecionados",
        group(selecionados, "bairro"),
        "",
        f"## Periferia sul/sudoeste (Regional V) — {len(sudoeste)} perfis, não incluídos por padrão",
        "",
        "Incluir só se \"sul de Fortaleza\" for entendido de forma ampla.",
        table(sudoeste) if sudoeste else "_nenhum_",
        "",
        f"## Sem bairro informado — {len(sem_bairro)} perfis",
        "",
        "Endereço genérico (\"Fortaleza - CE\") e texto sem menção a bairro-alvo. Impossível classificar sem contato.",
        table(sem_bairro) if sem_bairro else "_nenhum_",
        "",
    ]
    (HERE / "resultado.md").write_text("\n".join(md), encoding="utf-8")
    print(f"{len(perfis)} perfis | {len(selecionados)} selecionados | "
          f"{len(sudoeste)} sudoeste | {len(sem_bairro)} sem bairro")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--offline", action="store_true", help="usa só o cache local")
    args = ap.parse_args()
    CACHE_DIR.mkdir(exist_ok=True)

    with httpx.Client(headers={"User-Agent": UA}, timeout=30, follow_redirects=True) as client:
        listing = fetch(client, LISTING_URL, "_listing.html", args.offline)
        urls = listing_urls(listing)
        print(f"{len(urls)} perfis na listagem")

        perfis: list[dict] = []
        with ThreadPoolExecutor(max_workers=WORKERS) as pool:
            futs = {
                pool.submit(fetch, client, u, u.rstrip("/").split("/")[-1] + ".html", args.offline): u
                for u in urls
            }
            for i, fut in enumerate(as_completed(futs), 1):
                u = futs[fut]
                try:
                    perfis.append(parse_profile(u, fut.result()))
                except Exception as exc:  # noqa: BLE001
                    print(f"  falha {u}: {exc}", file=sys.stderr)
                    perfis.append({**parse_profile(u, ""), "erro": str(exc)})
                if i % 25 == 0:
                    print(f"  {i}/{len(urls)}")

    write_outputs(perfis)


if __name__ == "__main__":
    main()
