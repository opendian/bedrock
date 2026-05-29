# Bedrock voice layer — design + run book

A two-direction voice layer for the vault. Local-first, Apple-Silicon native.

- **Voice IN** (`dictate.py`) — a Wispr-style push-to-talk daemon. Speak, get clean text. Default lands **FR** (VOICE §A1: Obsidian thinking → FR only).
- **Voice OUT** (`note_to_audio.py` + the **Bedrock Voice** Obsidian plugin) — Kokoro reads a note back with **real-time karaoke captions inside Obsidian**. Tightened spoken script, **EN** narration (deployed content, VOICE §A7).

**Status (installed + verified):** venv on Python 3.12, Kokoro + MLX Whisper installed, `claude` and `codex` backends both return clean on-voice output, and `note_to_audio.py --captions` produces audio + per-sentence timing from a real note. The plugin is built (`.obsidian/plugins/bedrock-voice/main.js`) and enabled.

> [!warning]
> Two things can only be confirmed by you, in the GUI: (1) the plugin playing audio + painting captions — reload Obsidian, open a note, run **Read note aloud with captions**; (2) the dictation daemon — needs macOS **Microphone + Accessibility** grants before it captures and pastes.

---

## Architecture

```
VOICE IN  (Wispr-like)
  global hotkey ─▶ mic capture ─▶ MLX Whisper ─▶ LLM cleanup ─▶ insert
  (pynput)        (sounddevice)   (large-v3-turbo)  (Claude, reads VOICE.md)   │
                                                                               ├─ "insert" mode → paste at cursor (any app)
                                                                               └─ "note"   mode → write Inbox/<slug>.md w/ frontmatter

VOICE OUT (Kokoro)
  note.md ─▶ strip frontmatter ─▶ LLM tighten to spoken script ─▶ Kokoro TTS ─▶ Sources/audio/<slug>.wav ─▶ embed in note
            (body or tldr+H2)      (Claude, EN per §A7)            (af_heart)    (gitignored)
```

The cleanup and tighten steps **read `VOICE.md` + `CLAUDE.md` at runtime** and pass them as the system context. Edit the contract, the voice layer follows — no code change.

### No metered API — pick a backend (`BEDROCK_LLM_BACKEND`)

| Backend | Auth | Notes |
| --- | --- | --- |
| `claude` *(default)* | your Claude Code subscription (`claude -p`) | Best quality, no key, no download. Runs from a neutral cwd so the vault's CLAUDE.md isn't auto-loaded. |
| `codex` | your Codex/ChatGPT login (`codex exec`) | Same idea via OpenAI's CLI. **Not installed on this machine yet.** |
| `local` | none — fully offline | MLX-LM in-process (`Qwen2.5-3B-Instruct-4bit`). Slower, no network. |

No `ANTHROPIC_API_KEY` anywhere. The CLI backends ride auth you already have.

## The stack (why each piece)

| Need | Choice | Why |
| --- | --- | --- |
| STT | **MLX Whisper** `large-v3-turbo` | Apple-Silicon native (Metal), local, fast, accurate. |
| TTS | **Kokoro** (82M) | Apache-2, runs on CPU, multi-lingual, clean voice. |
| Hotkey | **pynput** | Global key listener without a full native app. |
| Mic | **sounddevice** + **soundfile** | Simple PCM capture to numpy. |
| Menubar | **rumps** | Minimal macOS status-bar app in Python. |
| Cleanup / tighten | **Anthropic SDK** | Applies VOICE live; prompt-caches the contract. |
| Insertion | clipboard + `Cmd+V` via `osascript` | Most robust way to drop arbitrary unicode at the cursor. |
| Cleanup / tighten | `claude -p` CLI (or codex / local MLX-LM) | Applies VOICE live, **no metered API** — uses subscription auth or runs offline. |

> [!note]
> Python is the pragmatic path and matches the existing `Notes/ops/` tooling. The polished long-term upgrade is a small **Swift** menubar app (true hold-to-talk, no Accessibility paste hack). Treat this as v1.

