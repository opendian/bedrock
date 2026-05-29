"""Bedrock Voice — shared config. All knobs are env-overridable (.env).

Vault root detection
--------------------
The plugin sets BEDROCK_VAULT_ROOT to the active vault path on every invocation
(plugin/main.ts), which is the authoritative source. The fallback below only
fires for direct CLI usage, where it walks upward from this file until it
finds a `.obsidian/` folder — the unambiguous marker of an Obsidian vault.
"""
from pathlib import Path
import os

try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).with_name(".env"))
except Exception:
    pass


def _detect_vault_root() -> Path:
    env = os.environ.get("BEDROCK_VAULT_ROOT")
    if env:
        return Path(env).resolve()
    # Walk up from this file looking for .obsidian/
    cur = Path(__file__).resolve().parent
    for parent in [cur, *cur.parents]:
        if (parent / ".obsidian").is_dir():
            return parent
    # Last-ditch fallback: the parent of the plugin folder
    # (covers .obsidian/plugins/<plugin>/voice/ -> .obsidian/.. -> vault root)
    return Path(__file__).resolve().parents[4] if len(Path(__file__).resolve().parents) >= 5 else Path.cwd()


VAULT_ROOT = _detect_vault_root()
VOICE_MD = VAULT_ROOT / "VOICE.md"
CLAUDE_MD = VAULT_ROOT / "CLAUDE.md"
INBOX = VAULT_ROOT / "Inbox"
NOTES = VAULT_ROOT / "Notes"
QUOTIDIEN = VAULT_ROOT / "Quotidien"
# Audio output — keep it inside .obsidian/plugins/bedrock-voice/audio/ by default
# so the user's note tree stays clean. Override with BEDROCK_AUDIO_OUT.
_audio_default = Path(__file__).resolve().parent.parent / "audio"
AUDIO_OUT = Path(os.environ.get("BEDROCK_AUDIO_OUT", str(_audio_default)))

# Models — all local, no network.
WHISPER_MODEL = os.environ.get("BEDROCK_WHISPER", "mlx-community/whisper-large-v3-turbo")
KOKORO_LANG = os.environ.get("BEDROCK_KOKORO_LANG", "a")        # a = US English
KOKORO_VOICE = os.environ.get("BEDROCK_KOKORO_VOICE", "af_heart")
KOKORO_SR = 24000       # Kokoro output rate

# ── LLM backend ────────────────────────────────────────────────────────
# Default = `local` (MLX-LM, fully offline, no auth required).
# This is the honest "no API key" path.
#
# Opt-in alternatives if you already have them installed:
#   claude  -> Claude Code CLI (subscription auth, 1-4s tightening)
#   codex   -> OpenAI Codex CLI (subscription auth, 0.5-2s tightening)
#   local   -> MLX-LM in-process (default, 8-20s tightening, $0)
LLM_BACKEND = os.environ.get("BEDROCK_LLM_BACKEND", "local")
CLAUDE_MODEL = os.environ.get("BEDROCK_CLAUDE_MODEL", "")
CODEX_MODEL = os.environ.get("BEDROCK_CODEX_MODEL", "")
# Local (MLX-LM). 3B-4bit fits an 8GB device; bump to Qwen2.5-7B-Instruct-4bit if RAM allows.
LLM_MODEL = os.environ.get("BEDROCK_LLM_MODEL", "mlx-community/Qwen2.5-3B-Instruct-4bit")
LLM_MAX_TOKENS = int(os.environ.get("BEDROCK_LLM_MAX_TOKENS", "1200"))

# Dictation (voice IN) — unrelated to the read-aloud pipeline.
SAMPLE_RATE = 16000
HOTKEY = os.environ.get("BEDROCK_HOTKEY", "<ctrl>+<alt>+d")
