# Changelog

All notable changes to Bedrock Voice are tracked here. Versioning follows [SemVer](https://semver.org).

## [Unreleased]

## [0.1.1] — 2026-05-29

This is the first reliable release. v0.1.0 shipped with a launch-critical regression in `extract_source` that caused the audio narration to drift from — or completely fabricate — content for any note with structural H2 headings. v0.1.1 fixes the extraction, pins macOS Apple Silicon as the supported platform, makes the fully-offline `local` LLM backend the honest default, and shrinks install to one command.

### Added
- `voicePath` setting to point the plugin at a non-bundled Python pipeline location (vault-relative or absolute). Default: bundled `<plugin>/voice/`.
- Smart cache: audio + captions are reused when the source note has not been edited since the last generation. Cache key includes `lang` and `whole` flags.
- "Show pipeline install instructions" command + modal with a copyable terminal command. Surfaces automatically when the pipeline isn't installed yet.
- `voice/audit_audio.py` — audit script that maps every cached audio back to its source note and reports drift, hallucination heat, coverage gaps, and stale cache.
- `.github/workflows/extract.yml` — 8 fixture cases asserting `extract_source` produces faithful output across frontmatter key variants, H2-with-body, markdown noise, and fallback paths.
- `docs/audit-2026-05.md` — public retrospective on the regression that motivated the v0.1.1 extract rewrite.
- `TROUBLESHOOTING.md` — 12 most-likely launch issues with deterministic fixes.
- HUD accessibility hardening: `role="region"`, `aria-live="polite"` (debounced per sentence), focus management on open, 44px minimum button target, four-channel active-word signal (color + weight + underline + glow) so colour-blind and reduced-motion users still see it. `@media (prefers-reduced-motion: reduce)` strips animation. `@media (forced-colors: active)` maps to Windows High Contrast system colors.

### Changed
- **Default LLM backend is now `local` (MLX-LM), not `claude`.** The `local` backend is fully offline with no auth required — the honest "no API key" path. `claude` and `codex` remain as opt-in faster alternatives for users who already have those CLIs.
- **Install shrunk to one command** (after BRAT): `cd "<vault>/.obsidian/plugins/bedrock-voice/voice" && bash install.sh`. The installer now verifies platform, installs Homebrew (with confirmation) if missing, all Python deps including MLX-LM, and smoke-tests the pipeline.
- `extract_source` now reads `tldr` / `gist` / `summary` / `description` from frontmatter (first match wins). Collects heading + first ~80 words of body per `## H2` section, stripping markdown noise (wikilinks, inline code, H3 markers, list markers, blockquotes, HTML). Whole-body fallback still triggers when no structural content is found.
- `config.py` now auto-detects `VAULT_ROOT` by walking upward looking for `.obsidian/`. Plugin sets `BEDROCK_VAULT_ROOT` env var on every invocation as the authoritative source.
- Default audio output moved to `<plugin>/audio/` (was tied to `<vault>/Sources/audio/`, which only made sense in the dev vault).
- Plugin notice message simplified: "preparing audio (backend)…" — the new cache layer often makes this near-instant.
- Pipeline writes `whole` flag into the captions sidecar so the cache invalidates correctly when the user toggles "Read whole note".

### Fixed
- **`extract_source` no longer narrates the wrong content.** v0.1.0 collected only H2 *labels* and looked solely for `tldr:`. Notes with structural H2s — book gems, distilled livre notes, setup guides — fell into a hole where the LLM tightening step had nothing to anchor on and produced VOICE-corpus-styled essays with zero source content. See `docs/audit-2026-05.md` for the full audit and the contract the new function holds.
- `VAULT_ROOT` was hardcoded to a specific vault layout, breaking audio output paths and note embedding for any OSS user with the bundled `<vault>/.obsidian/plugins/bedrock-voice/voice/` layout. Now detected at runtime.
- Plugin now checks for the Python interpreter + `note_to_audio.py` before invoking and surfaces a clear error message (instead of a cryptic `execFile` failure) when the voice pipeline isn't installed.

### Documentation
- README + landing page repositioned to productivity-led wedge (the productivity hook lands first, accessibility content remains prominent under "Who reaches for this" + `docs/ACCESSIBILITY.md`).
- Platform support matrix added near the top of README and landing: macOS Apple Silicon supported, Intel Mac partial, Linux/Windows not yet.
- Repo + brand moved to `opendian/bedrock`. Logo added (`docs/logo.png`).
- Landing site at `https://opendian.github.io/bedrock/` with hero GIF + MP4 demo.

## [0.1.0] — 2026-05-29

Initial public release.

### Added
- Read-aloud command and ribbon icon backed by a local Kokoro TTS pipeline.
- Real-time karaoke caption HUD with sentence + word-level highlighting.
- Playback controls: play/pause (Space), close (Esc), speed (0.75×–1.75×).
- Settings: backend (claude/codex/local), narration language (EN/FR), Kokoro voice, default speed, whole-note vs `tldr`+H2.
- Three LLM backends with no metered API:
  - `claude` — uses Claude Code CLI auth
  - `codex` — uses OpenAI Codex CLI auth
  - `local` — MLX-LM Qwen 2.5 3B (offline)
- Stop-reading command.
