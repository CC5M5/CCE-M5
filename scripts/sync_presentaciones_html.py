#!/usr/bin/env python3
"""
Sincroniza los bundles generados en presentaciones_html/ con web/public/presentaciones_html/.

Uso:
  python3 scripts/sync_presentaciones_html.py [--project-dir DIR]
  python3 scripts/sync_presentaciones_html.py --fecha 2026-09-27 [--project-dir DIR]
"""
import argparse
import shutil
import sys
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Sincroniza presentaciones HTML/PDF/PPTX a web/public"
    )
    parser.add_argument(
        "--project-dir",
        type=Path,
        default=None,
        help="Directorio raíz del proyecto (default: directorio padre de scripts/)",
    )
    parser.add_argument(
        "--fecha", help="Sincroniza solo la fecha indicada (YYYY-MM-DD)"
    )
    return parser.parse_args()


def sincronizar(project_dir: Path, fecha: str | None = None) -> list[Path]:
    src_dir = project_dir / "presentaciones_html"
    dst_dir = project_dir / "web" / "public" / "presentaciones_html"

    if not src_dir.exists():
        print("No existe fuente:", src_dir, file=sys.stderr)
        sys.exit(1)
    dst_dir.mkdir(parents=True, exist_ok=True)

    copiados: list[Path] = []
    if fecha:
        src = src_dir / f"{fecha}_presentacion"
        dst = dst_dir / f"{fecha}_presentacion"
        if not src.exists():
            print(f"No existe bundle para {fecha}", file=sys.stderr)
            sys.exit(1)
        if dst.exists():
            shutil.rmtree(dst)
        shutil.copytree(src, dst)
        copiados.append(dst)
    else:
        # Copia completa: limpiar destino y volver a copiar todo
        if dst_dir.exists():
            shutil.rmtree(dst_dir)
        shutil.copytree(src_dir, dst_dir)
        for child in dst_dir.iterdir():
            if child.is_dir():
                copiados.append(child)

    for d in copiados:
        print(f"Sincronizado: {d.name}")
    return copiados


if __name__ == "__main__":
    args = parse_args()
    if args.project_dir:
        project_dir = args.project_dir.resolve()
    else:
        project_dir = Path(__file__).resolve().parents[1]
    sincronizar(project_dir, args.fecha)
