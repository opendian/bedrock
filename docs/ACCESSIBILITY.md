# Accessibility design

Bedrock Voice is built around the idea that **bi-modal reading** — hearing a word at the exact moment you see it — is one of the most-studied, lowest-tech accessibility wins available. The whole UX exists to deliver that one moment cleanly, with controls that respect the user's pace, attention, and privacy.

This document captures the design choices and the *why* behind them. It's also a contract: changes to the plugin that erode any of these defaults need explicit discussion in a PR.

---

## Founding principles

### 1. Bi-modal by default

The synced sentence + word-level highlight is not a bonus feature — it is the product. Audio without highlight is just TTS. Highlight without audio is just the editor. The pairing is what makes this useful for dyslexia, ADHD, and auditory processing differences.

> Research: Stanovich (1986), Ehri (2005), and the [Bookshare](https://www.bookshare.org/) clinical lit have shown bi-modal reading improves comprehension and reduces reading fatigue for dyslexic readers. The karaoke pattern is the canonical implementation.

### 2. Self-paced, never auto

Audio only starts when the user explicitly triggers the read command. The plugin never autoplays anything, never re-opens on its own, never starts mid-task. Playback speed is user-selectable (0.75× through 1.75×) without re-synthesizing — you can slow down for a complex sentence and speed back up.

### 3. Keyboard-first

Every control is reachable from the keyboard:

- **Space** — toggle play / pause
- **Escape** — close the HUD
- Speed dropdown is keyboard-focusable

No mouse hunt. No hidden gestures. The plugin honors Obsidian's focus mode and other keyboard-driven workflows.

### 4. Predictable HUD

The caption HUD is the same shape, same position, same color every time. The only motion is the word highlight advancing through the current sentence. No fade-in, no animation, no zoom, no parallax. People with autism, vestibular sensitivities, or motion-triggered migraines need this — and everyone else benefits from it too.

### 5. No notification sounds

Ever. The narration is the only sound the plugin makes.

### 6. Honors theme contrast

Caption colors come from your Obsidian theme variables (`--text-normal`, `--text-muted`, `--text-accent`). High-contrast themes stay high-contrast. Dark themes stay dark.

### 7. Cache-first, no waiting penalty

The first read of a note runs the LLM + Kokoro pipeline (~10-30s). Subsequent reads of the same unchanged note replay from disk in under half a second. If you're using audio as a re-reading aid (which is the dyslexic / ADHD pattern), the second time is free.

### 8. Privacy-respecting

Local TTS. Local cache. The LLM tightening pass runs through a CLI tool you've already authenticated, or fully offline. Notes about your therapy, finances, or family don't leave your machine.

---

## Trade-offs we accepted

### TTS quality vs. local-only

Kokoro 82M sounds good, but not ElevenLabs-good. We chose local + free + private over hosted + premium. Voices will keep improving in this size class.

### Sentence-level timing vs. word-level

Real per-word timestamps require forced alignment (Whisper + audio re-pass). That's a ~30% performance hit on synth time for a marginal UX gain — the current char-interpolated word highlight is good enough for the bi-modal effect. Forced alignment is on the roadmap for when it can run without that cost.

### Single voice per session

You can change voice in settings, but you can't switch mid-playback. The cache key would explode. Restart the HUD with a new voice if you need to.

### macOS-first

Kokoro runs on any OS, but the Apple Silicon path is what we've tested. Windows and Linux are roadmap items, not v0.1 commitments.

---

## On the roadmap (accessibility-flavored)

- **OpenDyslexic / Atkinson Hyperlegible font option** for the HUD captions, opt-in in settings.
- **Read-selection-only** mode — narrate just the highlighted text, leave the rest alone.
- **Ambient mode** — read a note in the background with no HUD, for when you want pure audio.
- **Pronunciation overrides** — fix words Kokoro mangles (names, acronyms, technical terms) without rewriting the source note.
- **Background TTS for whole folders** — queue a folder of notes for sequential reading, podcast-style.

If you have lived-experience input on what would help you specifically, please [open an issue](https://github.com/opendian/bedrock/issues). The roadmap above is a guess; your feedback corrects it.

---

## What we are NOT

- We are not a screen reader. Use VoiceOver / NVDA / Orca for OS-level reading. Bedrock Voice is for the note content specifically.
- We are not a clinical tool. We make no claims about therapeutic outcomes.
- We are not a substitute for accommodations. If you need formal accessibility support at school or work, get a real assessment.

We're a thoughtful default for note-taking. That's the whole pitch.

---

## How to contribute accessibility improvements

Open an issue tagged `accessibility`. Describe:

1. **Your context** — what neurodiverse profile, accommodation, or use case you're working from.
2. **The friction** — what specifically gets in the way.
3. **What you'd want instead** — even a rough sketch.

We'll prioritize accessibility issues above feature requests. Always.

— [Yani Meziani](https://meziani.org)
