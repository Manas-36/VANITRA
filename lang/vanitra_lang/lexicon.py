"""ISL lexicon: what each gloss means and how it behaves in a sentence (lang/data/isl_lexicon.csv)."""
import csv
import os
from dataclasses import dataclass, field

DATA = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")


@dataclass
class Entry:
    gloss: str
    en: str
    pos: str                     # pron wh qmark time neg verb modal aspect noun adj interj adv
    forms: list = field(default_factory=list)
    tags: set = field(default_factory=set)

    def has(self, tag):
        return tag in self.tags


class Lexicon:
    def __init__(self, path=None):
        path = path or os.path.join(DATA, "isl_lexicon.csv")
        self.entries = {}
        with open(path, newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                forms = [x for x in r["forms"].split("|")] if r["forms"] else []
                self.entries[r["gloss"]] = Entry(r["gloss"], r["en"], r["pos"], forms, set(r["tags"].split()))
        # common alternative glosses used in ISL books
        for alias, real in {"ME": "I", "MY": "I", "INDEX": "HE-SHE", "THANKS": "THANK-YOU"}.items():
            if real in self.entries:
                self.entries.setdefault(alias, self.entries[real])

    def __contains__(self, g):
        return g in self.entries or g.startswith("FS:")

    def get(self, g):
        if g.startswith("FS:"):                  # fingerspelled word = proper noun
            name = g[3:].capitalize()
            return Entry(g, name, "noun", [name, name], {"proper"})
        return self.entries.get(g)

    def glosses(self):
        return list(self.entries)


def load_phrases(path=None):
    path = path or os.path.join(DATA, "phrases.csv")
    with open(path, newline="", encoding="utf-8") as f:
        return {tuple(r["glosses"].split()): r["english"] for r in csv.DictReader(f)}


def load_corpus(path=None):
    """lang/data/isl_corpus.txt -> list of (glosses, english, markers). Lines: [YN] [NEG] GLOSS ... | English"""
    path = path or os.path.join(DATA, "isl_corpus.txt")
    out = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.split("#", 1)[0].strip()
            if not line or "|" not in line:
                continue
            g, en = (s.strip() for s in line.split("|", 1))
            toks = g.split()
            markers = {t.strip("[]") for t in toks if t.startswith("[")}
            out.append(([t for t in toks if not t.startswith("[")], en, markers))
    return out
