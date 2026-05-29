# Architecture

A short tour of how Bedrock Voice is structured and the trade-offs behind it.

## The two halves

```
┌────────────────────────────────┐         ┌─────────────────────────────────┐
│  Obsidian Plugin (TypeScript)  │         │   Voice Pipeline (Python)        │
│  ─────────────────────────     │  exec   │   ─────────────────────────      │
│  - Ribbon icon                 │ ──────▶ │   - Read note + frontmatter      │
│  - Command palette             │         │   - Extract spoken source        │
│  - Caption HUD (DOM)           │ stdout  │   - Tighten via LLM CLI          │
│  - Settings UI                 │ ◀────── │   - Synthesize with Kokoro       │
└────────────────────────────────┘  JSON   │   - Return {wav,lang,segments}   │
                                           └─────────────────────────────────┘
                                                          │
                                                          ▼
                                                  Sources/audio/<slug>.wav
                                                  Sources/audio/<slug>.captions.json
```

The plugin is a thin shell. All heavy work (LLM call, TTS synthesis, audio writing) happens in Python. The plugin only:

1. Picks the active note.
2. Resolves the voice pipeline path.
3. Spawns `python note_to_audio.py <note> --captions --lang <lang> [--whole]`.
4. Parses the JSON payload from stdout.
5. Plays the audio and paints the HUD.

This split keeps the plugin small and lets the pipeline evolve (new TTS backends, new languages) without touching the Obsidian-facing code.

## The JSON contract

The pipeline writes a single line of JSON to stdout (and a `.captions.json` sidecar to disk):

```json
{
  "wav": "/abs/path/to/Sources/audio/<slug>.wav",
  "lang": "en",
  "whole": false,
  "segments": [
    { "text": "First sentence here.", "start": 0.0, "end": 2.31 },
    { "text": "Second sentence.", "start": 2.31, "end": 3.78 }
  ]
}
```

The plugin scans stdout from the end for the last line starting with `{` so library warnings printed earlier don't break parsing.

## Why two languages?

Python because Kokoro, MLX, and Whisper have first-class Python bindings; the bindings barely exist in TypeScript. TypeScript because Obsidian plugins are TypeScript.

A pure-Node implementation is possible (and would simplify install) but would require:
- Compiling Kokoro to ONNX and shipping a Node runtime
- Reimplementing the LLM CLI bridges
- Losing MLX support

That's a 5× larger codebase for a marginally simpler install. The split stands.

## Caching

Per-note caching lives in `voice/note_to_audio.py` (function `cached_payload`). The check is:

1. Does the WAV exist?
2. Does the captions sidecar exist?
3. Is the *older* of the two newer than the note's mtime?
4. Does the cached `lang` match the requested `lang`?
5. Does the cached `whole` match the requested `whole`?

All five must be true for a cache hit. On hit, the pipeline reads the sidecar and prints it back — no LLM call, no Kokoro synthesis. The plugin sees identical-shape JSON either way and behaves the same.

This means: clicking "Read note aloud" twice on an unchanged note is instant. Editing the note → next click regenerates. Changing language or toggling whole-note → next click regenerates.

## Why no metered API

The LLM "tightening" step (compressing the note into a clean spoken script) is the only LLM call in the pipeline. It happens once per cache-miss read. Most TTS plugins make this a per-character API call to a hosted TTS — which is what makes them expensive at scale.

Three backends avoid this:

- **`claude`** — invokes `claude -p "<system>" "<input>"`. If you have a Claude Code subscription you're already paying for, this is $0 marginal.
- **`codex`** — invokes `codex exec --json`. Same idea, OpenAI ChatGPT subscription auth.
- **`local`** — loads an MLX model in-process. Slower, fully offline, no auth.

The Kokoro TTS itself is always local and always free.

## Why a HUD instead of inline transcripts

Inline captions inside the editor (a popular pattern in IDE TTS tools) conflict with Obsidian's editor model — you'd need to inject decorations into either Live Preview or Source mode, and re-paint them on every audio frame. That's a lot of integration surface for a feature that's also worse for the user, who has to look at the same text twice.

The floating HUD:
- Lives outside the editor (one `<div>` appended to `document.body`).
- Works identically in any editor mode, any note, any device.
- Lets the user keep reading the source text underneath at their own pace.

## Performance budget

Per cache-miss read on an M2 Mac:

- LLM tightening: 1–4s (`claude` CLI), 0.5–2s (`codex`), 8–20s (`local`).
- Kokoro synthesis: ~0.6× real-time per sentence (a 2-minute note synthesizes in ~75s).
- Plugin overhead: <50ms (Python startup is the dominant constant).

Per cache hit: <500ms total (mostly Python startup). The plugin shows "preparing audio…" but it's gone almost immediately.

## Where to add code

| Want to… | Edit… |
| --- | --- |
| Add a new playback feature | `plugin/main.ts` `CaptionHud` class |
| Add a new LLM backend | `voice/llm.py` |
| Change what text gets narrated | `voice/note_to_audio.py` `extract_source` |
| Add a new language | `voice/config.py` `KOKORO_LANG` mapping + `voice/llm.py` system prompts |
| Add a new setting | `plugin/main.ts` `BedrockVoiceSettings` + the `display()` method |