## Install (run when ready — `install.sh`)

```bash
brew install python@3.12 espeak-ng ffmpeg
cd "Notes/ops/voice"
"$(brew --prefix)/bin/python3.12" -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

No `.env` needed for the default `claude` backend. System Python is 3.9 (too old for the modern stack) — the venv pins 3.12 from Homebrew. Skip `mlx-lm` unless you want the offline `local` backend.

### macOS permissions (one-time, required)

System Settings → Privacy & Security →
- **Microphone** → enable your launcher (Terminal / iTerm / the app that runs `dictate.py`).
- **Accessibility** → same launcher (needed to send the synthetic `Cmd+V`).

Without these the daemon records silence and pastes nothing.

## Usage

### Read-along captions in Obsidian (the main event)

Reload Obsidian, open a note, then run **Read note aloud with captions** (command palette or the `audio-lines` ribbon icon). The plugin shells out to `note_to_audio.py --captions`, plays the Kokoro audio, and paints a floating caption HUD that karaoke-highlights each sentence — with word-level highlight inside the sentence — synced to the audio. Space toggles play/pause, Esc closes, the dropdown changes speed. Settings (gear → Bedrock Voice): backend, language, Kokoro voice, default speed, whole-note vs tldr+headers.

### CLI (scripting / debugging)

```bash
source .venv/bin/activate

# Voice OUT — generate audio + timing JSON exactly as the plugin does
python note_to_audio.py "Notes/automatisations.md" --captions
python note_to_audio.py "Notes/x.md"                  # plain: write wav + embed link in note
python note_to_audio.py "Notes/x.md" --lang fr        # FR narration instead of EN
python note_to_audio.py "Notes/x.md" --whole          # whole body, not tldr+H2

# Voice IN — start the dictation daemon (menubar + hotkey)
python dictate.py
# Default hotkey: Ctrl+Alt+D toggles recording. Menubar switches Insert ⇄ Note mode.
```

## Files

| File | Role |
| --- | --- |
| `config.py` | Paths, model IDs, voice, hotkey — all env-overridable. |
| `vault.py` | Loads VOICE/CLAUDE, slugify, frontmatter builder, routing. |
| `llm.py` | `clean_dictation()` (FR) and `tighten_for_speech()` (EN), VOICE-aware, backend-pluggable (claude/codex/local). |
| `dictate.py` | The voice-IN daemon: hotkey → record → Whisper → cleanup → insert/note. |
| `note_to_audio.py` | The voice-OUT pipeline: note → tighten → Kokoro → wav + `--captions` timing JSON. |
| `requirements.txt` | Python deps. |
| `.env.example` | Backend choice + voice/hotkey overrides (no API key). |
| `install.sh` | Homebrew + venv setup. |
| `../../../.obsidian/plugins/bedrock-voice/` | The Obsidian plugin (`main.ts` → `main.js`) — caption HUD + playback. |

## Open decisions / roadmap

- **Hold-to-talk vs toggle.** v1 ships toggle (press to start/stop) — simpler with pynput. Hold-to-talk is cleaner but needs key up/down tracking; flagged for v2.
- **Word-level timing.** Captions interpolate word highlight across each sentence by char count (good enough, no alignment cost). True per-word timestamps via forced alignment is a v2.
- **Backend.** Default `claude` (subscription auth, no key); `codex` verified (uses `--json` to extract the clean message); `local` (MLX-LM) is the offline fallback — same `llm.py` interface, `pip install mlx-lm` to enable.
- **Verbatim read mode.** Today captions show the *tightened spoken script*. An alternative mode that reads the note verbatim and highlights the actual document text is a possible addition.
- **Swift rewrite** for the dictation surface, if v1 proves the workflow.

Next action: reload Obsidian, run **Read note aloud with captions** on a note, then grant Microphone + Accessibility and start `dictate.py`.
