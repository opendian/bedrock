"""Audit cached audio against source notes.

For every <slug>.captions.json under Sources/audio/, find the source note,
re-derive what the pipeline would have given to the LLM, then compare with
what was actually spoken.

Discrepancy categories
----------------------
1. ORPHAN          source note for the slug no longer in the vault
2. AMBIGUOUS       slug matches >1 note (the audio may not correspond to the
                   note we picked first)
3. STALE           source was edited after the audio was generated
4. CROSS-LANG      source lang ≠ spoken lang. This is BY DESIGN if the user
                   chose EN narration of a FR note (see VOICE.md §A7), so it's
                   only flagged, not an error per se.
5. COVERAGE GAP    a content H2 from the source is absent from the spoken
                   text (we filter out skeleton labels like "Gist", "Voisins")
6. NOVEL CONTENT   words spoken that don't appear in the source. Some level is
                   normal (the LLM is a rewriter, not a copier); we flag only
                   when the count is unusually high relative to source length.
"""
import argparse
import difflib
import json
import re
import sys
import unicodedata
from pathlib import Path

VAULT = Path(__file__).resolve().parents[3]
AUDIO_DIR = VAULT / "Sources" / "audio"

# H2 headings that are structural skeleton, not content. The pipeline
# legitimately drops these when tightening for speech.
SKELETON_HEADINGS = {
    "gist", "le gist",
    "voisins", "adjacent", "adjacents",
    "comment l'appliquer", "how to apply",
    "tldr", "tl;dr",
    "memorable quotes", "citations a garder", "citations à garder",
    "key principles", "principes", "trois principes", "principes a retenir",
    "premise", "premise & operating questions",
    "where to add code",
    "issues + prs welcome", "contributing",
    "license", "licence", "mit",
}


def slugify(text: str, maxlen: int = 50) -> str:
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii").lower()
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return (text[:maxlen].strip("-")) or "note"


def split_frontmatter(text: str):
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            nl = text.find("\n", end + 1)
            return text[: nl + 1], text[nl + 1 :]
    return None, text


def extract_source(text: str, whole: bool):
    """Reproduce voice/note_to_audio.py:extract_source exactly, including the
    fallback to body when tldr+H2 collection yields nothing."""
    fm, body = split_frontmatter(text)
    if whole:
        return body.strip(), fm, body
    parts = []
    if fm:
        m = re.search(r"^tldr:\s*(.+)$", fm, re.MULTILINE)
        if m:
            parts.append(m.group(1).strip())
    for line in body.splitlines():
        s = line.strip()
        if s.startswith("## "):
            parts.append(s[3:].strip())
    collected = "\n".join(parts).strip()
    return (collected or body.strip()), fm, body


def extract_frontmatter_lang(fm_text):
    if not fm_text:
        return None
    m = re.search(r"^lang:\s*(\S+)", fm_text, re.MULTILINE)
    return m.group(1).strip().strip('"\'') if m else None


def index_vault_notes():
    index = {}
    for p in VAULT.rglob("*.md"):
        if any(part.startswith(".") for part in p.relative_to(VAULT).parts):
            continue
        if "_legacy-catalogs" in p.parts:
            continue
        slug = slugify(p.stem)
        index.setdefault(slug, []).append(p)
    return index


def best_match(candidates, captions_slug, captions_mtime):
    """When >1 candidate, prefer one whose mtime is just before captions_mtime
    (the source most likely to have been narrated)."""
    if len(candidates) == 1:
        return candidates[0]
    older = [p for p in candidates if p.stat().st_mtime <= captions_mtime]
    if older:
        return max(older, key=lambda p: p.stat().st_mtime)
    return candidates[0]


def tokens(s):
    return set(re.findall(r"[a-zA-Zà-ÿÀ-ß']{3,}", s.lower()))


def fuzzy_present(needle, spoken_sentences):
    needle_n = needle.strip().lower()
    if not needle_n or not spoken_sentences:
        return 0.0
    return max(
        difflib.SequenceMatcher(None, needle_n, s.strip().lower()).ratio()
        for s in spoken_sentences
    )


