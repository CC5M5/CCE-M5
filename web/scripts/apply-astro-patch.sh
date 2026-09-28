#!/bin/bash
# Aplica parche para Astro 4.16 + Node 24: fallo al importar dist/renderers.mjs
set -e
WEB_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PATCH_FILE="$WEB_DIR/patches/astro+4.16.19.patch"
TARGET_A="$WEB_DIR/node_modules/astro/dist/core/build/generate.js"
TARGET_B="$WEB_DIR/node_modules/astro/dist/core/build/pipeline.js"

if [ ! -f "$PATCH_FILE" ]; then
    echo "Parche no encontrado: $PATCH_FILE"
    exit 0
fi

# Aplicar solo si aún no está aplicado
if grep -q "pathToFileURL" "$TARGET_A" 2>/dev/null && grep -q "pathToFileURL" "$TARGET_B" 2>/dev/null; then
    echo "Parche de Astro ya aplicado."
    exit 0
fi

cd "$WEB_DIR"
patch -p0 --forward --dry-run < "$PATCH_FILE" >/dev/null 2>&1 || true
patch -p0 --forward < "$PATCH_FILE" || true
echo "Parche de Astro aplicado."
