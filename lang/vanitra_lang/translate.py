"""ISL gloss sentence -> English sentence (rule-based, offline, explainable).

ISL grammar this follows (docs/isl_language.md):
  * time signs come first and carry tense  (YESTERDAY / TOMORROW / NOW ...; no verb inflection)
  * the predicate comes last (SOV):           I WATER WANT          -> I want water.
  * wh-signs come at the end:                 YOU GO WHERE          -> Where are you going?
  * negation comes at the end:                I UNDERSTAND NOT      -> I don't understand.
  * modals come after the verb:               YOU HELP CAN QUESTION -> Can you help?
  * FINISH after a verb = completed action:   I EAT FINISH          -> I have eaten.
  * no articles, no copula (be):              I SICK                -> I am sick.
  * yes/no questions are marked by the FACE (raised brows). The camera detects this; with gloves only,
    sign the general QUESTION sign at the end.
English adds what ISL leaves to context: articles, be/do/have, tense endings, word order.
"""
from .lexicon import Lexicon, load_phrases

BE = {"1s": ("am", "was"), "2": ("are", "were"), "3s": ("is", "was"), "1p": ("are", "were"), "3p": ("are", "were")}
NEG = {"am": "am not", "is": "isn't", "are": "aren't", "was": "wasn't", "were": "weren't", "do": "don't",
       "does": "doesn't", "did": "didn't", "can": "can't", "will": "won't", "have": "haven't", "has": "hasn't",
       "must": "mustn't"}
WH_NO_PRED = ("WHAT", "WHO", "WHERE", "WHEN", "HOW", "WHICH", "WHY")


class Subject:
    def __init__(self, text, person, pron=None):
        self.text, self.person, self.pron = text, person, pron