def audit_one(captions_path, vault_index):
    data = json.loads(captions_path.read_text(encoding="utf-8"))
    spoken_segments = data.get("segments", [])
    spoken_sentences = [seg.get("text", "") for seg in spoken_segments]
    spoken_text = " ".join(spoken_sentences).strip()
    sidecar_lang = data.get("lang", "?")
    sidecar_whole = data.get("whole")  # None on pre-fix sidecars
    wav_path = Path(data.get("wav", ""))
    wav_exists = wav_path.is_file()

    captions_slug = captions_path.name.replace(".captions.json", "")
    candidates = vault_index.get(captions_slug, [])
    if not candidates:
        for slug, paths in vault_index.items():
            if slug.startswith(captions_slug) or captions_slug.startswith(slug):
                candidates += paths

    r = {
        "slug": captions_slug,
        "captions_file": captions_path.name,
        "captions_mtime": captions_path.stat().st_mtime,
        "wav_exists": wav_exists,
        "sidecar_lang": sidecar_lang,
        "sidecar_whole": sidecar_whole,
        "spoken_words": len(spoken_text.split()),
        "spoken_segments": len(spoken_segments),
        "candidates": [str(p.relative_to(VAULT)) for p in candidates],
    }

    if not candidates:
        r["status"] = "ORPHAN"
        return r

    src = best_match(candidates, captions_slug, r["captions_mtime"])
    src_text = src.read_text(encoding="utf-8")

    # Try both modes; if sidecar tells us, use it; otherwise infer by which
    # extraction is closer in size to the spoken script.
    src_text_tldr_h2, fm, body = extract_source(src_text, whole=False)
    src_text_whole, _, _ = extract_source(src_text, whole=True)

    if sidecar_whole is True:
        extracted = src_text_whole
        inferred_mode = "whole"
    elif sidecar_whole is False:
        extracted = src_text_tldr_h2
        inferred_mode = "tldr+H2"
    else:
        spoken_w = max(1, r["spoken_words"])
        diff_tldr = abs(len(src_text_tldr_h2.split()) - spoken_w)
        diff_whole = abs(len(src_text_whole.split()) - spoken_w)
        if diff_tldr <= diff_whole:
            extracted = src_text_tldr_h2
            inferred_mode = "tldr+H2 (inferred)"
        else:
            extracted = src_text_whole
            inferred_mode = "whole (inferred)"

    src_lang = extract_frontmatter_lang(fm)
    h2_lines = [ln.strip()[3:].strip() for ln in body.splitlines() if ln.strip().startswith("## ")]
    content_h2 = [h for h in h2_lines if h.lower().strip() not in SKELETON_HEADINGS]

    r.update({
        "source": str(src.relative_to(VAULT)),
        "source_mtime": src.stat().st_mtime,
        "source_lang": src_lang or "?",
        "mode": inferred_mode,
        "extracted_words": len(extracted.split()),
        "source_h2_total": len(h2_lines),
        "source_h2_content": len(content_h2),
        "expansion_ratio": round(r["spoken_words"] / max(1, len(extracted.split())), 2),
        "stale": src.stat().st_mtime > r["captions_mtime"],
    })

    # Cross-language is by design when sidecar=en and source!=en (tighten_for_speech
    # rewrites FR -> EN intentionally per VOICE.md §A7). Flag for awareness only.
    if src_lang and sidecar_lang in ("en", "fr") and src_lang != sidecar_lang:
        if sidecar_lang == "en":
            r["cross_lang"] = f"{src_lang}→en (translation by design)"
        else:
            r["cross_lang"] = f"{src_lang}→{sidecar_lang} (potentially unexpected)"

    # Coverage on CONTENT H2 only
    uncovered = [h for h in content_h2 if fuzzy_present(h, spoken_sentences) < 0.30]
    if uncovered:
        r["uncovered_content_h2"] = uncovered

    # Novel-token heat. We compare lowercased word sets and exclude very-common
    # filler. We score "novel ratio" = novel_in_spoken / total_in_spoken.
    src_tok = tokens(extracted + " " + body)
    spk_tok = tokens(spoken_text)
    novel = spk_tok - src_tok
    STOP = {
        "the", "and", "for", "with", "this", "that", "from", "into", "your",
        "you", "are", "but", "not", "all", "one", "two", "off", "over", "way",
        "out", "any", "can", "has", "have", "was", "were", "more", "less",
        "than", "when", "what", "which", "while", "where", "their", "them",
        "they", "then", "there", "these", "those", "very", "well", "just",
        "vous", "tes", "ses", "des", "les", "une", "ils", "pas",
        "que", "qui", "ces", "dans", "pour", "avec", "sont",
        "tres", "tout", "tous", "plus", "moins", "mais", "donc",
        "alors", "encore", "deja", "etre", "fait", "faits",
        "comme", "ainsi", "selon", "entre", "leurs", "elle", "elles",
    }
    novel = sorted(t for t in novel if t not in STOP and len(t) >= 4)
    r["novel_token_count"] = len(novel)
    r["novel_ratio"] = round(len(novel) / max(1, len(spk_tok)), 2)
    if novel:
        r["novel_token_sample"] = novel[:30]

    r.setdefault("status", "AMBIGUOUS" if len(candidates) > 1 else "OK")
    return r


