#!/usr/bin/env bash
set -euo pipefail
SRC_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
DEST="$HOME/.hermes/skills/book-to-skill"
mkdir -p "$DEST"
cp -R "$SRC_DIR/book-to-skill/"* "$DEST/"
chmod +x "$DEST/scripts/extract.py"
echo "Installed: $DEST"
