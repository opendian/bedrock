#!/usr/bin/env bash
# Bedrock Voice — one-shot installer.
#
# Run this once after installing the plugin via BRAT:
#   cd "<your-vault>/.obsidian/plugins/bedrock-voice/voice" && bash install.sh
#
# What it does (idempotent — re-runs are safe):
#   1. Verifies macOS Apple Silicon (v0.1 is Apple-Silicon-only).
#   2. Ensures Homebrew is installed (will prompt to install if missing).
#   3. Ensures python@3.12, espeak-ng, ffmpeg via brew.
#   4. Creates .venv/ here, installs Python deps.
#   5. Pre-downloads the Kokoro 82M voice on first run (~300 MB).
#   6. Verifies the pipeline by running `note_to_audio.py --version`.

set -euo pipefail
cd "$(dirname "$0")"

# ── ANSI helpers ───────────────────────────────────────────────────────
if [[ -t 1 ]]; then
  BOLD=$'\033[1m'; DIM=$'\033[2m'; OK=$'\033[32m'; WARN=$'\033[33m'; ERR=$'\033[31m'; OFF=$'\033[0m'
else
  BOLD=""; DIM=""; OK=""; WARN=""; ERR=""; OFF=""
fi
say()  { printf "${BOLD}==>${OFF} %s\n" "$*"; }
ok()   { printf "${OK}✓${OFF} %s\n" "$*"; }
warn() { printf "${WARN}!${OFF} %s\n" "$*"; }
die()  { printf "${ERR}✗${OFF} %s\n" "$*" >&2; exit 1; }

# ── 1. Platform check ──────────────────────────────────────────────────
say "Checking platform"
OS=$(uname -s)
ARCH=$(uname -m)
if [[ "$OS" != "Darwin" ]]; then
  die "Bedrock Voice v0.1 is macOS only. Your system: $OS. Windows + Linux support is on the roadmap — see https://github.com/opendian/bedrock/issues."
fi
if [[ "$ARCH" != "arm64" ]]; then
  warn "Detected $ARCH. Bedrock Voice is tested on Apple Silicon (arm64) only."
  warn "Intel Mac may work for the Kokoro TTS path, but the default 'local' LLM backend (MLX) is Apple-Silicon-only."
  warn "Continuing anyway — you'll likely need to switch the backend to 'claude' or 'codex' in the plugin settings."
  read -rp "Continue? [y/N] " confirm
  [[ "$confirm" =~ ^[Yy]$ ]] || die "Aborted by user."
fi
ok "macOS $(sw_vers -productVersion) on $ARCH"

# ── 2. Homebrew ────────────────────────────────────────────────────────
say "Checking Homebrew"
if ! command -v brew >/dev/null 2>&1; then
  warn "Homebrew not found."
  read -rp "Install Homebrew now? [Y/n] " confirm
  if [[ "$confirm" =~ ^[Nn]$ ]]; then
    die "Homebrew is required. Install from https://brew.sh and re-run this script."
  fi
  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
  # PATH for fresh Homebrew install
  if [[ -x /opt/homebrew/bin/brew ]]; then
    eval "$(/opt/homebrew/bin/brew shellenv)"
  fi
fi
ok "Homebrew $(brew --version | head -1)"

# ── 3. Brew deps ───────────────────────────────────────────────────────
say "Installing Python 3.12 and audio dependencies"
brew install python@3.12 espeak-ng ffmpeg

PY="$(brew --prefix python@3.12)/bin/python3.12"
if [[ ! -x "$PY" ]]; then
  die "Expected Python 3.12 at $PY but didn't find it. Try: brew reinstall python@3.12"
fi
ok "$($PY --version)"

# ── 4. venv + pip ──────────────────────────────────────────────────────
say "Creating Python venv"
if [[ -d .venv ]]; then
  ok ".venv already exists — reusing"
else
  "$PY" -m venv .venv
  ok "Created .venv"
fi

# shellcheck disable=SC1091
source .venv/bin/activate
pip install --upgrade pip --quiet
say "Installing Python deps (this is the slow step — ~2-5 min on first run)"
pip install --quiet -r requirements.txt
ok "Dependencies installed"

# ── 5. Smoke test ──────────────────────────────────────────────────────
say "Smoke-testing the pipeline"
if python -c "import kokoro, soundfile, numpy" 2>/dev/null; then
  ok "Kokoro TTS imports cleanly"
else
  die "Kokoro import failed. Check the pip output above."
fi

if python -c "import mlx_lm" 2>/dev/null; then
  ok "MLX-LM available (default 'local' backend ready)"
else
  warn "MLX-LM not available — the default 'local' backend will fail."
  warn "If you have claude or codex CLI installed, switch in Settings → Bedrock Voice → LLM backend."
fi

# ── 6. Done ────────────────────────────────────────────────────────────
cat <<EOF

${BOLD}${OK}Setup complete.${OFF}

Next steps:
  1. ${BOLD}Reload Obsidian${OFF} (Cmd-R, or close + reopen).
  2. Open any note.
  3. Run ${BOLD}Read note aloud with captions${OFF} from the command palette,
     or click the ${BOLD}audio-lines${OFF} icon in the ribbon.

First read will be slow (~30s) — the local MLX model loads + Kokoro warms up.
Second read of an unchanged note replays from cache instantly.

Backend defaults to 'local' (offline, no API key). If you have ${BOLD}claude${OFF} or
${BOLD}codex${OFF} CLI installed, switch in Settings → Bedrock Voice → LLM backend
for 5-10× faster script tightening.

Issues? https://github.com/opendian/bedrock/issues
Docs:   https://opendian.github.io/bedrock/

EOF
