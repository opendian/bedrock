#!/usr/bin/env bash
# Bedrock voice layer — install. Run manually when ready.
set -euo pipefail
cd "$(dirname "$0")"

echo "==> Homebrew deps (python@3.12, espeak-ng, ffmpeg)"
brew install python@3.12 espeak-ng ffmpeg

PY="$(brew --prefix)/bin/python3.12"
echo "==> venv via $PY"
"$PY" -m venv .venv
# shellcheck disable=SC1091
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

cat <<'EOF'

Done. No API key required — the default backend uses your `claude` CLI subscription auth.

One manual step remains — System Settings > Privacy & Security:
  - Microphone    -> enable your terminal/launcher
  - Accessibility -> enable your terminal/launcher   (for Cmd+V insertion)

Backend (optional): set BEDROCK_LLM_BACKEND in .env to codex or local. Default is claude.

Smoke test:
  source .venv/bin/activate
  python note_to_audio.py "Notes/<some-note>.md"   # voice OUT
  python dictate.py                                 # voice IN daemon
EOF
