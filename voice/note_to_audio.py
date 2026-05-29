"""Voice OUT — read a note aloud with Kokoro.

    python note_to_audio.py "Notes/x.md"            # EN narration, tldr+H2 source
    python note_to_audio.py "Notes/x.md" --lang fr  # FR narration
    python note_to_audio.py "Notes/x.md" --whole     # whole body instead of tldr+H2
    python note_to_audio.py "Notes/x.md" --mp3       # mp3 (needs ffmpeg)

Writes Sources/audio/<slug>.wav (gitignored) and appends an embed link to the note footer.
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
import soundfile as sf

import config
from vault import split_frontmatter, slugify
from llm import tighten_for_speech


def extract_source(text, whole=False):
    """Return the text to narrate: tldr + H2 headers by default, or the whole body."""
    fm, body = split_frontmatter(text)
    if whole:
        return body.strip()
    parts = []
    if fm:
        m = re.search(r"^tldr:\s*(.+)$", fm, re.MULTILINE)
        if m:
            parts.append(m.group(1).strip())
    # first thesis line under H1 + each H2 line
    for line in body.splitlines():
        s = line.strip()
        if s.startswith("## "):
            parts.append(s[3:].strip())
    return "\n".join(parts).strip() or body.strip()


def synth(script, out_path):
    from kokoro import KPipeline
    pipe = KPipeline(lang_code=config.KOKORO_LANG)
    chunks = [audio for _, _, audio in pipe(script, voice=config.KOKORO_VOICE)]
    if not chunks:
        raise RuntimeError("Kokoro produced no audio")
    full = np.concatenate(chunks)
    sf.write(str(out_path), full, config.KOKORO_SR)


def split_sentences(text):
    parts = re.split(r"(?<=[.!?…])\s+", text.strip())
    return [p.strip() for p in parts if p.strip()]


def synth_segments(script, out_path):
    """Synthesize sentence by sentence; return [{text,start,end}] with exact timing."""
    from kokoro import KPipeline
    pipe = KPipeline(lang_code=config.KOKORO_LANG)
    sr = config.KOKORO_SR
    audio_parts, segments, t = [], [], 0.0
    for sent in split_sentences(script):
        chunks = [a for _, _, a in pipe(sent, voice=config.KOKORO_VOICE)]
        if not chunks:
            continue
        audio = np.concatenate(chunks)
        dur = len(audio) / sr
        segments.append({"text": sent, "start": round(t, 3), "end": round(t + dur, 3)})
        t += dur
        audio_parts.append(audio)
    if not audio_parts:
        raise RuntimeError("Kokoro produced no audio")
    sf.write(str(out_path), np.concatenate(audio_parts), sr)
    return segments


def cached_payload(note_path, wav_path, sidecar_path, lang, whole):
    """Return the cached payload iff WAV + sidecar are newer than the note AND
    the cached lang/whole match the current request. Otherwise None."""
    if not wav_path.exists() or not sidecar_path.exists():
        return None
    note_mtime = note_path.stat().st_mtime
    cache_mtime = min(wav_path.stat().st_mtime, sidecar_path.stat().st_mtime)
    if note_mtime > cache_mtime:
        return None
    try:
        payload = json.loads(sidecar_path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    if payload.get("lang") != lang:
        return None
    if payload.get("whole", False) != whole:
        return None
    # Repoint the wav path in case the vault was moved.
    payload["wav"] = str(wav_path)
    return payload


def to_mp3(wav_path):
    mp3_path = wav_path.with_suffix(".mp3")
    subprocess.run(["ffmpeg", "-y", "-i", str(wav_path), "-b:a", "128k", str(mp3_path)], check=True)
    wav_path.unlink(missing_ok=True)
    return mp3_path


def embed_link(note_path, audio_path):
    """Append a vault-relative embed to the note if not already present."""
    rel = audio_path.relative_to(config.VAULT_ROOT).as_posix()
    embed = f"![[{rel}]]"
    text = note_path.read_text(encoding="utf-8")
    if embed in text:
        return
    sep = "" if text.endswith("\n") else "\n"
    note_path.write_text(text + f"{sep}\n**Audio :** {embed}\n", encoding="utf-8")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("note")
    ap.add_argument("--lang", choices=["en", "fr"], default="en")
    ap.add_argument("--whole", action="store_true")
    ap.add_argument("--mp3", action="store_true")
    ap.add_argument("--captions", action="store_true",
                    help="sentence-level timing; print JSON {wav,lang,segments} for the Obsidian plugin")
    args = ap.parse_args()

    note_path = Path(args.note)
    if not note_path.is_absolute():
        note_path = config.VAULT_ROOT / note_path
    if not note_path.exists():
        sys.exit(f"note not found: {note_path}")

    log = (lambda *a: None) if args.captions else print   # keep stdout pure JSON in captions mode

    config.AUDIO_OUT.mkdir(parents=True, exist_ok=True)
    out = config.AUDIO_OUT / f"{slugify(note_path.stem)}.wav"
    sidecar = out.with_suffix(".captions.json")

    # Cache hit: WAV + sidecar are newer than the note and match the requested
    # lang/whole. Skip LLM tightening + Kokoro synth — return what we have.
    cached = cached_payload(note_path, out, sidecar, args.lang, args.whole)
    if cached is not None:
        log(f"[cache] reusing {out.name} (note unchanged)")
        if args.captions:
            print(json.dumps(cached, ensure_ascii=False))
            return
        if args.mp3 and out.suffix == ".wav":
            mp3 = out.with_suffix(".mp3")
            if not mp3.exists() or mp3.stat().st_mtime < out.stat().st_mtime:
                out = to_mp3(out)
            else:
                out = mp3
        embed_link(note_path, out)
        log(f"done (cached) → {out}")
        return

    text = note_path.read_text(encoding="utf-8")
    source = extract_source(text, whole=args.whole)
    log(f"[1/3] tightening to spoken script ({args.lang})…")
    script = tighten_for_speech(source, target_lang=args.lang)

    if args.captions:
        segments = synth_segments(script, out)
        payload = {"wav": str(out), "lang": args.lang, "whole": args.whole, "segments": segments}
        sidecar.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(payload, ensure_ascii=False))   # stdout = the only thing the plugin parses
        return

    log(f"[2/3] synthesizing → {out.name}")
    synth(script, out)
    if args.mp3:
        out = to_mp3(out)
    log("[3/3] embedding link in note")
    embed_link(note_path, out)
    log(f"done → {out}")


if __name__ == "__main__":
    main()
