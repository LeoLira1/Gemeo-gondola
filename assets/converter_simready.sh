#!/usr/bin/env bash
# Converte as empilhadeiras e paleteiras SimReady (assets/simready/, ver baixar_simready.py) em .glb leves
# para a cena Three.js, em static/modelos/.
#   1. assets/usd_para_glb.py: USD -> .glb cru (Y para cima, atlas UDIM)
#   2. gltfpack: simplifica para ~TRIS triângulos, junta malhas e quantiza (KHR_mesh_quantization)
#   3. gltf-transform: tira texturas repetidas e passa para WebP (EXT_texture_webp)
# Precisa de: pip install usd-core trimesh pillow numpy · node 18+ (npx baixa gltfpack e gltf-transform)
set -euo pipefail
cd "$(dirname "$0")/.."
TRIS=${TRIS:-40000}
SAIDA=static/modelos
TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
mkdir -p "$SAIDA"

for usd in assets/simready/*/simready_usd/sm_*.usd; do
  nome=$(basename "$(dirname "$(dirname "$usd")")")
  python3 assets/usd_para_glb.py "$usd" "$TMP/$nome.glb" | tee "$TMP/log"
  tris=$(grep -o '[0-9]* triângulos' "$TMP/log" | cut -d' ' -f1)
  razao=$(python3 -c "print(min(1, $TRIS / $tris))")
  npx -y gltfpack@0.24.0 -i "$TMP/$nome.glb" -o "$TMP/$nome.s.glb" -si "$razao"
  npx -y @gltf-transform/cli@4.5.1 dedup "$TMP/$nome.s.glb" "$TMP/$nome.d.glb"
  npx -y @gltf-transform/cli@4.5.1 webp "$TMP/$nome.d.glb" "$SAIDA/$nome.glb" --quality 85
  ls -la "$SAIDA/$nome.glb"
done