def render(reports):
    out = []
    for r in reports:
        flags = []
        if r.get("status") == "ORPHAN":
            flags.append("ORPHAN")
        if r.get("status") == "AMBIGUOUS":
            flags.append(f"AMBIGUOUS({len(r.get('candidates', []))})")
        if r.get("stale"):
            flags.append("STALE")
        if "cross_lang" in r:
            tag = "CROSS-LANG-DESIGN" if "design" in r["cross_lang"] else "CROSS-LANG-DRIFT"
            flags.append(tag)
        if r.get("uncovered_content_h2"):
            flags.append(f"GAPS({len(r['uncovered_content_h2'])})")
        if r.get("novel_ratio", 0) >= 0.60:
            flags.append(f"NOVEL({r['novel_ratio']})")

        out.append(f"── {r['captions_file']}")
        if r.get("source"):
            out.append(f"   source     : {r['source']}")
        out.append(f"   mode       : {r.get('mode', '?')}     lang : sidecar={r['sidecar_lang']} source={r.get('source_lang','?')}")
        out.append(f"   words      : extracted={r.get('extracted_words','?')}  spoken={r['spoken_words']}  ratio={r.get('expansion_ratio','?')}")
        out.append(f"   H2         : total={r.get('source_h2_total', '?')} content={r.get('source_h2_content','?')}")
        out.append(f"   novel ratio: {r.get('novel_ratio','?')} ({r.get('novel_token_count', 0)} tokens)")
        if flags:
            out.append(f"   FLAGS      : {' '.join(flags)}")
        if r.get("uncovered_content_h2"):
            for h in r["uncovered_content_h2"]:
                out.append(f"     · uncovered: {h}")
        if "cross_lang" in r:
            out.append(f"     · {r['cross_lang']}")
        out.append("")
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if not AUDIO_DIR.is_dir():
        sys.exit(f"no audio dir at {AUDIO_DIR}")
    captions = sorted(AUDIO_DIR.glob("*.captions.json"))
    if not captions:
        sys.exit("no captions sidecars found")

    index = index_vault_notes()
    reports = [audit_one(c, index) for c in captions]

    if args.json:
        print(json.dumps(reports, indent=2, default=str))
        return

    print(f"\n=== Audit — {len(reports)} captioned audio files ===\n")
    print(render(reports))

    n_orphan = sum(1 for r in reports if r.get("status") == "ORPHAN")
    n_ambig = sum(1 for r in reports if r.get("status") == "AMBIGUOUS")
    n_stale = sum(1 for r in reports if r.get("stale"))
    n_xlang_design = sum(1 for r in reports if "cross_lang" in r and "design" in r["cross_lang"])
    n_xlang_drift = sum(1 for r in reports if "cross_lang" in r and "design" not in r["cross_lang"])
    n_gap = sum(1 for r in reports if r.get("uncovered_content_h2"))
    n_novel = sum(1 for r in reports if r.get("novel_ratio", 0) >= 0.60)

    print(f"Summary  · orphans={n_orphan}  ambiguous={n_ambig}  stale={n_stale}  "
          f"FR→EN by-design={n_xlang_design}  cross-lang-drift={n_xlang_drift}  "
          f"coverage-gaps={n_gap}  high-novel={n_novel}\n")


if __name__ == "__main__":
    main()
