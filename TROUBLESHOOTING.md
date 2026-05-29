# Troubleshooting

The top 12 things most likely to go wrong, with the fix. Sorted by frequency expected at launch.

> **Before anything else:** are you on **macOS Apple Silicon**? Bedrock Voice v0.1 doesn't support Windows, Linux, or Intel Macs yet. See [Platform support](#platform-support).

---

## 1. "Pipeline missing" / install modal pops up on every read

**Symptom:** Clicking "Read note aloud" opens the install modal instead of playing audio. Or you see a notice: "Bedrock Voice: pipeline missing at …".

**Cause:** The Python pipeline at `<plugin>/voice/` isn't installed yet, or the venv was deleted.

**Fix:** Open Terminal and run:

```bash
cd "<your-vault>/.obsidian/plugins/bedrock-voice/voice"
bash install.sh
```

The plugin's "Show pipeline install instructions" command (search command palette) also displays this command with a copy button.

---

## 2. "claude not found" / backend error

**Symptom:** Notice says something like "command not found: claude" or "no JSON payload from note_to_audio.py".

**Cause:** You set the backend to `claude` or `codex` but those CLIs aren't installed.

**Fix:** Settings → Bedrock Voice → LLM backend → choose **local** (the default). The `local` backend uses MLX-LM in-process — no external CLI needed.

---

## 3. First read is very slow (30-60 seconds)

**Symptom:** The first time you read any note, the "preparing audio..." notice hangs for ~30-60 seconds.

**Cause:** Three things load on first use:
- Kokoro 82M voice weights (~300 MB) download once.
- MLX-LM model (Qwen 2.5 3B-4bit) loads into memory (~2 GB).
- The script-tightening LLM warms up.

**Fix:** Wait it out. Every subsequent read of the **same unchanged note** is instant (cached). Every read of a **different note** takes 8-20 seconds with the `local` backend, or 1-4 seconds with `claude`/`codex` if you have those installed.

If it's been >2 minutes, the model download probably stalled — see issue #4.

---

## 4. Kokoro model download fails / hangs

**Symptom:** First read hangs for several minutes; install.sh completes but Kokoro never finishes.

**Cause:** Network issue, Hugging Face rate limit, or disk space.

**Fix:**

```bash
cd "<your-vault>/.obsidian/plugins/bedrock-voice/voice"
source .venv/bin/activate
python -c "from kokoro import KPipeline; KPipeline(lang_code='a')"
```

Watch the output. If you see a download error, check:
- `df -h ~` — at least 1 GB free.
- `ping huggingface.co` — network reachable.
- Try again. Hugging Face occasionally rate-limits.

---

## 5. No audio plays / HUD appears but silent

**Symptom:** Caption HUD appears and highlights words, but no sound.

**Cause:** Macros system audio output, Obsidian doesn't have audio permission, or the WAV file is empty.

**Fix:**

1. Check system volume + output device.
2. Open the generated WAV in Finder to confirm it has audio:
   `<plugin>/audio/<note-slug>.wav` (path depends on `BEDROCK_AUDIO_OUT` env var).
3. Try a different note. If only one note is silent, check that the note has either a `tldr:` frontmatter field or `## H2` headings (those are what gets narrated by default — see "Read whole note" setting below).

---

## 6. Note read is much shorter than expected

**Symptom:** The audio narrates 1-2 sentences but your note has 5 paragraphs.

**Cause:** Default mode reads the **`tldr:` frontmatter field + H2 headers only**. This is intentional — for long notes, a structured digest works better than a raw text-dump.

**Fix:** Settings → Bedrock Voice → "Read whole note" → toggle ON.

---

## 7. HUD doesn't appear after clicking the button

**Symptom:** The notice flashes "preparing audio..." then nothing — no HUD, no error.

**Cause:** The Python pipeline failed silently OR the JSON payload didn't parse.

**Fix:**

1. Open Obsidian → View → Toggle Developer Tools → Console. Look for red errors prefixed `Bedrock Voice:`.
2. Run the pipeline manually to see real stderr:

```bash
cd "<your-vault>/.obsidian/plugins/bedrock-voice/voice"
source .venv/bin/activate
python note_to_audio.py "/full/path/to/your/note.md" --captions
```

