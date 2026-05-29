"""Vault helpers — contract loading, slugify, frontmatter per CLAUDE.md §B1."""
import re
import datetime
import unicodedata
from functools import lru_cache

import config


@lru_cache(maxsize=1)
def load_contract():
    """Return (VOICE.md, CLAUDE.md) as text — the live voice + routing contract."""
    voice = config.VOICE_MD.read_text(encoding="utf-8")
    claude = config.CLAUDE_MD.read_text(encoding="utf-8")
    return voice, claude


def slugify(text, maxlen=50):
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii").lower()
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return (text[:maxlen].strip("-")) or "note"


def today():
    return datetime.date.today().isoformat()


def split_frontmatter(text):
    """Return (frontmatter_str_or_None, body)."""
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            nl = text.find("\n", end + 1)
            return text[: nl + 1], text[nl + 1 :]
    return None, text


def build_frontmatter(titre, tldr, typ="note", statut="graine", lang="fr",
                      tags=None, voisins=None, projet="aucun", deploy=("fr", "en")):
    """Minimal valid frontmatter per CLAUDE.md §B1."""
    tags = tags or []
    voisins = voisins or []
    d = today()
    lines = ["---",
             f"titre: {titre}",
             f"tldr: {tldr}",
             f"créé: {d}",
             f"modifié: {d}",
             f"type: {typ}",
             f"projet: {projet}",
             f"statut: {statut}",
             "voisins:"]
    lines += [f'  - "{v}"' for v in voisins] or ["  []"]
    lines += [f"tags: [{', '.join(tags)}]",
              f"lang: {lang}",
              f"deploy: [{', '.join(deploy)}]",
              "---", ""]
    return "\n".join(lines)
