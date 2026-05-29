#!/usr/bin/env bash
# Bedrock Voice — interactive screenshot helper
#
# Usage:
#   bash bin/capture.sh <slug>          # interactive crop, saves docs/screenshots/<slug>.png
#   bash bin/capture.sh hero-hud
#   bash bin/capture.sh caption-detail
#   bash bin/capture.sh ribbon-icon
#   bash bin/capture.sh settings
#
# macOS only (uses /usr/sbin/screencapture).

set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "usage: bash bin/capture.sh <slug>" >&2
  echo "  slug examples: hero-hud, caption-detail, ribbon-icon, settings" >&2
  exit 1
fi

slug="$1"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT_DIR="$ROOT/docs/screenshots"
mkdir -p "$OUT_DIR"
OUT="$OUT_DIR/$slug.png"

echo ""
echo "── $slug ──"
echo "Position the Obsidian window with the scene you want."
echo "Then click-drag to select the region. Esc cancels."
echo ""
read -p "Press Enter when ready... " _

# -i interactive (crosshair), -o no shadow, -t png
/usr/sbin/screencapture -i -o -t png "$OUT"

if [[ -f "$OUT" ]]; then
  size_kb=$(( $(stat -f%z "$OUT") / 1024 ))
  echo "✓ saved $OUT (${size_kb} KB)"
  # Open in Preview for sanity check
  open "$OUT"
else
  echo "✗ no capture (cancelled?)"
  exit 1
fi
