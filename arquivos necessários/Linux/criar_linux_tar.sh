#!/usr/bin/env bash
set -euo pipefail
TOOLS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$TOOLS_DIR/../.." && pwd)"
ZIP_DIR="$ROOT_DIR/ZIP final/Linux"
APP_VERSION="1.100.29"
OUT_DIR="dist/CUMA_linux"
TAR_NAME="CUMA_linux.tar.gz"
TAR_PATH="$ZIP_DIR/$TAR_NAME"
RELEASE_NOTES="NOTAS_RELEASE.md"

# Suporta layouts:
# 1) GitHub Actions / repositorio: ROOT/cuma.py
# 2) pacote novo:                  ROOT/Repositorio_GitHub/cuma.py
# 3) pacote antigo:                ROOT/GitHub/cuma.py
if [ -f "$ROOT_DIR/cuma.py" ]; then
  SRC_DIR="$ROOT_DIR"
elif [ -f "$ROOT_DIR/Repositorio_GitHub/cuma.py" ]; then
  SRC_DIR="$ROOT_DIR/Repositorio_GitHub"
elif [ -f "$ROOT_DIR/GitHub/cuma.py" ]; then
  SRC_DIR="$ROOT_DIR/GitHub"
else
  echo "[ERRO] cuma.py nao encontrado." >&2
  echo "Procurado em:" >&2
  echo "  $ROOT_DIR/cuma.py" >&2
  echo "  $ROOT_DIR/Repositorio_GitHub/cuma.py" >&2
  echo "  $ROOT_DIR/GitHub/cuma.py" >&2
  exit 1
fi

cd "$SRC_DIR"
mkdir -p "$ZIP_DIR"

if ! command -v python3 >/dev/null 2>&1; then
  echo "[ERRO] Python 3.11+ nao encontrado para compilar." >&2
  exit 1
fi

if [ ! -x ".venv/bin/python" ]; then
  python3 -m venv .venv
fi

source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

rm -rf build dist

echo "Gerando CUMA_linux autocontido..."
python -m PyInstaller --noconfirm cuma_linux.spec

test -x "$OUT_DIR/cuma"
test -x "$OUT_DIR/cuma_updater"

cp -f manual_do_programa.txt "$OUT_DIR/manual_do_programa.txt" 2>/dev/null || true
cp -f LEIA-ME.txt README.md LICENSE "$OUT_DIR/" 2>/dev/null || true
cp -f "NOTAS_RELEASE.md" "AUDITORIA_DEBUG.md" "$OUT_DIR/" 2>/dev/null || true

rm -f "$OUT_DIR"/CUMA.log "$OUT_DIR"/CUMA_update.log "$OUT_DIR"/erro.txt "$OUT_DIR"/debug_completo_cuma.txt "$OUT_DIR"/cuma_settings.json "$OUT_DIR"/config_cuma.json
rm -rf "$OUT_DIR"/.cuma_user_data "$OUT_DIR"/limpos

chmod +x "$OUT_DIR/cuma" "$OUT_DIR/cuma_updater"

rm -f "$TAR_PATH"
tar -C dist -czf "$TAR_PATH" CUMA_linux

python scripts/preparar_manifesto_release.py soldieg CUMA "$APP_VERSION" "$TAR_PATH" Stable "$RELEASE_NOTES" linux || true

echo "OK: $TAR_PATH"
