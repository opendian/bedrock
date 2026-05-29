"""VOICE-aware LLM passes — no metered API. Backends: claude CLI / codex CLI / local MLX-LM.

The contract (VOICE.md + CLAUDE.md) is passed inline as the system context. CLI backends run
from a neutral cwd so the vault's CLAUDE.md is NOT auto-loaded (which would append a ✓ flag).
"""
import json
import os
import re
import shutil
import subprocess
import tempfile

import config
from vault import load_contract

_NEUTRAL_CWD = tempfile.gettempdir()

# GUI apps (Obsidian launched from the Dock) get a minimal PATH that omits these.
# claude/codex live here, and claude (a Node app) needs node reachable too.
_BIN_DIRS = [
    os.path.expanduser("~/.local/bin"),
    "/opt/homebrew/bin",
    "/usr/local/bin",
    "/usr/bin",
    "/bin",
]


def _cli_env():
    env = dict(os.environ)
    env["PATH"] = os.pathsep.join(_BIN_DIRS) + os.pathsep + env.get("PATH", "")
    return env


def _resolve(binary):
    return shutil.which(binary, path=_cli_env()["PATH"]) or binary
# CLAUDE.md's flag system (🜂🜁🜃✓) is for interactive turns — strip it from machine output.
_FLAG_RE = re.compile(r"\s*[🜂🜁🜃✓]+\s*$")


def _strip_flags(text):
    return _FLAG_RE.sub("", text).strip()


def _contract():
    voice, claude = load_contract()
    return (
        "You are the voice layer for Yani Meziani's Bedrock Vault. Apply this contract exactly. "
        "Output ONLY the requested artifact — no preamble, no closing remarks. "
        "The CLAUDE.md flag system (🜂🜁🜃✓) and command protocol do NOT apply here: emit no flag.\n\n"
        "=== VOICE.md ===\n" + voice +
        "\n\n=== CLAUDE.md (routing + frontmatter) ===\n" + claude
    )


def _full_prompt(instruction, content):
    return f"{_contract()}\n\n# TASK\n{instruction}\n\n# INPUT\n{content}"


# ── backends ───────────────────────────────────────────────────────────
def _run_claude(instruction, content):
    cmd = [_resolve("claude"), "-p", "--output-format", "text"]
    if config.CLAUDE_MODEL:
        cmd += ["--model", config.CLAUDE_MODEL]
    r = subprocess.run(cmd, input=_full_prompt(instruction, content),
                       text=True, capture_output=True, cwd=_NEUTRAL_CWD, check=True,
                       env=_cli_env())
    return r.stdout.strip()


def _run_codex(instruction, content):
    # --json gives structured events; the answer is the last agent_message item.
    cmd = [_resolve("codex"), "exec", "--json", "--color", "never", "--skip-git-repo-check"]
    if config.CODEX_MODEL:
        cmd += ["--model", config.CODEX_MODEL]
    cmd += [_full_prompt(instruction, content)]
    r = subprocess.run(cmd, input="", text=True, capture_output=True,
                       cwd=_NEUTRAL_CWD, check=True, env=_cli_env())
    msg = ""
    for line in r.stdout.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        item = event.get("item", {})
        if event.get("type") == "item.completed" and item.get("type") == "agent_message":
            msg = item.get("text", msg)
    if not msg:
        raise RuntimeError("codex returned no agent_message")
    return msg


_mlx = None


def _run_local(instruction, content):
    global _mlx
    from mlx_lm import load, generate
    if _mlx is None:
        _mlx = load(config.LLM_MODEL)
    model, tok = _mlx
    messages = [
        {"role": "system", "content": _contract()},
        {"role": "user", "content": f"# TASK\n{instruction}\n\n# INPUT\n{content}"},
    ]
    prompt = tok.apply_chat_template(messages, add_generation_prompt=True, tokenize=False)
    return generate(model, tok, prompt=prompt, max_tokens=config.LLM_MAX_TOKENS, verbose=False).strip()


_BACKENDS = {"claude": _run_claude, "codex": _run_codex, "local": _run_local}


def _run(instruction, content):
    fn = _BACKENDS.get(config.LLM_BACKEND)
    if fn is None:
        raise ValueError(f"unknown BEDROCK_LLM_BACKEND: {config.LLM_BACKEND}")
    return _strip_flags(fn(instruction, content))


# ── tasks ──────────────────────────────────────────────────────────────
def clean_dictation(raw, mode="raw"):
    """Clean a dictated transcript. FR (operating language, VOICE §A1).

    mode 'raw'  -> cleaned prose only (for insert-at-cursor).
    mode 'note' -> body for a vault note (thesis, refutation, atomic H2s).
    """
    if mode == "note":
        instruction = (
            "Transforme cette transcription dictée en corps de note FR pour le coffre. "
            "Enlève hésitations, faux départs, répétitions. "
            "Structure: une ligne de thèse, une refutation en gras (§A2), des H2 atomiques si la matière s'y prête. "
            "Wikilinks sur les noms, jamais les verbes. Dernier mot = un verbe (§A10.5). "
            "N'invente aucun fait, chiffre, produit, date. Ne résume pas."
        )
    else:
        instruction = (
            "Nettoie cette transcription dictée en prose FR que Yani écrirait. "
            "Enlève 'euh', faux départs, répétitions. Ponctuation correcte. Rythme §A3, zéro hedge (§A11). "
            "N'ajoute rien, ne résume pas. Renvoie seulement le texte nettoyé."
        )
    return _run(instruction, raw)


def tighten_for_speech(note_body, target_lang="en"):
    """Rewrite a note body into a 60-90s spoken script."""
    lang_clause = (
        "Rewrite (do not machine-translate) into English using the EN cadence in §A7."
        if target_lang == "en"
        else "Garde le français (§A7 FR)."
    )
    instruction = (
        "Turn this note into a spoken script of 60-90 seconds, meant to be heard, not read. "
        + lang_clause +
        " Strip all Markdown and wikilink syntax — say the names plainly. Expand abbreviations. "
        "Short sentences, one idea each (§A3). Open on the reframe (§A2), end on a verb (§A10.5). "
        "No stage directions, no host names, no 'welcome back'. Output only the words to speak."
    )
    return _run(instruction, note_body)
