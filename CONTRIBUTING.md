# Contributing to Bedrock Voice

Thanks for considering a contribution. Bedrock Voice is a small project that exists because a single-purpose tool, done well, beats five half-built ones. Contributions that keep it focused — clearer code, fewer moving parts, better defaults — are especially welcome.

## Before you open a PR

1. **Open an issue first** for any non-trivial change. A 5-minute conversation saves hours of redirected work.
2. **One change per PR.** If you're touching both the plugin and the pipeline, split into two PRs and link them.
3. **No new runtime dependencies** without justification. The plugin's TypeScript dep tree and the Python `requirements.txt` are deliberately minimal.

## Local setup

### Plugin (TypeScript)

```bash
cd plugin/
npm install
npm run dev          # rebuilds main.js on change
```

To test in a real vault, symlink the plugin folder into a test vault:

```bash
ln -s "$(pwd)" "/path/to/test-vault/.obsidian/plugins/bedrock-voice"
```

Then reload the test vault.

### Voice pipeline (Python)

```bash
cd voice/
brew install python@3.12 espeak-ng ffmpeg
bash install.sh
source .venv/bin/activate
python note_to_audio.py "/path/to/some-note.md" --captions
```

## Code style

### TypeScript

- Strict mode. No `any` without a comment explaining why.
- Keep `main.ts` under ~400 lines. If it grows past that, split into modules.
- Settings names use `camelCase`. Plugin user-facing strings are sentence case.

### Python

- `black` for formatting (line length 100).
- Type hints on public functions.
- Stdout is the JSON-payload channel — never `print()` to stdout from helper functions during `--captions` mode. Use the `log` shim.

## Commit messages

Short and verb-first:

```
voice: cache audio + captions on note mtime
plugin: make voicePath setting absolute-aware
docs: clarify Apple Silicon requirement
ci: pin Node 20
```

Optional body for context if the change is non-obvious. No issue numbers in subject lines — GitHub links them automatically.

## Tests

For the plugin, the manual smoke test is: load it in a real vault, run "Read note aloud with captions" on a note, confirm audio plays and the HUD highlights words. For the pipeline, `python note_to_audio.py <note> --captions` should print a valid JSON payload to stdout with `wav`, `lang`, `whole`, and `segments`.

We don't have a full test suite yet. If you add one, smaller is better.

## What to NOT change without discussion

- The `--captions` stdout JSON contract. The plugin parses it; breaking changes need a major version bump.
- The settings keys (`backend`, `lang`, `voice`, `rate`, `whole`, `voicePath`). User installations rely on these.
- The bundled `voice/` location convention. Moving it requires migration logic.

## Releasing (maintainers)

Releases are cut by tag:

```bash
cd plugin/
npm version <patch|minor|major>     # bumps manifest.json + package.json
git push origin main --tags
```

GitHub Actions builds `main.js` from `main.ts` and attaches `main.js + manifest.json + styles.css` to the release.

For new community-plugin submissions, see `.github/COMMUNITY_PLUGIN_SUBMISSION.md` (TBD).

## Code of conduct

Be useful. Be specific. Read [VOICE.md](https://github.com/yanimeziani/bedrock-voice/blob/main/docs/voice.md) (the writing style this project is built around) before opening philosophical PRs.
