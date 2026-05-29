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


# Frontmatter keys that act as a one-line gist. First match wins.
_TLDR_KEYS = ("tldr", "gist", "summary", "description")

# Cap per-section body so a long note doesn't blow the LLM context budget.
_SECTION_WORD_CAP = 80


def _clean_markdown(line):
    """Strip markdown noise from a single line so the LLM gets readable prose."""
    s = re.sub(r"^#+\s+", "", line)                              # ### subheading
    s = re.sub(r"\[\[([^\]|]+)(\|[^\]]+)?\]\]", r"\1", s)        # [[wiki|alias]] -> wiki
    s = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", s)               # [text](url) -> text
    s = re.sub(r"`([^`]+)`", r"\1", s)                            # `inline code`
    s = re.sub(r"\*\*([^*]+)\*\*", r"\1", s)                     # **bold**
    s = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"\1", s)            # *italic*
    s = re.sub(r"^[-*+]\s+", "", s)                               # - list item
    s = re.sub(r"^\d+\.\s+", "", s)                               # 1. list item
    s = re.sub(r"^>+\s*", "", s)                                  # > blockquote
    s = re.sub(r"<[^>]+>", "", s)                                 # <html>, <https://url>
    return s.strip()


def extract_source(text, whole=False):
    """Return the text to narrate.

    Default mode (whole=False) — collect the load-bearing prose:
      1. Frontmatter `tldr:` (or `gist:`/`summary:`/`description:`).
      2. For each `## H2` section: the heading + the first ~80 words of body.
         Skips code blocks, tables, separators.
      3. Fallback to the whole body if nothing was extracted.

    whole=True bypasses extraction and returns the body verbatim.
    """
    fm, body = split_frontmatter(text)
    if whole:
        return body.strip()

    parts = []

    # 1. Frontmatter one-line gist (first matching key wins).
    if fm:
        for key in _TLDR_KEYS:
            m = re.search(rf"^{key}:\s*(.+)$", fm, re.MULTILINE | re.IGNORECASE)
            if m:
                value = m.group(1).strip().strip('"\'').strip()
                if value:
                    parts.append(value)
                break

    # 2. Walk each H2 section, capturing heading + first paragraph of body.
    lines = body.splitlines()
    n = len(lines)
    i = 0
    in_code = False
    while i < n:
        s = lines[i].strip()

        if s.startswith("```"):
            in_code = not in_code
            i += 1
            continue

        if not in_code and s.startswith("## "):
            heading = s[3:].strip()
            body_words = []
            j = i + 1
            sec_in_code = False
            while j < n:
                t = lines[j].strip()
                if t.startswith("```"):
                    sec_in_code = not sec_in_code
                    j += 1
                    continue
                if sec_in_code:
                    j += 1
                    continue
                if t.startswith("## ") or t.startswith("# "):
                    break
                if t.startswith("|") or t in ("---", "***", "___"):
                    j += 1
                    continue
                cleaned = _clean_markdown(t)
                if cleaned:
                    body_words.extend(cleaned.split())
                if len(body_words) >= _SECTION_WORD_CAP:
                    break
                j += 1

            section_body = " ".join(body_words[:_SECTION_WORD_CAP])
            parts.append(f"{heading}. {section_body}".strip(". ").strip() or heading)
            i = j
            continue

        i += 1

    collected = "\n\n".join(p for p in parts if p).strip()
    return collected or body.strip()


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
