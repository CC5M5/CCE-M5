#!/usr/bin/env python3
"""Sirve archivos estáticos con soporte para index.html en directorios."""
from __future__ import annotations

import argparse
import os
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


class IndexHTMLHandler(SimpleHTTPRequestHandler):
    """Sirve index.html cuando la URL apunta a un directorio."""

    def __init__(self, request, client_address, server, *, directory: str = ".") -> None:
        self._root = Path(directory).resolve()
        super().__init__(request, client_address, server, directory=directory)

    def send_head(self):
        """Override to serve index.html for directory paths."""
        path = self.translate_path(self.path)
        if os.path.isdir(path):
            index = os.path.join(path, "index.html")
            if os.path.exists(index):
                path = index
        # Reuse base implementation logic for serving the resolved path
        return super().send_head()

    def translate_path(self, path: str) -> str:
        clean = path.split("?", 1)[0].split("#", 1)[0]
        # URL-decode path manually for safe file access
        rel = clean.lstrip("/")
        try:
            # Python 3.7+
            from urllib.parse import unquote  # noqa: PLC0415
            rel = unquote(rel)
        except Exception:
            pass
        target = (self._root / rel).resolve()
        # Prevent path traversal outside root
        try:
            target.relative_to(self._root)
        except ValueError:
            return str(self._root / "404.html")
        return str(target)

    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-cache")
        super().end_headers()


def main() -> int:
    parser = argparse.ArgumentParser(description="Sirve web/dist con index.html por defecto")
    parser.add_argument("--directory", default="/app/web/dist", help="Directorio raíz a servir")
    parser.add_argument("--port", type=int, default=4321, help="Puerto HTTP")
    parser.add_argument("--host", default="0.0.0.0", help="Host HTTP")
    args = parser.parse_args()

    os.chdir(args.directory)
    server = ThreadingHTTPServer((args.host, args.port), IndexHTMLHandler)
    print(f"Sirviendo {args.directory} en http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
