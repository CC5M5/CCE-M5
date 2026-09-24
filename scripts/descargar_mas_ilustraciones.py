#!/usr/bin/env python3
"""
Segunda ronda de descarga de ilustraciones para CCE-M5.
Fuentes:
- Más Fano: Diócesis de Málaga (aumentar cuota por año).
- Más Pati.te: artículos de Omnes Mag, Alfa y Omega, Canta y Camina, PEJ22, web oficial (productos de ilustración).
- Más Sara BG: tienda oficial, productos tipo lámina/cuadro/ilustración (no merch).
"""
from __future__ import annotations

import hashlib
import json
import re
import time
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from PIL import Image

PROJECT_DIR = Path(__file__).resolve().parents[1]
OUT_DIR = PROJECT_DIR / "data" / "ilustraciones"
METADATA_PATH = OUT_DIR / "descargas_metadata_2.json"


def safe_name(text: str | None, max_len: int = 60) -> str:
    if not text:
        return "sin_titulo"
    text = str(text).lower()
    text = re.sub(r"[^a-z0-9áéíóúüñ\s-]", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+", "_", text.strip())
    text = text.strip("_")[:max_len]
    return text or "sin_titulo"


def download(url: str, dest: Path, session: requests.Session, retries: int = 3) -> bool:
    if dest.exists():
        return True
    for attempt in range(retries):
        try:
            r = session.get(url, timeout=20)
            if r.status_code == 200:
                dest.write_bytes(r.content)
                return True
        except Exception as e:
            print(f"  intento {attempt + 1} fallido para {url}: {e}")
            time.sleep(1)
    return False


def validate_image(path: Path) -> bool:
    try:
        with Image.open(path) as im:
            w, h = im.size
            return w >= 400 and h >= 400
    except Exception:
        return False


def fetch_fano_more(session: requests.Session, max_per_year: int = 15) -> list[dict]:
    base_url = "https://diocesismalaga.es/dibujos-de-fano-en-color"
    results: list[dict] = []
    for year in range(2014, 2027):
        url = f"{base_url}?year={year}"
        print(f"[Fano+] Año {year}")
        try:
            r = session.get(url, timeout=30)
            r.raise_for_status()
        except Exception as e:
            print(f"  Error: {e}")
            continue
        soup = BeautifulSoup(r.text, "html.parser")
        items = []
        for link in soup.find_all("a", href=re.compile(r"/media/dibujos/\d+\.jpg")):
            img_url = urljoin(base_url, link.get("href"))
            m = re.search(r"/media/dibujos/(\d+)\.jpg", img_url)
            if not m:
                continue
            img_id = m.group(1)
            # evitar duplicados de archivo existente
            dest_check = OUT_DIR / "fano" / f"fano_{img_id}_*.jpg"
            if list(OUT_DIR.glob(f"fano/fano_{img_id}_*.jpg")) or (OUT_DIR / "fano" / f"{img_id}.jpg").exists():
                continue
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
            fecha = ""
            for p in container.find_all("p"):
                txt = p.get_text(strip=True)
                if re.match(r"\d{2}/\d{2}/\d{4}", txt):
                    fecha = txt
                    break
            items.append({"id": img_id, "url": img_url, "title": title, "fecha": fecha})
        seen = set()
        unique = []
        for it in items:
            if it["id"] not in seen:
                seen.add(it["id"])
                unique.append(it)
        print(f"  {len(unique)} nuevas encontradas, descargando hasta {max_per_year}")
        for it in unique[:max_per_year]:
            filename = f"fano_{it['id']}_{safe_name(it['title'])}.jpg"
            dest = OUT_DIR / "fano" / filename
            if download(it["url"], dest, session):
                if validate_image(dest):
                    results.append({"artista": "fano", "archivo": str(dest.relative_to(OUT_DIR)), "titulo": it["title"]})
                    print(f"    OK {dest.name}")
                else:
                    dest.unlink(missing_ok=True)
            time.sleep(0.2)
    return results


def fetch_patite_more(session: requests.Session) -> list[dict]:
    urls = [
        "https://www.omnesmag.com/foco/pati-te-senti-que-el-senor-me-decia-trabaja-con-los-talentos-que-te-he-dado/",
        "https://www.omnesmag.com/en/focus/pati-te-i-felt-the-lord-telling-me-to-work-with-the-talents-i-have-given-you/",
        "https://alfayomega.es/ana-la-virgen-y-la-abuela-catalina/",
        "https://alfayomega.es/tomas-trigo-es-importante-que-los-ninos-no-lean-contenidos-nonos/",
        "https://www.pej22.es/noticias/ilustraciones-de-patite-en-la-pej22/",
        "https://www.pej22.es/mcs-al-servicio-de-la-evangelizacion/",
        "https://cantaycamina.net/maria-la-bella-pastora-joven-embarazada-madre-y-maestra-iesu-communio/",
        "https://www.patite.es/tienda/virgen-fatima/",
    ]
    results: list[dict] = []
    for url in urls:
        print(f"[Pati.te+] {url}")
        try:
            r = session.get(url, timeout=30)
            r.raise_for_status()
        except Exception as e:
            print(f"  Error: {e}")
            continue
        soup = BeautifulSoup(r.text, "html.parser")
        for img in soup.find_all("img"):
            src = img.get("src", "")
            if not src:
                continue
            if src.startswith("//"):
                src = "https:" + src
            elif src.startswith("/"):
                src = urljoin(url, src)
            low = src.lower()
            if not re.search(r"\.(jpg|jpeg|png|webp)", low):
                continue
            if any(x in low for x in ["logo", "icon", "avatar", "banner", "kallyas", "theme", "favicon", "whatsapp", "facebook", "twitter", "instagram", "pinterest", "reuters", "hhs", "apple", "iphone", "osv", "ecclesia", "noticiafaustino", "catalina", "imagen_principal"]):
                continue
            alt = img.get("alt", "") or img.get("title", "")
            if alt and any(x in alt.lower() for x in ["reuters", "hhs", "iphone", "apple", "catalina", "noticia"]):
                continue
            # evitar duplicados por hash al descargar
            filename = f"patite_{safe_name(alt or 'ilustracion')}_{hashlib.md5(src.encode()).hexdigest()[:8]}{Path(urlparse(src).path).suffix or '.jpg'}"
            dest = OUT_DIR / "patite" / filename
            if download(src, dest, session):
                if validate_image(dest):
                    results.append({"artista": "patite", "archivo": str(dest.relative_to(OUT_DIR)), "titulo": alt, "url_origen": src})
                    print(f"    OK {dest.name}")
                else:
                    dest.unlink(missing_ok=True)
            time.sleep(0.2)
    return results


def fetch_sarabg_more(session: requests.Session) -> list[dict]:
    """Descarga ilustraciones de productos de Sara BG descartando merch."""
    base = "https://sarabg.com/collections/all"
    results: list[dict] = []
    print(f"[Sara BG+] {base}")
    try:
        r = session.get(base, timeout=30)
        r.raise_for_status()
    except Exception as e:
        print(f"  Error: {e}")
        return results
    soup = BeautifulSoup(r.text, "html.parser")
    product_data: dict[str, dict] = {}
    for card in soup.find_all("a", href=re.compile(r"/products/")):
        href = card.get("href", "").split("?")[0]
        if not href.startswith("/products/"):
            continue
        product_url = urljoin(base, href)
        data = product_data.setdefault(product_url, {"title": "", "img_url": ""})
        title_text = card.get_text(" ", strip=True)
        title_text = re.sub(r"\s*€[\d.,]+\s*", " ", title_text)
        title_text = re.sub(r"\bAgotado\b", "", title_text, flags=re.IGNORECASE)
        title_text = re.sub(r"\bAhorre\s+\d+%?", "", title_text, flags=re.IGNORECASE)
        title_text = title_text.strip()
        title_el = card.find(["h2", "h3", "h4", "span", "p"], class_=re.compile(r"title|product|name", re.I))
        if title_el:
            el_text = re.sub(r"\bAgotado\b", "", title_el.get_text(strip=True), flags=re.IGNORECASE).strip()
            if el_text and len(el_text) < 120:
                data["title"] = el_text
        elif title_text and title_text.lower() not in {"", "agotado"}:
            if not data["title"] or len(title_text) > len(data["title"]):
                data["title"] = title_text
        img = card.find("img")
        if img and not data["img_url"]:
            img_url = img.get("src", "")
            if img_url.startswith("//"):
                img_url = "https:" + img_url
            elif img_url.startswith("/"):
                img_url = urljoin(base, img_url)
            if img_url:
                data["img_url"] = img_url

    # Filtrar solo ilustraciones/láminas/cuadros, no merch
    merch_keywords = ["pegatinas", "calendario", "carta", "cartas", "colgantes", "bloc", "colorear",
                      "balconera", "adorno", "calvario", "abstracto", "en_calma", "creer_sin_ver",
                      "cuento", "dibujo_para_colorear", "collage", "edén", "buen_pastor", "durmió",
                      "pack", "pegatina", "sticker", "recordatorio", "joya", "medalla"]
    illustration_keywords = ["lamina", "cuadro", "obra", "sagrado", "corazon", "virgen", "maria",
                             "jesus", "cristo", "divina", "pastora", "nazaret", "inmaculado", "paz"]

    products = []
    for url, d in product_data.items():
        if not d["img_url"]:
            continue
        title = (d["title"] or url.split("/")[-1].replace("-", " ")).lower()
        if any(k in title for k in merch_keywords):
            continue
        if any(k in title for k in illustration_keywords):
            products.append((url, d["title"], d["img_url"]))

    print(f"  {len(products)} productos de ilustración encontrados")
    for url, title, img_url in products:
        ext = Path(urlparse(img_url).path).suffix or ".jpg"
        filename = f"sarabg_{safe_name(title)}_{hashlib.md5(img_url.encode()).hexdigest()[:8]}{ext}"
        dest = OUT_DIR / "sarabg" / filename
        if download(img_url, dest, session):
            if validate_image(dest):
                results.append({"artista": "sarabg", "archivo": str(dest.relative_to(OUT_DIR)), "titulo": title, "url_origen": img_url})
                print(f"    OK {dest.name}")
            else:
                dest.unlink(missing_ok=True)
        time.sleep(0.2)
    return results


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "es-ES,es;q=0.9",
    })
    all_meta: list[dict] = []
    all_meta.extend(fetch_fano_more(session, max_per_year=15))
    all_meta.extend(fetch_patite_more(session))
    all_meta.extend(fetch_sarabg_more(session))

    # Deduplicar físico
    for artista in {"fano", "sarabg", "patite"}:
        folder = OUT_DIR / artista
        if not folder.exists():
            continue
        hashes: dict[str, Path] = {}
        for p in folder.iterdir():
            if not p.is_file():
                continue
            h = hashlib.md5(p.read_bytes()).hexdigest()
            if h in hashes:
                print(f"[DEDUPE] {p.name} == {hashes[h].name}")
                p.unlink()
                all_meta = [m for m in all_meta if m.get("archivo") != str(p.relative_to(OUT_DIR))]
            else:
                hashes[h] = p

    METADATA_PATH.write_text(json.dumps(all_meta, indent=2, ensure_ascii=False))
    print(f"\nTotal nuevas descargadas: {len(all_meta)}")


if __name__ == "__main__":
    main()
