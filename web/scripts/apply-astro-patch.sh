#!/bin/bash
# Aplica parche para Astro 4.16 + Node 24: fallo al importar dist/renderers.mjs
set -e
WEB_DIR="$(cd "$(dirname "$0")/.." && pwd)"
TARGET_A="$WEB_DIR/node_modules/astro/dist/core/build/generate.js"
TARGET_B="$WEB_DIR/node_modules/astro/dist/core/build/pipeline.js"

if [ ! -f "$TARGET_A" ] || [ ! -f "$TARGET_B" ]; then
    echo "Astro no instalado; omitiendo parche."
    exit 0
fi

apply_once() {
    local file="$1"
    if grep -q 'return new URL("./" + filePath, outFolder);' "$file" 2>/dev/null; then
        echo "Ya parcheado: $file"
        return
    fi
    sed -i 's|return new URL("./" + filePath + `?time=${Date.now()}`\, outFolder);|return new URL("./" + filePath, outFolder);|g' "$file"
    echo "Parcheado: $file"
}

apply_once "$TARGET_A"
apply_once "$TARGET_B"
echo "Parche de Astro aplicado."
