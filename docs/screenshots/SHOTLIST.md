# Screenshot shotlist

A list of images the README needs. Each entry: the file the README expects, the scene, framing notes, and capture commands.

**General rules**
- Resolution: at least 1440 × 900 (2× retina). PNG (not JPG).
- Background: use a clean, light Obsidian theme (e.g., the default light theme or Minimal). Dark theme works too, pick one and stay consistent.
- Note content: use the demo notes under `docs/screenshots/demo-notes/` (see TODO below) — never capture from a real personal vault.
- Crop tightly. No menubar / dock unless it's part of the shot.

---

## 1. `hero-hud.png` — top of README

**Scene:** The caption HUD floating over a note, current sentence highlighted, word-level karaoke clearly visible.

**Framing:** Window-wide (Obsidian fills the frame). The note is in the background, the HUD overlays the lower-middle.

**Capture:**
```bash
# 1. Open the demo note in Obsidian
# 2. Trigger "Read note aloud with captions"
# 3. Wait until 3-4 sentences in (so the cache JSON has filled and the highlight is mid-word)
# 4. Run: bash bin/capture.sh hero-hud
```

---

## 2. `caption-detail.png` — "What it does" section

**Scene:** Close-up on the caption HUD. The current sentence is highlighted at the word level (one word in `.speaking` state, prior words in `.spoken`, next words unstyled). The next-sentence preview is visible below.

**Framing:** Just the HUD card, cropped tight. ~640 × 200.

**Capture:**
```bash
# Same as above, but crop tightly to the HUD only
bash bin/capture.sh caption-detail
```

---

## 3. `ribbon-icon.png` — "Usage" section

**Scene:** The Obsidian left sidebar (ribbon) showing the `audio-lines` icon, ideally with a hover-tooltip "Read note aloud (Bedrock Voice)" visible.

**Framing:** Just the ribbon column, ~160 × 480.

---

## 4. `settings.png` (optional) — "Settings" section

**Scene:** The Bedrock Voice settings tab open in Obsidian, all six settings visible.

**Framing:** The settings modal, ~900 × 700.

---

## 5. `architecture-diagram.png` (optional) — `docs/architecture.md`

**Scene:** A clean diagram of the flow (Obsidian → Plugin → Python → HUD). Build in Excalidraw / Figma / draw.io and export PNG.

**Framing:** Centered diagram on a white background, ~1200 × 600.

---

## Demo notes (to author and commit under `docs/screenshots/demo-notes/`)

Three notes that show off the plugin without leaking anything personal:

1. `demo-essay.md` — a short essay-style note (~200 words) on a generic topic ("Why morning walks change a workday", "On reading slowly", etc.).
2. `demo-distilled-book.md` — a faux "distilled book" note (gist + 3 principles + closer) showing the structured-note use case.
3. `demo-fr.md` — a short French note for the FR narration screenshots.

Keep these short enough that the audio is under 30 seconds — easier to demo, faster to regenerate when re-capturing.

---

## Recording the animated GIF (the killer asset)

The single highest-leverage marketing asset is a 10-second GIF of the karaoke highlight in action.

```bash
brew install ffmpeg
# 1. Open the demo note in Obsidian. Position window for the shot.
# 2. Run "Read note aloud with captions"
# 3. As the audio starts, run:
ffmpeg -f avfoundation -framerate 24 -i "1" -t 10 -vf "scale=1280:-1" -y docs/screenshots/hero.mp4
# 4. Convert to gif (optimized):
ffmpeg -i docs/screenshots/hero.mp4 -vf "fps=18,scale=720:-1:flags=lanczos,split[s0][s1];[s0]palettegen[p];[s1][p]paletteuse" -y docs/screenshots/hero.gif
```

Replace `hero-hud.png` in the README with `hero.gif` once the GIF is ready.

---

## Privacy checklist before committing screenshots

- [ ] No real note content from a personal vault.
- [ ] No identifying info in the system menubar (battery %, network name, clock seconds).
- [ ] No browser tabs visible in background.
- [ ] No real names, emails, addresses, or financial numbers.
- [ ] No third-party logos beyond Obsidian's own UI.
- [ ] All images cropped to remove anything not load-bearing.
