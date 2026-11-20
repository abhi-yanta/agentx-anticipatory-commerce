import re
from search import load_catalogue

UNITS = {w: i for i, w in enumerate(
    "zero one two three four five six seven eight nine ten eleven twelve thirteen "
    "fourteen fifteen sixteen seventeen eighteen nineteen".split())}
TENS = {w: 10 * (i + 2) for i, w in enumerate(
    "twenty thirty forty fifty sixty seventy eighty ninety".split())}
SIZE_WORDS = {"small": "s", "medium": "m", "large": "l", "xl": "xl", "xxl": "xxl", "xs": "xs"}
MARKERS = {"no", "wait", "actually", "instead", "sorry", "change", "make", "not"}


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

    def start(self, request_id):
        self.words, self.last_key, self.committed, self.pending = [], None, None, None

    def parse(self):
        text = " ".join(numify(self.words)).lower()
        text = re.sub(r"(\d+)\s*k\b", lambda m: str(int(m.group(1)) * 1000), text)
        for a, b in (("double extra large", "xxl"), ("extra extra large", "xxl"),
                     ("extra large", "xl"), ("extra small", "xs")):
            text = text.replace(a, b)
        f = {}
        for field, values in self.vocab.items():
            spots = []
            for v in values:
                forms = [v, v[:-1]] if field == "category" and v.endswith("s") else [v]
                spots += [(m.start(), v) for x in forms
                          for m in re.finditer(rf"\b{re.escape(x)}\b", text)]
            if spots:
                f[field] = max(spots)[1]
        sz = re.findall(r"\b(?:size|uk|waist)\s+([a-z0-9]+)\b", text)
        if sz and sz[-1] in self.sizes:
            f["size"] = self.sizes[sz[-1]]
        else:
            for w in reversed(text.split()):
                if w in SIZE_WORDS and SIZE_WORDS[w] in self.sizes:
                    f["size"] = self.sizes[SIZE_WORDS[w]]; break
        b = re.findall(r"\b(?:under|below|less than|within|max|up to|budget)\s+"
                       r"(?:rs\.?\s*|₹)?([\d,]+)\b", text)
        if b:
            f["max_price"] = int(b[-1].replace(",", ""))
        return text, f

    def observe(self, word):
        self.words.append(word.lower())
        if self.committed or word.lower() in MARKERS:
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
            if self.pending == pid:        # same unique product seen twice in a row
                self.committed = pid
                return {"commit": pid}
            self.pending = pid
        else:
            self.pending = None
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