"""Tests for the language layer.   python lang/tests/test_lang.py   (or: pytest lang/tests)"""
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "ml"))

from vanitra_lang import (BigramLM, Lexicon, SentenceBuilder, SignEvent, Translator, beam_decode,  # noqa: E402
                          load_corpus, merge_fingerspelling)


def test_corpus_translations():
    tr = Translator()
    bad = []
    for g, en, m in load_corpus():
        out = tr(g, yn="YN" in m, neg="NEG" in m)
        if out != en:
            bad.append((" ".join(g), out, en))
    assert not bad, "\n".join(f"{g}: got {o!r}, want {e!r}" for g, o, e in bad)


def test_every_corpus_gloss_is_in_lexicon():
    lex = Lexicon()
    missing = {t for g, _e, _m in load_corpus() for t in g if t not in lex}
    assert not missing, missing


def test_vocabulary_glosses_are_in_lexicon():
    import csv
    lex = Lexicon()
    path = os.path.join(os.path.dirname(__file__), "..", "..", "ml", "vocabulary.csv")
    with open(path, newline="", encoding="utf-8") as f:
        labels = [r["label"] for r in csv.DictReader(f)]
    missing = [l for l in labels if l != "REST" and l not in lex]
    assert not missing, missing


def test_fingerspelling_merge():
    assert merge_fingerspelling(["I", "NAME", "FS_R", "FS_A", "FS_M"]) == ["I", "NAME", "FS:RAM"]
    assert Translator()(["I", "NAME", "FS:RAM"]) == "My name is Ram."


def test_lm_fixes_a_wrong_top_guess():
    lex = Lexicon()
    lm = BigramLM.default(lex.glosses())
    # the recogniser's top guess for the 3rd sign is WHERE (0.48) but WANT (0.42) makes sense here
    evs = [SignEvent(0.0, [("I", 0.9), ("YOU", 0.05)]),
           SignEvent(1.0, [("WATER", 0.8), ("FOOD", 0.1)]),
           SignEvent(2.0, [("WHERE", 0.48), ("WANT", 0.42), ("WAIT", 0.05)])]
    assert beam_decode(evs, lm) == ["I", "WATER", "WANT"]


def test_lm_keeps_a_confident_guess():
    lm = BigramLM.default(Lexicon().glosses())
    evs = [SignEvent(0.0, [("TOILET", 0.95)]), SignEvent(1.0, [("WHERE", 0.9), ("WANT", 0.05)])]
    assert beam_decode(evs, lm) == ["TOILET", "WHERE"]


def test_spurious_low_confidence_event_dropped():
    lm = BigramLM.default(Lexicon().glosses())
    evs = [SignEvent(0.0, [("I", 0.95)]), SignEvent(0.5, [("TRAIN", 0.30), ("BUS", 0.25)]),
           SignEvent(1.0, [("HUNGRY", 0.9)])]
    assert beam_decode(evs, lm) == ["I", "HUNGRY"]


def test_sentence_builder_and_nonmanual_question():
    lex = Lexicon()
    sb = SentenceBuilder(Translator(lex), BigramLM.default(lex.glosses()), gap=1.5)
    sb.add(SignEvent(0.0, [("YOU", 0.9)]))
    sb.add_nonmanual(brow_raise=1.0, head_shake=0.0)
    sb.add(SignEvent(0.8, [("HUNGRY", 0.9)]))
    sb.add_nonmanual(brow_raise=1.0, head_shake=0.0)
    assert sb.poll(1.0) is None
    s = sb.poll(3.0)
    assert s.glosses == ["YOU", "HUNGRY"] and s.english == "Are you hungry?"


def test_noisy_sentences_held_out():
    """A simulated recogniser that is right 85 % of the time. The LM is trained on HALF the corpus and
    tested on the OTHER half, so this measures generalisation, not memorisation."""
    lex = Lexicon()
    corpus = [g for g, _e, _m in load_corpus() if not any(t.startswith("FS") for t in g)]
    order = list(range(len(corpus)))
    random.Random(1).shuffle(order)
    train = [corpus[i] for i in order[: len(order) // 2]]
    test = [corpus[i] for i in order[len(order) // 2:]]
    lm = BigramLM.default(lex.glosses(), train)
    vocab = [g for g in lex.glosses() if lex.get(g).pos != "interj"]
    raw_ok = lm_ok = 0
    for seed in range(3):
        rng = random.Random(seed)
        for g in test:
            evs = []
            for t in g:
                wrong = rng.choice(vocab)
                if rng.random() < 0.85:
                    nb = [(t, rng.uniform(0.5, 0.9)), (wrong, rng.uniform(0.05, 0.3))]
                else:
                    nb = [(wrong, rng.uniform(0.4, 0.6)), (t, rng.uniform(0.25, 0.4))]
                evs.append(SignEvent(0, sorted(nb, key=lambda x: -x[1])))
            raw_ok += [e.nbest[0][0] for e in evs] == g
            lm_ok += beam_decode(evs, lm) == g
    print(f"     held-out sentences fully correct: top-guess {raw_ok}/{3 * len(test)}, "
          f"with LM {lm_ok}/{3 * len(test)}")
    assert lm_ok > raw_ok


if __name__ == "__main__":
    fails = 0
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            try:
                fn()
                print("ok  ", name)
            except AssertionError as e:
                fails += 1
                print("FAIL", name, e)
    sys.exit(1 if fails else 0)
