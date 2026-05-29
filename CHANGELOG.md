# Changelog

All notable changes to Bedrock Voice are tracked here. Versioning follows [SemVer](https://semver.org).

## [Unreleased]

### Added
- `voicePath` setting to point the plugin at a non-bundled Python pipeline location (vault-relative or absolute). Default: bundled `<plugin>/voice/`.
- Smart cache: audio + captions are reused when the source note has not been edited since the last generation. Cache key includes `lang` and `whole` flags.

### Changed
- Plugin notice message simplified: "preparing audio (backend)…" instead of "generating audio…" — the new cache layer often makes this near-instant.
- Pipeline writes `whole` flag into the captions sidecar so the cache invalidates correctly when the user toggles "Read whole note".

### Fixed
- Plugin now checks for the Python interpreter + `note_to_audio.py` existence and surfaces a clear error message instead of a cryptic execFile failure when the voice pipeline isn't installed.

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
