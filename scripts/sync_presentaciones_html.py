#!/usr/bin/env python3
"""
Sincroniza los bundles generados en presentaciones_html/ con web/public/presentaciones_html/.

Uso:
  python3 scripts/sync_presentaciones_html.py
  python3 scripts/sync_presentaciones_html.py --fecha 2026-09-27
"""
import argparse
import importlib.util
import shutil
import sys
from pathlib import Path


def _load_settings():
    """Carga src.config.settings sin depender de PYTHONPATH."""
    project_root = Path(__file__).resolve().parents[1]
    module_path = project_root / "src" / "config.py"
    spec = importlib.util.spec_from_file_location("src.config", module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"No se pudo cargar src.config desde {module_path}")
    module = importlib.util.module_from_spec(spec)
    sys.modules["src.config"] = module
    spec.loader.exec_module(module)
    return module.settings


settings = _load_settings()

SRC_DIR = settings.project_dir / "presentaciones_html"
DST_DIR = settings.web_dir / "public" / "presentaciones_html"


def sincronizar(fecha: str | None = None) -> list[Path]:
    if not SRC_DIR.exists():
        print("No existe fuente:", SRC_DIR, file=sys.stderr)
        sys.exit(1)
    DST_DIR.mkdir(parents=True, exist_ok=True)

    copiados: list[Path] = []
    if fecha:
        src = SRC_DIR / f"{fecha}_presentacion"
        dst = DST_DIR / f"{fecha}_presentacion"
        if not src.exists():
            print(f"No existe bundle para {fecha}", file=sys.stderr)
            sys.exit(1)
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(src, dst)
        copiados.append(dst)
    else:
        # Copia completa: limpiar destino y volver a copiar todo
        if DST_DIR.exists():
            shutil.rmtree(DST_DIR)
        shutil.copytree(SRC_DIR, DST_DIR)
        for child in DST_DIR.iterdir():
            if child.is_dir():
                copiados.append(child)

    for d in copiados:
        print(f"Sincronizado: {d.name}")
    return copiados


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Sincroniza presentaciones HTML/PDF/PPTX a web/public")
    parser.add_argument("--fecha", help="Sincroniza solo la fecha indicada (YYYY-MM-DD)")
    args = parser.parse_args()
    sincronizar(args.fecha)
