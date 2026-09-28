#!/bin/bash
# Aplica parche para Astro 4.16/4.19 + Node 24:
# - Astro usa URLs file://.../pages/404.astro.mjs?time=... para importar páginas
#   generadas, y Node 24 no las resuelve correctamente.
# - También falla al importar dist/renderers.mjs con new URL().
set -e
WEB_DIR="$(cd "$(dirname "$0")/.." && pwd)"
TARGET_A="$WEB_DIR/node_modules/astro/dist/core/build/generate.js"
TARGET_B="$WEB_DIR/node_modules/astro/dist/core/build/pipeline.js"

if [ ! -f "$TARGET_A" ] || [ ! -f "$TARGET_B" ]; then
    echo "Astro no instalado; omitiendo parche."
    exit 0
fi

# Añadir import pathToFileURL si falta
ensure_import() {
    local file="$1"
    if ! grep -q 'pathToFileURL' "$file"; then
        # generate.js: después de import os
        # pipeline.js: al inicio del archivo
        if [ "$file" = "$TARGET_A" ]; then
            sed -i 's|import os from "node:os";|import os from "node:os";\nimport { pathToFileURL } from "node:url";|' "$file"
        else
            sed -i '1s|^|import { pathToFileURL } from "node:url";\n|' "$file"
        fi
        echo "Import añadido en $file"
    fi
}

# Quitar query time de createEntryURL
patch_create_entry_url() {
    local file="$1"
    if grep -q 'return new URL("./" + filePath + `?time=${Date.now()}`\, outFolder);' "$file"; then
        sed -i 's|return new URL("./" + filePath + `?time=${Date.now()}`\, outFolder);|return new URL("./" + filePath, outFolder);|g' "$file"
        echo "createEntryURL parcheado en $file"
    fi
}

# Usar pathToFileURL para renderersEntryUrl
patch_renderers_url() {
    local file="$1"
    # Variantes originales que pueden aparecer
    sed -i 's|const renderersEntryUrl = new URL("renderers.mjs"\, baseDirectory);|const renderersEntryUrl = pathToFileURL(new URL("renderers.mjs", baseDirectory).pathname);|g' "$file"
    sed -i 's|const renderersEntryUrl = new URL(`renderers.mjs?time=${Date.now()}`, baseDirectory);|const renderersEntryUrl = pathToFileURL(new URL("renderers.mjs", baseDirectory).pathname);|g' "$file"
    if grep -q 'pathToFileURL(new URL("renderers.mjs"' "$file"; then
        echo "renderersEntryUrl parcheado en $file"
    fi
}

ensure_import "$TARGET_A"
ensure_import "$TARGET_B"
patch_create_entry_url "$TARGET_A"
patch_create_entry_url "$TARGET_B"
patch_renderers_url "$TARGET_A"
patch_renderers_url "$TARGET_B"

echo "Parche de Astro aplicado."