class Translator:
    def __init__(self, lex=None, phrases=None):
        self.lex = lex or Lexicon()
        self.phrases = load_phrases() if phrases is None else phrases

    # ------------------------------------------------------------------ helpers
    def e(self, g):
        e = self.lex.get(g)
        if e is None:                                         # unknown gloss: say it as a noun
            from .lexicon import Entry
            w = g.lower().replace("-", " ")
            e = Entry(g, w, "noun", [w, w + "s"], set())
        return e

    def np(self, g, role, motion=False, definite=False):
        e = self.e(g)
        if e.pos == "pron":
            return e.forms[1] if role != "subj" else e.forms[0]
        if e.has("proper"):
            return e.en
        if e.has("place") and motion:
            if g == "HOME":
                return "home"
            return f"to {e.en}" if e.has("bare") else f"to the {e.en}"
        if role == "subj" or definite or e.has("definite") or e.has("place"):
            return f"the {e.en}" if not e.has("bare") or role == "subj" else e.en
        if e.has("mass"):
            return e.en
        return ("an " if e.en[0] in "aeiou" else "a ") + e.en

    # ------------------------------------------------------------------ public
    def __call__(self, glosses, yn=False, neg=False):
        toks = [g for g in glosses if g and g != "REST"]
        if not toks:
            return ""
        key = tuple(toks)
        if key in self.phrases and not neg:
            out = self.phrases[key]
            return out[:-1] + "?" if yn and out[-1] in ".!" else out
        before, after = [], []
        while len(toks) > 1 and self.e(toks[0]).pos == "interj" and toks[0] != "PLEASE":
            before.append(self.e(toks[0]).forms[0])
            toks = toks[1:]
        while len(toks) > 1 and toks[-1] in ("THANK-YOU", "SORRY", "BYE"):
            after.insert(0, self.e(toks[-1]).forms[0])
            toks = toks[:-1]
        please = "PLEASE" in toks and len(toks) > 1
        if please:
            toks = [t for t in toks if t != "PLEASE"]
        if tuple(toks) in self.phrases and not neg:
            core = self.phrases[tuple(toks)]
            if please and core.endswith("."):
                core = core[:-1] + ", please."
        else:
            core = self.clause(toks, yn, neg, please)
        return " ".join(before + [core] + after).strip()

    # ------------------------------------------------------------------ one clause
    def clause(self, toks, yn, neg, please):
        tense, times, wh, modal, perfect, never, adv, core = None, [], None, None, False, False, [], []
        for t in toks:
            e = self.e(t)
            if e.pos == "time":
                if e.forms:
                    tense = tense or e.forms[0]
                times.append(e.en)
            elif e.pos == "wh":
                wh = t
            elif e.pos == "qmark":
                yn = True
            elif e.pos == "neg":
                if t == "NEVER":
                    never = True
                    continue
                neg = True
                if t == "CAN-NOT":
                    modal = "can"
                elif t == "DONT-WANT":
                    core.append("WANT")
            elif e.pos == "modal":
                modal = e.en
            elif e.pos == "aspect":
                perfect = True
            elif e.pos == "adv":
                adv.append(e.en)
            elif e.pos == "interj":
                continue
            else:
                core.append(t)

        preds = [i for i, t in enumerate(core) if self.e(t).pos in ("verb", "adj")]
        if not preds and modal:                          # YOU TICKET MUST -> You must have a ticket.
            core.append("HAVE")
            preds = [len(core) - 1]
        pi = preds[-1] if preds else None
        if pi is None and perfect:
            core.append("FINISH")
            pi = len(core) - 1
            perfect = True
        pred = core[pi] if pi is not None else None
        pre = core[:pi] if pred else list(core)
        post = core[pi + 1:] if pred else []
        pe = self.e(pred) if pred else None
        if pred == "FINISH":
            perfect = True

        # infinitive complement: I HOME GO WANT -> I want to go home
        comp = None
        if pe and pe.has("takes_inf"):
            vis = [i for i, t in enumerate(pre) if self.e(t).pos == "verb"]
            if vis and not (pre[vis[-1]] == "HELP" and pe.has("takes_noun") and vis[-1] == len(pre) - 1
                            and len(pre) <= 2):
                comp = pre[vis[-1]]
                pre = pre[:vis[-1]] + pre[vis[-1] + 1:]

        # subject
        subj, rest = None, list(pre)
        if rest and self.e(rest[0]).pos == "pron":
            p = self.e(rest.pop(0))
            rel_ok = pred is None or pe.pos == "adj"
            if rest and self.e(rest[0]).has("relational") and rel_ok and wh != "HOW-MANY":
                n = self.e(rest.pop(0))
                subj = Subject(f"{p.forms[2]} {n.en}", "3s")
            else:
                subj = Subject(p.forms[0], p.forms[5], p)
        elif rest and self.e(rest[0]).pos == "noun":
            n = self.e(rest[0])
            if n.has("person") or n.has("proper") or (pred is None and wh) or (pe and pe.pos == "adj"):
                rest.pop(0)
                subj = Subject(self.np(n.gloss, "subj"), "3p" if n.gloss == "POLICE" else "3s")
        objects = [t for t in rest + post if self.e(t).pos in ("noun", "pron", "verb")]

        imperative = False
        if subj is None:
            if wh or yn:
                subj = Subject("you", "2")
            elif pred and pe.has("imperative") and not tense and not modal and not perfect:
                imperative = True
            elif pred is not None:
                subj = Subject("I", "1s")

        if (subj and subj.text == "you" and please and pe is not None and pe.has("imperative")
                and not (wh or yn or tense or modal or perfect)):
            subj, imperative = None, True                  # YOU SIT PLEASE -> Please sit.

        motion = bool(pe and pe.has("motion")) or (comp is not None and self.e(comp).has("motion"))
        poss = subj.pron.forms[2] if subj and subj.pron else None

        def obj(t):
            e = self.e(t)
            if poss and e.has("relational") and not (motion and e.has("place")) and pred != "HAVE":
                return f"{poss} {e.en}"                    # I FRIEND CALL MUST -> I must call my friend.
            return self.np(t, "obj", motion=motion, definite=perfect)
        obj_txt = " ".join(obj(t) for t in objects)
        tail = " ".join(x for x in [obj_txt] + adv + times if x)
        end = "?" if (wh or yn) else "."

        # ---- no predicate: "YOU NAME WHAT", "TOILET WHERE", "YOU WHO", fragments
        if pred is None:
            if wh == "HOW-MANY" and objects:
                n = self.e(objects[0])
                who = subj.text if subj else "you"
                aux = "does" if subj and subj.person == "3s" else "do"
                return cap(f"how many {n.forms[1]} {aux} {who} have?")
            if wh in WH_NO_PRED and subj:
                be = BE[subj.person][1 if tense == "past" else 0]
                return cap(f"{self.e(wh).en} {be} {subj.text}" + (f" {tail}" if tail else "") + "?")
            if subj and objects and not wh:                # I NAME FS:MANAS -> My name is Manas.
                o = self.e(objects[0])
                if o.has("proper") or o.has("person"):
                    be = BE[subj.person][1 if tense == "past" else 0]
                    pred_np = o.en if o.has("proper") else self.np(o.gloss, "obj")
                    return cap(f"{subj.text} {be} {'not ' if neg else ''}{pred_np}" + end)
            words = [subj.text] if subj else []
            words += [obj_txt] if obj_txt else []
            if wh:
                return cap(" ".join([self.e(wh).en] + words) + "?")
            s = " ".join(words + adv + times) or toks[0].lower()
            return cap(s + (", please" if please else "") + end)

        # ---- imperative: WAIT PLEASE -> Please wait.
        if imperative:
            v = pe.forms[0] if pe.pos == "verb" else f"be {pe.en}"
            s = ("don't " if neg else "") + v + (f" {tail}" if tail else "")
            return cap(("please " if please else "") + s + ".")

        person = subj.person
        third = person == "3s"
        q = bool(wh or yn)

        # ---- auxiliary + main verb
        if pe.pos == "adj":
            if modal:
                aux, main = modal, f"be {pe.en}"
            elif tense == "future":
                aux, main = "will", f"be {pe.en}"
            else:
                aux, main = BE[person][1 if tense == "past" else 0], pe.en
        else:
            base, s3, past, pp, ing = pe.forms
            stative = pe.has("stative") or never
            if modal:
                aux, main = modal, base
            elif perfect:
                aux, main = ("has" if third else "have"), pp
            elif tense == "past":
                aux, main = ("did", base) if (neg or q) else (None, past)
            elif tense == "future":
                aux, main = "will", base
            elif stative:
                aux, main = (("does" if third else "do"), base) if (neg or q) else (None, s3 if third else base)
            else:
                aux, main = BE[person][0], ing
            if comp:
                ce = self.e(comp)
                main += f" to {ce.forms[0]}"
        if never:
            main = "never " + main
            neg = False

        # wh as object: YOU WANT WHAT -> What do you want?
        whw = self.e(wh).en if wh else None
        if wh == "HOW-MANY" and objects:
            whw = f"how many {self.e(objects[0]).forms[1]}"
            tail = " ".join(adv + times)
        if q:
            a = aux or ("does" if third else "do")
            a = NEG.get(a, a + " not") if neg else a
            body = " ".join(x for x in [a, subj.text, main, tail] if x)
            return cap((whw + " " if whw else "") + body + "?")
        a = (NEG.get(aux, aux + " not") if neg else aux) if aux else None
        if neg and aux is None:
            a = "didn't" if tense == "past" else ("doesn't" if third else "don't")
            main = pe.forms[0]
        body = " ".join(x for x in [subj.text, a, main, tail] if x)
        return cap(body + (", please" if please else "") + end)


def cap(s):
    s = " ".join(s.split())
    return s[:1].upper() + s[1:] if s else s


_default = None


def translate(glosses, yn=False, neg=False):
    global _default
    if _default is None:
        _default = Translator()
    return _default(glosses, yn, neg)
