"""Bedrock voice layer — shared config. All knobs are env-overridable (.env)."""
from pathlib import Path
import os

try:
    from dotenv import load_dotenv
    # config.py lives at Notes/ops/voice/config.py
    load_dotenv(Path(__file__).with_name(".env"))
except Exception:
    pass

# Vault root = Notes/ops/voice/ -> up 3
VAULT_ROOT = Path(__file__).resolve().parents[3]
VOICE_MD = VAULT_ROOT / "VOICE.md"
CLAUDE_MD = VAULT_ROOT / "CLAUDE.md"
INBOX = VAULT_ROOT / "Inbox"
NOTES = VAULT_ROOT / "Notes"
QUOTIDIEN = VAULT_ROOT / "Quotidien"
AUDIO_OUT = VAULT_ROOT / "Sources" / "audio"   # gitignored

# Models — all local, no network.
WHISPER_MODEL = os.environ.get("BEDROCK_WHISPER", "mlx-community/whisper-large-v3-turbo")
KOKORO_LANG = os.environ.get("BEDROCK_KOKORO_LANG", "a")        # a = US English
KOKORO_VOICE = os.environ.get("BEDROCK_KOKORO_VOICE", "af_heart")
# LLM backend — no metered API key. One of:
#   claude  -> `claude -p` CLI, your Claude Code subscription auth (default, best quality)
#   codex   -> `codex exec` CLI, your Codex/ChatGPT subscription auth
#   local   -> MLX-LM in-process, fully offline, no auth
LLM_BACKEND = os.environ.get("BEDROCK_LLM_BACKEND", "claude")
CLAUDE_MODEL = os.environ.get("BEDROCK_CLAUDE_MODEL", "")   # "" = CLI default
CODEX_MODEL = os.environ.get("BEDROCK_CODEX_MODEL", "")     # "" = CLI default
# Local (MLX-LM) only. 3B-4bit fits an 8GB device; bump to Qwen2.5-7B-Instruct-4bit if RAM allows.
LLM_MODEL = os.environ.get("BEDROCK_LLM_MODEL", "mlx-community/Qwen2.5-3B-Instruct-4bit")
LLM_MAX_TOKENS = int(os.environ.get("BEDROCK_LLM_MAX_TOKENS", "1200"))

# Audio / dictation
SAMPLE_RATE = 16000     # Whisper expects 16 kHz mono
KOKORO_SR = 24000       # Kokoro output rate
HOTKEY = os.environ.get("BEDROCK_HOTKEY", "<ctrl>+<alt>+d")