The error will be human-readable. Common causes: wrong backend, missing model, MLX out of memory.

---

## 8. Cache doesn't refresh when I edit the note

**Symptom:** You edit a note then click read — old audio plays.

**Cause:** The cache key is `(note mtime, lang, whole)`. If your filesystem doesn't update mtime (rare, but happens with some sync tools like iCloud Drive), the cache won't invalidate.

**Fix:** Force-touch the file:

```bash
touch "/path/to/your/note.md"
```

Or delete the cached audio:

```bash
rm "<your-vault>/.obsidian/plugins/bedrock-voice/audio/<note-slug>.wav"
rm "<your-vault>/.obsidian/plugins/bedrock-voice/audio/<note-slug>.captions.json"
```

---

## 9. Cache refreshes when I don't expect it

**Symptom:** Re-reading the same note keeps regenerating audio.

**Cause:** Something else is touching the file — Obsidian sync, an auto-formatter, the Linter plugin. Each modification triggers regeneration.

**Fix:** Check if a plugin is auto-modifying your notes. If yes, either:
- Disable the auto-modifier for now.
- Accept the regeneration cost.
- Open a feature request for content-hash caching (more accurate than mtime).

---

## 10. "MLX out of memory" / kernel panic

**Symptom:** Read triggers an error mentioning Metal, MLX, or memory.

**Cause:** Default model is `Qwen2.5-3B-Instruct-4bit` (~2 GB resident). On a 8 GB Mac running other big apps, you can run out.

**Fix:** Either:

1. Close memory-hungry apps (Chrome, Slack), retry.
2. Switch to a smaller model — edit `<plugin>/voice/.env`:

```
BEDROCK_LLM_MODEL=mlx-community/SmolLM2-1.7B-Instruct-4bit
```

3. Switch backend to `claude` or `codex` if you have them.

---

## 11. HUD text is unreadable / wrong colors

**Symptom:** Caption colors blend into your theme, hard to read.

**Cause:** The HUD inherits Obsidian's theme variables. Some custom themes set `--text-accent` to a low-contrast color.

**Fix:** The plugin marks the active word with **three signals** (color + bold + underline + glow), so the active word is always identifiable. If reading the rest of the sentence is hard, switch to a higher-contrast theme temporarily, or open an issue tagged `accessibility` describing your setup.

---

## 12. Apple Silicon Mac, but you mentioned Intel works?

**Symptom:** Install on Intel Mac proceeded, but the `local` backend errors out.

**Cause:** MLX requires Apple Silicon (Metal/MPS). Kokoro works on Intel, but the default LLM backend doesn't.

**Fix:** Switch backend to `claude` or `codex` in Settings. Or wait for v0.2 (a CPU LLM backend is planned — see issue tracker).

---

## Platform support

| Platform | Status | Notes |
| --- | --- | --- |
| **macOS Apple Silicon** | ✅ Supported | Tested daily on M-series Macs running macOS 14+. |
| macOS Intel | ⚠ Partially | Kokoro TTS works. `local` LLM backend (MLX) does not — use `claude`/`codex`. |
| Linux | 🚧 Roadmap | Kokoro should work but install path is untested. PRs welcome. |
| Windows | 🚧 Roadmap | Install path needs rewrite (no bash, no brew). |
| iOS / Android | ❌ Not supported | Obsidian mobile can't shell out to Python. |

We're loud about this because surprise install failures during a launch window poison sentiment more than any feature gap. v0.1 is intentionally small in scope.

---

## Filing a good issue

If none of the above fixes it, [open an issue](https://github.com/opendian/bedrock/issues/new?template=bug.yml) with:

1. **macOS version + chip:** `sw_vers && uname -m`
2. **Plugin version:** Settings → Community plugins → Bedrock Voice → version
3. **Backend:** what's selected in Settings
4. **Error message** from the Obsidian developer console (View → Toggle Developer Tools → Console)
5. **Pipeline error** from running `python note_to_audio.py <note> --captions` directly

The bug template asks for all of this. Filling it out helps us reproduce in <5 minutes instead of <2 hours.
