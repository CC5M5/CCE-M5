#!/usr/bin/env python3
"""
Descarga ilustraciones de artistas católicos para el repositorio CCE-M5.
Fuentes:
- Fano (Patxi Velasco): https://diocesismalaga.es/dibujos-de-fano-en-color
- Pati.te: artículos en Alfa y Omega / Aleteia / web oficial
- Sara BG: https://sarabg.com/collections/all

Uso:
  .venv/bin/python scripts/descargar_ilustraciones.py --out data/ilustraciones
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from PIL import Image


def safe_name(text: str | None, max_len: int = 60) -> str:
    """Normaliza texto para nombre de archivo; devuelve siempre un nombre válido."""
    if not text:
        return "sin_titulo"
    text = str(text).lower()
    text = re.sub(r"[^a-z0-9áéíóúüñ\s-]", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+", "_", text.strip())
    text = text.strip("_")[:max_len]
    return text or "sin_titulo"


def download(url: str, dest: Path, session: requests.Session, retries: int = 3) -> bool:
    """Descarga URL a destino. Retorna True si éxito."""
    if dest.exists():
        return True
    for attempt in range(retries):
        try:
            r = session.get(url, timeout=20)
            r.raise_for_status()
            dest.write_bytes(r.content)
            return True
        except Exception as e:
            print(f"  intento {attempt + 1} fallido para {url}: {e}")
            time.sleep(1)
    return False


def validate_image(path: Path) -> bool:
    """Comprueba que el archivo sea una imagen legible con tamaño razonable."""
    try:
        with Image.open(path) as im:
            w, h = im.size
            return w >= 400 and h >= 400
    except Exception:
        return False


def fetch_fano(session: requests.Session, out_dir: Path, max_per_year: int = 8, years: list[int] | None = None) -> list[dict]:
    """Descarga ilustraciones de Fano desde la web de Diócesis de Málaga."""
    if years is None:
        years = list(range(2014, 2027))
    base_url = "https://diocesismalaga.es/dibujos-de-fano-en-color"
    results: list[dict] = []

    for year in years:
        url = f"{base_url}?year={year}" if year else base_url
        print(f"[Fano] Año {year}: {url}")
        try:
            r = session.get(url, timeout=30)
            r.raise_for_status()
        except Exception as e:
            print(f"  Error cargando {url}: {e}")
            continue
        soup = BeautifulSoup(r.text, "html.parser")
        items = []
        for link in soup.find_all("a", href=re.compile(r"/media/dibujos/\d+\.jpg")):
            img_url = urljoin(base_url, link.get("href"))
            m = re.search(r"/media/dibujos/(\d+)\.jpg", img_url)
            if not m:
                continue
            img_id = m.group(1)
            # extraer título: siguiente <p> o img alt
            container = link.find_parent("div") or link
            title = ""
            alt_img = link.find("img")
            if alt_img:
                title = alt_img.get("alt", "")
            if not title:
                for p in container.find_all("p"):
                    txt = p.get_text(strip=True)
                    if txt and not re.match(r"\d{2}/\d{2}/\d{4}", txt):
                        title = txt
                        break
            # fecha
            fecha = ""
            for p in container.find_all("p"):
                txt = p.get_text(strip=True)
                if re.match(r"\d{2}/\d{2}/\d{4}", txt):
                    fecha = txt
                    break
            items.append({"id": img_id, "url": img_url, "title": title, "fecha": fecha})

        # Eliminar duplicados por ID
        seen = set()
        unique_items = []
        for it in items:
            if it["id"] not in seen:
                seen.add(it["id"])
                unique_items.append(it)

        print(f"  {len(unique_items)} imágenes encontradas, descargando hasta {max_per_year}")
        for it in unique_items[:max_per_year]:
            filename = f"fano_{it['id']}_{safe_name(it['title'])}.jpg"
            dest = out_dir / "fano" / filename
            dest.parent.mkdir(parents=True, exist_ok=True)
            if download(it["url"], dest, session):
                if validate_image(dest):
                    results.append({
                        "artista": "fano",
                        "id": it["id"],
                        "archivo": str(dest.relative_to(out_dir)),
                        "titulo": it["title"],
                        "fecha": it["fecha"],
                        "url_origen": it["url"],
                    })
                    print(f"    OK {dest.name}")
                else:
                    print(f"    IMAGEN INVÁLIDA {dest.name}")
                    dest.unlink(missing_ok=True)
            else:
                print(f"    FAIL {it['url']}")
            time.sleep(0.3)
    return results


def fetch_sarabg(session: requests.Session, out_dir: Path, max_images: int = 30) -> list[dict]:
    """Descarga imágenes de producto de la tienda Sara BG."""
    base = "https://sarabg.com/collections/all"
    results: list[dict] = []
    print(f"[Sara BG] {base}")
    try:
        r = session.get(base, timeout=30)
        r.raise_for_status()
    except Exception as e:
        print(f"  Error: {e}")
        return results

    soup = BeautifulSoup(r.text, "html.parser")
    # Agrupar por URL de producto, recolectando mejor título e imagen
    product_data: dict[str, dict] = {}
    for card in soup.find_all("a", href=re.compile(r"/products/")):
        href = card.get("href", "").split("?")[0]
        if not href.startswith("/products/"):
            continue
        product_url = urljoin(base, href)
        data = product_data.setdefault(product_url, {"title": "", "img_url": ""})
        # título: buscar h2/h3/h4/span con clase de título, o todo texto limpio
        title_text = card.get_text(" ", strip=True)
        # limpiar precios y "Agotado" si viene junto
        title_text = re.sub(r"\s*€[\d.,]+\s*", " ", title_text)
        title_text = re.sub(r"\bAgotado\b", "", title_text, flags=re.IGNORECASE)
        title_text = re.sub(r"\bAhorre\s+\d+%?", "", title_text, flags=re.IGNORECASE)
        title_text = title_text.strip()
        # buscar específicamente elemento título
        title_el = card.find(["h2", "h3", "h4", "span", "p"], class_=re.compile(r"title|product|name", re.I))
        if title_el:
            el_text = re.sub(r"\bAgotado\b", "", title_el.get_text(strip=True), flags=re.IGNORECASE).strip()
            if el_text and len(el_text) < 120:
                data["title"] = el_text
        elif title_text and len(title_text) < 120 and title_text.lower() not in {"", "agotado"}:
            if not data["title"] or len(title_text) > len(data["title"]):
                data["title"] = title_text
        # imagen
        img = card.find("img")
        if img and not data["img_url"]:
            img_url = img.get("src", "")
            if img_url.startswith("//"):
                img_url = "https:" + img_url
            elif img_url.startswith("/"):
                img_url = urljoin(base, img_url)
            if img_url:
                data["img_url"] = img_url

    products = [(url, d["title"], d["img_url"]) for url, d in product_data.items() if d["img_url"]]
    print(f"  {len(products)} productos encontrados, descargando hasta {max_images}")
    for url, title, img_url in products[:max_images]:
        if not title:
            title = url.split("/")[-1].replace("-", " ")
        ext = Path(urlparse(img_url).path).suffix or ".jpg"
        filename = f"sarabg_{safe_name(title)}_{hashlib.md5(img_url.encode()).hexdigest()[:8]}{ext}"
        dest = out_dir / "sarabg" / filename
        dest.parent.mkdir(parents=True, exist_ok=True)
        if download(img_url, dest, session):
            if validate_image(dest):
                results.append({
                    "artista": "sarabg",
                    "archivo": str(dest.relative_to(out_dir)),
                    "titulo": title,
                    "url_origen": img_url,
                    "url_producto": url,
                })
                print(f"    OK {dest.name}")
            else:
                print(f"    IMAGEN INVÁLIDA {dest.name}")
                dest.unlink(missing_ok=True)
        else:
            print(f"    FAIL {img_url}")
        time.sleep(0.3)
    return results


def fetch_patite_articles(session: requests.Session, out_dir: Path, max_images: int = 30) -> list[dict]:
    """Busca ilustraciones de Pati.te en artículos conocidos."""
    urls = [
        "https://alfayomega.es/pati-te-mis-padres-me-han-transmitido-la-ternura-que-se-aprecia-en-mis-ilustraciones/",
        "https://es.aleteia.org/2019/09/11/una-joven-ilustradora-emociona-en-las-redes-con-sus-dibujos-de-la-virgen/",
        "https://www.eldebate.com/religion/catolicos/20240527/patite-influencer-acerca-virgen-165000-seguidores-hay-alguien-tocando-almas-estos-trazos_199277.html",
        "https://www.patite.es/",
        "https://www.patite.es/colaboraciones/",
        "https://www.cope.es/religion/hoy-en-dia/iglesia-espanola/noticias/pati-trigo-idea-virgen-mis-dibujos-sencilla-joven-cercana-muy-amiga-20210102_1826402",
    ]
    results: list[dict] = []
    print("[Pati.te] Buscando imágenes en artículos...")
    for article_url in urls:
        print(f"  {article_url}")
        try:
            r = session.get(article_url, timeout=30)
            r.raise_for_status()
        except Exception as e:
            print(f"    Error: {e}")
            continue
        soup = BeautifulSoup(r.text, "html.parser")
        for img in soup.find_all("img"):
            src = img.get("src", "")
            if not src:
                continue
            if src.startswith("//"):
                src = "https:" + src
            elif src.startswith("/"):
                src = urljoin(article_url, src)
            parsed = urlparse(src)
            ext = Path(parsed.path).suffix.lower()
            if ext not in {".jpg", ".jpeg", ".png", ".webp"}:
                continue
            # descartar iconos/logos pequeños por URL
            low = src.lower()
            if any(x in low for x in ["logo", "icon", "avatar", "banner", "whatsapp", "facebook", "twitter", "instagram", "pinterest", "reuters", "hhs", "osv", "apple", "iphone"]):
                continue
            # descartar imágenes muy pequeñas por URL (miniaturas de tema)
            if any(x in low for x in ["kallyas", "theme", "favicon"]):
                continue
            alt = img.get("alt", "") or img.get("title", "")
            # descartar si alt parece no religioso
            if alt and any(x in alt.lower() for x in ["reuters", "hhs", "saoirse", "iphone", "apple"]):
                continue
            filename = f"patite_{safe_name(alt or 'ilustracion')}_{hashlib.md5(src.encode()).hexdigest()[:8]}{ext}"
            dest = out_dir / "patite" / filename
            dest.parent.mkdir(parents=True, exist_ok=True)
            if download(src, dest, session):
                if validate_image(dest):
                    results.append({
                        "artista": "patite",
                        "archivo": str(dest.relative_to(out_dir)),
                        "titulo": alt,
                        "url_origen": src,
                        "url_articulo": article_url,
                    })
                    print(f"    OK {dest.name}")
                    if len(results) >= max_images:
                        return results
                else:
                    dest.unlink(missing_ok=True)
            time.sleep(0.3)
    return results


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="/tmp/cce-m5-descargas")
    parser.add_argument("--max-fano-year", type=int, default=8)
    parser.add_argument("--max-sarabg", type=int, default=30)
    parser.add_argument("--max-patite", type=int, default=30)
    parser.add_argument("--metadata", default="/tmp/cce-m5-descargas/metadata.json")
    args = parser.parse_args()

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "es-ES,es;q=0.9",
    })

    all_meta: list[dict] = []
    all_meta.extend(fetch_fano(session, out_dir, max_per_year=args.max_fano_year))
    all_meta.extend(fetch_sarabg(session, out_dir, max_images=args.max_sarabg))
    all_meta.extend(fetch_patite_articles(session, out_dir, max_images=args.max_patite))

    # Deduplicar físico: eliminar duplicados dentro de cada artista
    for artista in {"fano", "sarabg", "patite"}:
        folder = out_dir / artista
        if not folder.exists():
            continue
        hashes: dict[str, Path] = {}
        for p in folder.iterdir():
            if not p.is_file():
                continue
            h = hashlib.md5(p.read_bytes()).hexdigest()
            if h in hashes:
                print(f"[DEDUPE] Eliminando duplicado {p.name} (igual a {hashes[h].name})")
                p.unlink()
                all_meta = [m for m in all_meta if m.get("archivo") != str(p.relative_to(out_dir))]
            else:
                hashes[h] = p

    Path(args.metadata).write_text(json.dumps(all_meta, indent=2, ensure_ascii=False))
    print(f"\nTotal descargado: {len(all_meta)} imágenes")
    print(f"Metadatos guardados en {args.metadata}")


if __name__ == "__main__":
    main()
