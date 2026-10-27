#!/usr/bin/env python3
"""Regression invariants for the post-audit migration fix (S1, S4, S6)."""
import json, pathlib, re, sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
fails = []

# S1: web export data stays valid and path-free of the origin home
data = json.loads((ROOT / "web/data/presentaciones.json").read_text())
assert isinstance(data, list) and len(data) >= 1
raw = (ROOT / "web/data/presentaciones.json").read_text()
if "/home/pciath" in raw:
    fails.append("S1: /home/pciath present in web/data/presentaciones.json")
for e in data:
    for k in ("ruta_pptx", "ruta_pdf_fieles", "ruta_pdf_musicos", "ruta_web"):
        v = e.get(k)
        if v and v.startswith("/"):
            fails.append(f"S1: absolute {k} in entry {e.get('id')}: {v}")

# S4: systemd templates carry no nvm and pin CCE_NODE_BIN=/usr/bin
for unit in sorted((ROOT / "config/systemd/user").glob("*.service")):
    t = unit.read_text()
    if re.search(r"nvm", t, re.I):
        fails.append(f"S4: nvm reference in {unit.name}")
if "CCE_NODE_BIN=/usr/bin" not in (ROOT / "config/systemd/user/cce-m5-admin.service").read_text():
    fails.append("S4: CCE_NODE_BIN=/usr/bin missing from cce-m5-admin.service template")

# S6: docs carry no dead origin references (historical SDD notes excepted)
for p in list((ROOT / "README.md").glob("*")) + list((ROOT / "specs").rglob("*")):
    if p.is_file() and p.suffix in {".md", ".py", ".js", ".ts", ".sh", ".astro"}:
        t = p.read_text(errors="replace")
        if "/home/pciath" in t or "192.168.68.244" in t:
            fails.append(f"S6: stale reference in {p.relative_to(ROOT)}")
for p in (ROOT / "docs/SDD").rglob("*.md"):
    if "/home/pciath/.nvm" in p.read_text(errors="replace"):
        fails.append(f"S6: dead nvm path in {p.relative_to(ROOT)}")

if fails:
    print("\n".join(fails)); sys.exit(1)
print("migration invariants OK")
