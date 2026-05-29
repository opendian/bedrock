# Bedrock Voice

> **An accessibility-first reading companion for your second brain.**
>
> Bedrock Voice reads your Obsidian notes aloud — with karaoke captions that highlight each word as it's spoken. Built for ADHD, dyslexia, auditory processing, and anyone trying to actually *finish* what they wrote down. Runs locally on your Mac. No metered API. No notes leave your machine.

[![License: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Accessibility](https://img.shields.io/badge/accessibility-first-success.svg)](docs/ACCESSIBILITY.md)
[![Built with Kokoro](https://img.shields.io/badge/TTS-Kokoro%2082M-purple.svg)](https://huggingface.co/hexgrad/Kokoro-82M)
[![Apple Silicon](https://img.shields.io/badge/Apple%20Silicon-native-black.svg)](#)
[![No API Key](https://img.shields.io/badge/API%20key-none-green.svg)](#why-this-stays-on-your-machine)

<p align="center">
  <a href="docs/screenshots/hero.mp4">
    <img src="docs/screenshots/hero.gif" alt="Bedrock Voice reading an Obsidian note aloud with karaoke captions highlighting each word as it's spoken" width="720" />
  </a>
  <br/>
  <sub><i>Click the GIF for the high-res MP4. The plugin runs at the speed and quality shown.</i></sub>
</p>

---

## Why this exists

If you have ADHD, dyslexia, an auditory processing difference, or you just live in 2026 with too many notes — reading the things you wrote down can be the hardest part of having written them.

Bedrock Voice is built around one observation: **bi-modal reading** (seeing a word + hearing it at the same moment) is one of the most-studied, lowest-tech accessibility interventions there is. It's the foundation of [Bookshare](https://www.bookshare.org/), [Kurzweil 3000](https://www.kurzweiledu.com/products/kurzweil-3000.html), [Speechify](https://speechify.com), and a generation of school-library reading tools — but those are SaaS, locked-in, expensive, and not built for the way you actually take notes.

This is the same idea, opinionated for Obsidian, **local-first**, free as in MIT.

---

## What it does

- **Reads any note aloud** with a clean local voice (Kokoro 82M, Apache-2).
- **Karaoke captions** float over Obsidian, highlighting the current word and current sentence as they're spoken.
- **Tightens the spoken script** with an LLM pass first — your note as cadence, not as raw text-dump.
- **Caches everything** — clicking the read button twice on an unchanged note replays the existing audio instantly. Edit the note → next click regenerates.

<p align="center">
  <img src="docs/screenshots/caption-detail.png" alt="Word-level highlight on the active sentence with the next sentence previewed below" width="640" />
</p>

## Who it's for

| If you… | …this is for you |
| --- | --- |
| Have **ADHD** and lose the thread re-reading your own notes | Hearing + seeing simultaneously cuts attention drift. Audio anchors the eyes. |
| Are **dyslexic** | The karaoke pattern is the canonical dyslexia accommodation. This puts it on your second brain. |
| Have an **auditory processing** difference | Self-paced playback (0.75× – 1.75×), Space to pause anytime, no autoplay surprise. |
| Are **autistic** and need predictable pacing | No notifications, no ambient sounds, no animation beyond the highlight. |
| Have **screen fatigue** or eye strain | Look away. Keep listening. The note keeps reading. |
| Are **overwhelmed by your own vault** | Audio while walking, cooking, commuting. The notes you wrote to think become the notes you listen to remember. |
| Are **multilingual** (the project author is FR + EN) | English narration is rewritten for spoken cadence. French stays French. |

Bedrock Voice doesn't pretend to be a clinical tool. It's a thoughtful default — the small accessibility win that should have been built into every note app from day one.

---

## How it works

```
Obsidian note ──▶ Plugin (TS) ──▶ Python pipeline ──▶ Karaoke HUD
                                  │
                                  ├─ Extract source (tldr + H2, or whole body)
                                  ├─ Tighten for speech (Claude/Codex CLI, or local MLX)
                                  ├─ Synthesize sentence-by-sentence (Kokoro)
                                  └─ Return wav + per-sentence timing JSON
```

The plugin shells out to a small Python pipeline. The pipeline does the work and returns a JSON payload the plugin uses to drive the audio and the HUD. The audio file and the sentence timings are cached on disk next to your vault — no recompute when nothing changed.

For the technical architecture, see [docs/architecture.md](docs/architecture.md).

---

## Accessibility design choices

These aren't features tacked on — they're the spine of the project. Full notes in [docs/ACCESSIBILITY.md](docs/ACCESSIBILITY.md).

- **Bi-modal by default.** Audio is always paired with synced visual highlight. Not one or the other.
- **Self-paced playback.** 0.75× through 1.75× without re-synthesizing.
- **Keyboard-first controls.** Space to toggle, Escape to close. No mouse hunt.
- **No autoplay surprise.** Audio only starts when you explicitly trigger the read command.
- **Predictable HUD.** Same position, same size, no animation beyond the word highlight.
- **High-contrast captions.** Honors your Obsidian theme; falls back to readable defaults.
- **No notification sounds.** Ever.
- **Cache-first.** A second click on an unchanged note replays instantly — no waiting penalty.
- **Local TTS.** Sensitive personal notes never leave your machine.

---

## Install

> **Requirements:** macOS (Apple Silicon strongly preferred). Obsidian desktop. Windows + Linux are on the roadmap.

### 1. Install the plugin

Until it's on the community plugin list, use [BRAT](https://github.com/TfTHacker/obsidian42-brat):

1. Install BRAT from Obsidian community plugins.
2. BRAT settings → "Add Beta Plugin" → paste `yanimeziani/bedrock-voice`.
3. Enable **Bedrock Voice** under Community plugins.

Or manually — download `main.js`, `manifest.json`, `styles.css` from [Releases](https://github.com/yanimeziani/bedrock-voice/releases/latest) and drop them into `<your-vault>/.obsidian/plugins/bedrock-voice/`.

### 2. Install the voice pipeline

A small Python pipeline ships inside the plugin folder under `voice/`. One-time setup:

```bash
brew install python@3.12 espeak-ng ffmpeg
cd "<your-vault>/.obsidian/plugins/bedrock-voice/voice"
bash install.sh
```

The first run downloads the Kokoro 82M voice (~300MB), once.

### 3. Pick a backend (optional)

By default Bedrock Voice uses the `claude` CLI to tighten the spoken script. If you don't have Claude Code installed, switch in Settings → Bedrock Voice → LLM backend:

- **`codex`** — Uses the OpenAI Codex CLI (same auth model).
- **`local`** — Fully offline. MLX-LM with a small model. `pip install mlx-lm` inside the voice venv.

All three avoid metered API calls — see [Why this stays on your machine](#why-this-stays-on-your-machine).

---

## Usage

<p align="center">
  <img src="docs/screenshots/ribbon-icon.png" alt="The audio-lines ribbon icon in Obsidian's left sidebar" width="160" />
</p>

- **Ribbon icon** (`audio-lines`) or **command palette** → "Read note aloud with captions".
- **Spacebar** — toggle play / pause.
- **Escape** — close the caption HUD.
- **Speed dropdown** — 0.75× through 1.75×, no re-synthesis.
- **"Stop reading"** command — hard stop mid-sentence.

The HUD floats over your note. The current sentence is foregrounded; the next sentence previews underneath. Each word lights up as it's spoken.

---

## Settings

| Setting | What it does |
| --- | --- |
| **LLM backend** | `claude` / `codex` / `local`. All three avoid metered APIs. |
| **Narration language** | English (rewritten for cadence) or French (kept French). |
| **Kokoro voice** | Default `af_heart`. See [Kokoro voices](https://huggingface.co/hexgrad/Kokoro-82M#voices). |
| **Default speed** | Playback rate, 0.75× – 1.75×. |
| **Read whole note** | Off: `tldr` frontmatter + H2 headers. On: the full body. |
| **Voice pipeline path** | Where the Python pipeline lives. Empty = bundled `<plugin>/voice/`. |

---

## Why this stays on your machine

Most TTS plugins use a hosted API (ElevenLabs, OpenAI, Cartesia). That model is:

- **Expensive** — pennies per minute add up fast on a daily-use vault.
- **Privacy-leaky** — every note you read goes to a third-party server.
- **Lock-in** — your TTS history isn't yours.

Bedrock Voice was built for a personal vault where every read shouldn't tick a meter — and where notes about your finances, therapy, code, or family don't belong on someone else's server.

| Component | Where it runs | What it costs |
| --- | --- | --- |
| TTS (Kokoro 82M) | Locally, on your CPU | $0 |
| Script tightening (`claude`) | Via Claude Code CLI auth (subscription) | $0 marginal |
| Script tightening (`codex`) | Via OpenAI Codex CLI auth (subscription) | $0 marginal |
| Script tightening (`local`) | MLX-LM in-process | $0 (offline) |

No `ANTHROPIC_API_KEY`. No `OPENAI_API_KEY`. No `ELEVENLABS_API_KEY`. Nothing ticks.

---

## Roadmap

- [x] Cache audio + captions on note mtime
- [x] Configurable voice pipeline path
- [ ] **Submit to Obsidian community plugins**
- [ ] **Windows + Linux testing**
- [ ] **Per-word timestamps** via forced alignment (currently char-interpolated within sentence)
- [ ] **Dyslexia-friendly font option** for the HUD (OpenDyslexic, Atkinson Hyperlegible)
- [ ] **Background ambient reading mode** — read selection without HUD
- [ ] **Read selection** instead of whole note / TLDR
- [ ] **Anki + Readwise export**
- [ ] **More languages** (Kokoro supports several)

Issues and pull requests welcome. See [CONTRIBUTING.md](CONTRIBUTING.md).

---

## Repository layout

```
bedrock-voice/
├── plugin/            TypeScript Obsidian plugin
├── voice/             Python pipeline (Kokoro + LLM tightening)
├── docs/
│   ├── architecture.md       How the pieces fit together
│   ├── ACCESSIBILITY.md      Design choices in detail
│   └── screenshots/          Hero + feature images
├── .github/workflows/  CI: build + release
├── LICENSE             MIT
└── README.md           This file
```

---

## Acknowledgements

- [**Kokoro 82M**](https://huggingface.co/hexgrad/Kokoro-82M) by hexgrad. This whole project sits on this voice.
- [**MLX**](https://github.com/ml-explore/mlx) by Apple. Native-on-Silicon inference, no fuss.
- [**Obsidian**](https://obsidian.md) — the canvas this is painted onto.
- Everyone who's ever asked their note app to read something out loud and gotten back robot voice + no highlight + a bill.

---

## License

MIT. See [LICENSE](LICENSE).

— [Yani Meziani](https://meziani.org)
