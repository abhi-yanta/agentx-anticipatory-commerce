import re
from search import load_catalogue

UNITS = {w: i for i, w in enumerate(
    "zero one two three four five six seven eight nine ten eleven twelve thirteen "
    "fourteen fifteen sixteen seventeen eighteen nineteen".split())}
TENS = {w: 10 * (i + 2) for i, w in enumerate(
    "twenty thirty forty fifty sixty seventy eighty ninety".split())}
SIZE_WORDS = {"small": "s", "medium": "m", "large": "l", "xs": "xs", "s": "s",
              "m": "m", "l": "l", "xl": "xl", "xxl": "xxl", "2xl": "xxl"}
MARKERS = {"no", "wait", "actually", "instead", "sorry", "change", "make", "not", "oops", "oh"}
BLOCKERS = {"no", "wait", "actually", "sorry", "oops", "mean", "meant", "matlab",
            "nahi", "instead", "change", "make", "rather"}
SYNONYMS = {
    "category": {
        "t-shirts": ["tee", "tees", "tshirt", "tshirts", "t shirt", "t shirts"],
        "hoodies": ["hooded sweatshirt", "hooded sweatshirts", "hoodie"],
        "sandals": ["floaters", "floater", "slides", "slide"],
        "track pants": ["joggers", "jogger", "trackpants", "track pant"],
        "running shoes": ["jogging shoes", "jogging shoe", "running sneakers",
                          "running sneaker", "runners"],
    },
    "colour": {"grey": ["gray"], "navy": ["navy blue"], "olive": ["olive green"]},
}


def numify(words):
    out, total, cur, active = [], 0, 0, False
    for w in words:
        if w in UNITS or w in TENS:
            cur += UNITS.get(w, TENS.get(w)); active = True
        elif w == "hundred" and active:
            cur = (cur or 1) * 100
        elif w in ("thousand", "grand") and active:
            total += (cur or 1) * 1000; cur = 0
        else:
            if active:
                out.append(str(total + cur)); total = cur = 0; active = False
            out.append(w)
    if active:
        out.append(str(total + cur))
    return out


class Agent:
    def __init__(self, tools):
        self.tools = tools
        cat = load_catalogue()
        self.vocab = {f: sorted({p[f].lower() for p in cat if p[f]}, key=len, reverse=True)
                      for f in ("category", "colour", "brand")}
        self.sizes = {p["size"].lower(): p["size"] for p in cat if p["size"]}
        self.aliases = []
        for field, values in self.vocab.items():
            for v in values:
                forms = {v, v.replace("-", " ")}
                if field == "category" and v.endswith("s"):
                    forms |= {v[:-1], v[:-1].replace("-", " ")}
                for x in forms:
                    self.aliases.append((x, field, v))
        for field, d in SYNONYMS.items():
            for canon, alts in d.items():
                if canon in self.vocab[field]:
                    for x in alts:
                        self.aliases.append((x, field, canon))
        self.aliases.sort(key=lambda a: -len(a[0]))

    def start(self, request_id):
        self.words, self.last_key, self.committed = [], None, None
        self.pending, self.count, self.blocked, self.prev = None, 0, False, ""

    def find(self, text):
        taken = [False] * len(text)
        best = {}
        for alias, field, canon in self.aliases:
            for m in re.finditer(rf"(?<![a-z0-9]){re.escape(alias)}(?![a-z0-9])", text):
                s, e = m.span()
                if any(taken[s:e]):
                    continue
                for i in range(s, e):
                    taken[i] = True
                if field not in best or s > best[field][0]:
                    best[field] = (s, canon)
        return {k: v[1] for k, v in best.items()}

    def parse(self):
        text = " ".join(numify(self.words)).lower()
        text = re.sub(r"(\d+(?:\.\d+)?)\s*k\b",
                      lambda m: str(int(round(float(m.group(1)) * 1000))), text)
        for a, b in (("double extra large", "xxl"), ("extra extra large", "xxl"),
                     ("double xl", "xxl"), ("extra large", "xl"), ("extra small", "xs")):
            text = text.replace(a, b)
        f = self.find(text)
        toks = text.split()
        for i, w in enumerate(toks):
            cand = SIZE_WORDS.get(w)
            if cand is None and w.isdigit() and (
                    (i > 0 and toks[i - 1] in ("size", "uk", "waist"))
                    or (i + 1 < len(toks) and toks[i + 1] == "uk")):
                cand = w
            if cand and cand in self.sizes:
                f["size"] = self.sizes[cand]
        b = re.findall(r"\b(?:under|below|less than|within|max|maximum|up to|upto|budget|"
                       r"not more than|no more than|at most)\s+(?:rs\.?\s*|₹)?(\d[\d,]*)", text)
        if b:
            f["max_price"] = int(b[-1].replace(",", "") or 0)
        return text, f

    def observe(self, word):
        w = word.lower().strip(",.;:!?\"'()[]")
        if not w:
            return None
        self.words.append(w)
        if self.prev == "no" and w != "more":      # "no more than" is a budget, not a correction
            self.blocked = True
        if w in BLOCKERS and w != "no":
            self.blocked = True
        self.prev = w
        if self.committed or self.blocked or w in MARKERS:
            return None
        text, f = self.parse()
        if len(f) < 4 or "category" not in f or "max_price" not in f:
            return None
        key = tuple(sorted(f.items()))
        if key == self.last_key and self.pending is None:
            return None
        self.last_key = key
        hits = self.tools.search(text, f, k=2)
        if len(hits) == 1:
            pid = hits[0]["product_id"]
            if self.pending == pid:
                self.count += 1
            else:
                self.pending, self.count = pid, 1
            if self.count >= 3:                    # same unique product on 3 words in a row
                self.committed = pid
                return {"commit": pid}
        else:
            self.pending, self.count = None, 0
        return None

    def finish(self):
        if self.committed:
            return self.committed
        text, f = self.parse()
        for drop in (None, "max_price", "size", "brand", "colour", "category"):
            f.pop(drop, None)
            hits = self.tools.search(text, f, k=1)
            if hits:
                return hits[0]["product_id"]
        return None