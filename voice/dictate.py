"""Voice IN — Wispr-style dictation daemon (menubar + global hotkey).

    python dictate.py

Hotkey (default Ctrl+Alt+D) toggles recording. Release the hotkey combo, press again to stop.
Menubar switches mode:
    Insert  -> cleaned FR prose pasted at the cursor (any app).
    Note    -> cleaned FR note written to Inbox/<slug>.md with frontmatter.

Requires macOS Microphone + Accessibility permissions for the launching app.
"""
import subprocess
import threading

import numpy as np
import rumps
import sounddevice as sd
from pynput import keyboard

import config
from llm import clean_dictation
from vault import build_frontmatter, slugify


# ── audio capture ──────────────────────────────────────────────────────
class Recorder:
    def __init__(self):
        self.frames = []
        self.recording = False
        self.stream = None

    def _cb(self, indata, frames, time_, status):
        if self.recording:
            self.frames.append(indata.copy())

    def start(self):
        self.frames = []
        self.recording = True
        self.stream = sd.InputStream(
            samplerate=config.SAMPLE_RATE, channels=1, dtype="float32", callback=self._cb
        )
        self.stream.start()

    def stop(self):
        self.recording = False
        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None
        if not self.frames:
            return None
        return np.concatenate(self.frames, axis=0).flatten().astype(np.float32)


# ── STT ────────────────────────────────────────────────────────────────
def transcribe(audio):
    import mlx_whisper
    res = mlx_whisper.transcribe(audio, path_or_hf_repo=config.WHISPER_MODEL)
    return res.get("text", "").strip()


# ── insertion ──────────────────────────────────────────────────────────
def paste_at_cursor(text):
    subprocess.run(["pbcopy"], input=text.encode("utf-8"), check=True)
    subprocess.run(
        ["osascript", "-e", 'tell application "System Events" to keystroke "v" using command down'],
        check=True,
    )


def write_inbox_note(body):
    title_line = body.strip().splitlines()[0][:60] if body.strip() else "capture vocale"
    slug = slugify(title_line)
    fm = build_frontmatter(titre=title_line, tldr=title_line, typ="note", statut="graine", lang="fr")
    path = config.INBOX / f"{slug}.md"
    config.INBOX.mkdir(parents=True, exist_ok=True)
    path.write_text(fm + f"# {title_line}\n\n" + body.strip() + "\n", encoding="utf-8")
    return path


# ── app ────────────────────────────────────────────────────────────────
class DictateApp(rumps.App):
    def __init__(self):
        super().__init__("🎙", quit_button="Quitter")
        self.rec = Recorder()
        self.mode = "insert"   # or "note"
        self.busy = False
        self.mode_item = rumps.MenuItem("Mode : Insert", callback=self.toggle_mode)
        self.menu = [self.mode_item]
        self._start_hotkey()

    def toggle_mode(self, _):
        self.mode = "note" if self.mode == "insert" else "insert"
        self.mode_item.title = f"Mode : {'Note' if self.mode == 'note' else 'Insert'}"

    def _start_hotkey(self):
        # GlobalHotKeys runs its own listener thread.
        self._hk = keyboard.GlobalHotKeys({config.HOTKEY: self._on_hotkey})
        self._hk.start()

    def _on_hotkey(self):
        if self.busy:
            return
        if not self.rec.recording:
            self.title = "🔴"
            self.rec.start()
        else:
            self.title = "⏳"
            self.busy = True
            threading.Thread(target=self._finish, daemon=True).start()

    def _finish(self):
        try:
            audio = self.rec.stop()
            if audio is None or len(audio) < config.SAMPLE_RATE * 0.3:
                rumps.notification("Bedrock", "Dictation", "trop court — ignoré")
                return
            raw = transcribe(audio)
            if not raw:
                rumps.notification("Bedrock", "Dictation", "rien transcrit")
                return
            cleaned = clean_dictation(raw, mode=("note" if self.mode == "note" else "raw"))
            if self.mode == "note":
                path = write_inbox_note(cleaned)
                rumps.notification("Bedrock", "Note créée", path.name)
            else:
                paste_at_cursor(cleaned)
        except Exception as e:  # noqa: BLE001 — daemon must survive a bad take
            rumps.notification("Bedrock", "Erreur", str(e)[:120])
        finally:
            self.busy = False
            self.title = "🎙"


if __name__ == "__main__":
    DictateApp().run()
