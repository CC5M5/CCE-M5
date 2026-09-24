#!/usr/bin/env python3
"""
Genera el catalogo.json del repositorio de ilustraciones CCE-M5 a partir de las
imágenes descargadas de Fano, Pati.te y Sara BG.

- Elimina referencias repetidas.
- Asigna imágenes a momentos litúrgicos según palabras clave en títulos.
- Genera un catálogo extendido con metadatos.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from PIL import Image


PROJECT_DIR = Path(__file__).resolve().parents[1]
ILUSTRACIONES_DIR = PROJECT_DIR / "data" / "ilustraciones"
CATALOGO_PATH = ILUSTRACIONES_DIR / "catalogo.json"
EXTENDED_PATH = ILUSTRACIONES_DIR / "catalogo_extendido.json"

MOMENTOS = [
    "portada",
    "entrada",
    "transicion_palabra",
    "perdon",
    "paso",
    "gloria",
    "primera_lectura",
    "salmo",
    "segunda_lectura",
    "aleluya",
    "evangelio",
    "transicion_eucaristia",
    "credo",
    "ofertorio",
    "santo",
    "padre_nuestro",
    "paz",
    "comunion",
    "maria",
    "despedida",
]


KEYWORDS: dict[str, list[str]] = {
    "maria": ["virgen", "maria", "madre", "fatima", "fatima", "nazaret", "inmaculada", "abrazada", "mirame", "mariana", "mariplano", "magnificat"],
    "paz": ["paz", "comunidad", "abrazo", "hermanos", "unidos", "unidad", "reconciliacion", "familia", "amor"],
    "comunion": ["pan", "vino", "eucaristia", "comunion", "comer", "mesa", "cordero", "cena", "altar", "ofrecer", "ofrenda"],
    "salmo": ["salmo", "palabra", "agua", "luz", "semilla", "seminador", "camino", "sembrar", "crecer", "vid", "pastor", "oveja"],
    "perdon": ["perdon", "confesar", "pecado", "conversion", "arrepentir", "misericordia", "corazon", "penitencia", "luchar"],
    "gloria_aleluya": ["gloria", "aleluya", "espiritu", "rey", "resucitado", "pascua", "fiesta", "cielo", "triunfo", "hosanna"],
    "entrada": ["entrar", "camino", "llamar", "llamada", "venid", "venga", "recibir", "abrir", "puerta", "caminar", "invitar", "bienvenido"],
    "ofertorio": ["ofrenda", "ofrecer", "don", "dar", "entregar", "manos", "servir", "compartir"],
    "santo_padre_credo": ["santo", "padre", "credo", "fe", "oracion", "rezar", "trinidad", "paternoster", "amarse"],
    "despedida": ["despedida", "enviar", "mision", "mundo", "ir", "paz", "bendicion", "camino", "gracias"],
    "lecturas": ["lectura", "evangelio", "biblia", "escritura", "palabra", "anunciar", "proclamar", "profeta"],
}


def score_for_momento(path: Path, title: str, momento: str) -> int:
    """Puntuación heurística de adecuación de una imagen a un momento."""
    text = f"{path.name} {title}".lower()
    text = re.sub(r"[^a-záéíóúüñ\s]", " ", text)
    words = set(text.split())

    score = 0
    if momento == "maria" and any(k in words for k in KEYWORDS["maria"]):
        score += 10
    if momento == "paz" and any(k in words for k in KEYWORDS["paz"]):
        score += 10
    if momento in ("comunion", "ofertorio") and any(k in words for k in KEYWORDS["comunion"]):
        score += 10
    if momento == "salmo" and any(k in words for k in KEYWORDS["salmo"]):
        score += 10
    if momento == "perdon" and any(k in words for k in KEYWORDS["perdon"]):
        score += 10
    if momento in ("gloria", "aleluya") and any(k in words for k in KEYWORDS["gloria_aleluya"]):
        score += 10
    if momento == "entrada" and any(k in words for k in KEYWORDS["entrada"]):
        score += 10
    if momento in ("santo", "padre_nuestro", "credo") and any(k in words for k in KEYWORDS["santo_padre_credo"]):
        score += 10
    if momento == "despedida" and any(k in words for k in KEYWORDS["despedida"]):
        score += 10
    if momento in ("primera_lectura", "segunda_lectura", "evangelio") and any(k in words for k in KEYWORDS["lecturas"]):
        score += 10
    # momentos transición y paso aceptan cualquier imagen religiosa válida
    if momento in ("transicion_palabra", "transicion_eucaristia", "paso", "portada"):
        score += 1
    return score


def load_images() -> list[dict[str, Any]]:
    """Carga metadatos de todas las imágenes válidas del repositorio."""
    images: list[dict[str, Any]] = []
    for p in ILUSTRACIONES_DIR.rglob("*"):
        if not p.is_file() or p.name in {"catalogo.json", "catalogo_extendido.json", "descargas_metadata.json"}:
            continue
        if p.suffix.lower() not in {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"}:
            continue
        try:
            with Image.open(p) as im:
                w, h = im.size
            if w < 400 or h < 400:
                continue
        except Exception:
            continue

        rel = str(p.relative_to(ILUSTRACIONES_DIR))
        artista = rel.split("/")[0]
        title = derive_title(p, artista)
        images.append({
            "archivo": rel,
            "artista": artista,
            "titulo": title,
            "ancho": w,
            "alto": h,
            "bytes": p.stat().st_size,
            "hash": hashlib.md5(p.read_bytes()).hexdigest(),
        })
    return images


def derive_title(path: Path, artista: str) -> str:
    """Deriva un título legible del nombre de archivo."""
    name = path.stem
    # quitar prefijo artista_ y sufijos hash
    name = re.sub(r"^(fano|patite|sarabg)_", "", name)
    name = re.sub(r"_[a-f0-9]{8}$", "", name)
    name = re.sub(r"_\d{8}$", "", name)  # ids fano
    name = name.replace("_", " ").strip()
    name = re.sub(r"\s+", " ", name)
    # capitalizar primeras letras
    return name.title() if name else path.name


def assign_images(images: list[dict[str, Any]]) -> dict[str, list[str]]:
    """Asigna imágenes a momentos litúrgicos minimizando repeticiones."""
    assignments: dict[str, list[str]] = {m: [] for m in MOMENTOS}
    used_refs: set[str] = set()

    # Primero, asignar preferencias fuertes por momento
    for momento in MOMENTOS:
        scores = []
        for img in images:
            if img["archivo"] in used_refs:
                continue
            s = score_for_momento(Path(img["archivo"]), img["titulo"], momento)
            if s > 0:
                scores.append((s, img["archivo"], img["artista"]))
        # Ordenar por score, priorizar diversidad de artista
        scores.sort(key=lambda x: (-x[0], x[2], x[1]))
        # Tomar hasta 8 imágenes, intentando no repetir artista consecutivamente
        artista_count: dict[str, int] = {}
        for _, ref, artista in scores:
            if len(assignments[momento]) >= 8:
                break
            if artista_count.get(artista, 0) >= 5:
                continue
            assignments[momento].append(ref)
            used_refs.add(ref)
            artista_count[artista] = artista_count.get(artista, 0) + 1

    # Rellenar momentos con pocas imágenes con cualquier imagen no usada
    unused = [img for img in images if img["archivo"] not in used_refs]
    for momento in MOMENTOS:
        while len(assignments[momento]) < 5 and unused:
            img = unused.pop(0)
            assignments[momento].append(img["archivo"])
            used_refs.add(img["archivo"])

    # Asegurar que transiciones, paso y maria tengan variedad
    for momento in ("paso", "transicion_palabra", "transicion_eucaristia", "portada", "maria"):
        while len(assignments[momento]) < 6 and unused:
            img = unused.pop(0)
            assignments[momento].append(img["archivo"])
            used_refs.add(img["archivo"])

    return assignments


def build_extended_catalog(images: list[dict[str, Any]], assignments: dict[str, list[str]]) -> dict[str, Any]:
    """Construye el catálogo extendido con metadatos."""
    by_file = {img["archivo"]: img for img in images}
    catalogo: dict[str, Any] = {
        "descripcion": "Catálogo de ilustraciones por tipo de slide. Se resuelve la primera imagen disponible en el orden indicado.",
        "fuentes": {
            "fano": "Dibujos de Patxi Velasco Fano (uso pastoral no comercial)",
            "patite": "Ilustraciones de Pati.te (Patricia Trigo, uso pastoral no comercial)",
            "sarabg": "Ilustraciones de Sara BG (Sara Bargueño, uso pastoral no comercial)",
        },
        "imagenes": assignments,
        "metadatos": {},
    }
    for momento, refs in assignments.items():
        for ref in refs:
            img = by_file.get(ref, {})
            catalogo["metadatos"][ref] = {
                "artista": img.get("artista", "desconocido"),
                "titulo": img.get("titulo", ""),
                "dimensiones": f"{img.get('ancho', 0)}x{img.get('alto', 0)}",
            }
    return catalogo


def main() -> None:
    print("Cargando imágenes...")
    images = load_images()
    print(f"  {len(images)} imágenes válidas")

    print("Asignando imágenes a momentos litúrgicos...")
    assignments = assign_images(images)

    print("Escribiendo catálogo.json...")
    catalogo = {
        "descripcion": "Catálogo de ilustraciones por tipo de slide. Se resuelve la primera imagen disponible en el orden indicado.",
        "fuentes": {
            "fano": "Dibujos de Patxi Velasco Fano (uso pastoral no comercial)",
            "patite": "Ilustraciones de Pati.te (Patricia Trigo, uso pastoral no comercial)",
            "sarabg": "Ilustraciones de Sara BG (Sara Bargueño, uso pastoral no comercial)",
        },
        "imagenes": assignments,
    }
    CATALOGO_PATH.write_text(json.dumps(catalogo, indent=2, ensure_ascii=False))

    print("Escribiendo catalogo_extendido.json...")
    extended = build_extended_catalog(images, assignments)
    EXTENDED_PATH.write_text(json.dumps(extended, indent=2, ensure_ascii=False))

    # Resumen
    total_refs = sum(len(v) for v in assignments.values())
    unique_refs = len(set(r for v in assignments.values() for r in v))
    print(f"\nTotal referencias en catálogo: {total_refs}")
    print(f"Imágenes únicas referenciadas: {unique_refs}")
    for momento, refs in assignments.items():
        print(f"  {momento}: {len(refs)} imágenes")


if __name__ == "__main__":
    main()
