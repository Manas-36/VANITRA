"""From a stream of recognised signs to a sentence.

The recognisers (glove CNN, camera CNN) emit SignEvents: a moment where one sign was held/performed,
with the model's top-N guesses. A sentence ends after a pause (hands down / REST).
Then the decoder picks the most likely GLOSS SEQUENCE using
    score = sum(  w_model * log p(sign guess)  +  w_lm * log P(gloss | previous gloss)  )
over all combinations of the N-best guesses (beam search), so a guess that makes no sense in
context ("I WATER WHERE WANT") loses to one that does ("I WATER WANT").
An event can also be dropped (a false detection) at a cost. Then the gloss sentence is translated.
"""
import math
from collections import Counter, defaultdict
from dataclasses import dataclass, field

from .lexicon import load_corpus, load_phrases


@dataclass
class SignEvent:
    t: float                                   # time (s) the sign was accepted
    nbest: list                                # [(gloss, prob), ...] best first
    source: str = "glove"


@dataclass
class Sentence:
    glosses: list
    english: str
    events: list = field(default_factory=list)
    yn: bool = False
    neg: bool = False


class BigramLM:
    """Gloss bigram model, interpolated with a unigram model (Jelinek-Mercer), trained on
    lang/data/isl_corpus.txt + phrases.csv. Interpolation keeps unseen-but-valid pairs possible."""

    def __init__(self, sentences, vocab, lam=0.6):
        self.vocab = {norm(v) for v in vocab} | {"</s>"}
        self.lam = lam
        self.big = defaultdict(Counter)
        self.uni = Counter()
        for s in sentences:
            toks = ["<s>"] + [norm(t) for t in s] + ["</s>"]
            self.uni.update(toks[1:])
            for a, b in zip(toks, toks[1:]):
                self.big[a][b] += 1
        self.n_uni = sum(self.uni.values())

    def logp(self, prev, word):
        prev, word = norm(prev), norm(word)
        pu = (self.uni[word] + 1) / (self.n_uni + len(self.vocab))
        c = self.big.get(prev)
        pb = c[word] / sum(c.values()) if c else 0.0
        return math.log(self.lam * pb + (1 - self.lam) * pu)

    def uniform(self):
        return math.log(1.0 / len(self.vocab))

    @classmethod
    def default(cls, vocab, sentences=None):
        sents = sentences if sentences is not None else (
            [g for g, _en, _m in load_corpus()] + [list(k) for k in load_phrases()])
        return cls(sents, vocab)


def norm(g):
    return "FS" if g.startswith("FS:") or g.startswith("FS_") else g


def merge_fingerspelling(glosses):
    """FS_R FS_A FS_M -> FS:RAM (letters from the fingerspelling recogniser become one name)."""
    out = []
    for g in glosses:
        if g.startswith("FS_") and out and out[-1].startswith("FS:"):
            out[-1] += g[3:]
        elif g.startswith("FS_"):
            out.append("FS:" + g[3:])
        else:
            out.append(g)
    return out


def beam_decode(events, lm, w_model=1.0, w_lm=0.3, drop_scale=0.3, beam=12):
    """events: list[SignEvent] -> best gloss list."""
    beams = [(0.0, ["<s>"])]
    for ev in events:
        top = ev.nbest[0][1] if ev.nbest else 0.0
        cand = []
        for score, seq in beams:
            prev = seq[-1]
            for g, p in ev.nbest:
                if g == "REST":
                    continue
                if g == prev and not g.startswith("FS_"):          # a held sign detected twice: merge,
                    cand.append((score + w_model * math.log(max(p, 1e-6)) + w_lm * lm.uniform(), seq))
                    continue                                       # but it still costs its probability
                s = score + w_model * math.log(max(p, 1e-6)) + w_lm * lm.logp(prev, g)
                cand.append((s, seq + [g]))
            # dropping the event = it was a false detection: likely only if the model was unsure.
            # The uniform-LM term keeps the number of LM factors equal to the 'keep' paths.
            p_drop = max(0.005, (1.0 - top) * drop_scale)
            cand.append((score + w_model * math.log(p_drop) + w_lm * lm.uniform(), seq))
        cand.sort(key=lambda x: -x[0])
        seen, beams = set(), []
        for s, seq in cand:
            key = tuple(seq)
            if key not in seen:
                seen.add(key)
                beams.append((s, seq))
            if len(beams) >= beam:
                break
    best = max(beams, key=lambda b: b[0] + w_lm * lm.logp(b[1][-1], "</s>"))
    return merge_fingerspelling(best[1][1:])


class SentenceBuilder:
    """Collects SignEvents, closes a sentence after `gap` seconds without a new sign, then decodes.

    Non-manual markers (camera only) are accumulated with add_nonmanual(): brows raised for most of
    the sentence -> yes/no question; head shaking -> negation.
    """

    def __init__(self, translator, lm, gap=2.0, w_lm=0.3):
        self.tr, self.lm, self.gap, self.w_lm = translator, lm, gap, w_lm
        self.events, self.last_t = [], None
        self.brow, self.shake, self.nm_n = 0.0, 0.0, 0

    def add(self, ev):
        self.events.append(ev)
        self.last_t = ev.t

    def add_nonmanual(self, brow_raise, head_shake):
        if self.events:                        # only while a sentence is in progress
            self.brow += brow_raise
            self.shake = max(self.shake, head_shake)
            self.nm_n += 1

    def partial(self):
        g = beam_decode(self.events, self.lm, w_lm=self.w_lm) if self.events else []
        return g

    def poll(self, now, force=False):
        """Returns a Sentence when the current one is finished, else None."""
        if not self.events or (not force and now - self.last_t < self.gap):
            return None
        g = beam_decode(self.events, self.lm, w_lm=self.w_lm)
        yn = self.nm_n > 0 and self.brow / self.nm_n > 0.5
        neg = self.shake > 0.5
        s = Sentence(g, self.tr(g, yn=yn, neg=neg), list(self.events), yn, neg)
        self.events, self.last_t = [], None
        self.brow, self.shake, self.nm_n = 0.0, 0.0, 0
        return s
