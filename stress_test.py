import random, sys
from evaluate import run, summarise, load_agent
from search import load_catalogue, search

random.seed(int(sys.argv[1]) if len(sys.argv) > 1 else 1)
cat = load_catalogue()
colours = sorted({p["colour"] for p in cat if p["colour"]})
LEADS = ["I want", "show me", "looking for", "get me", "do you have"]
TAILS = ["", "for my dad", "as a gift", "for office", "this week"]
CUES = ["scratch that", "no no", "on second thought", "forget that", "never mind",
        "cancel that", "I take that back", "hmm no", "wait", "actually"]
KINDS = ["plain", "correction", "late_constraint"]


def build(p, kind):
    cap = (p["price"] // 500 + 1) * 500
    f = {"category": p["category"], "colour": p["colour"], "brand": p["brand"], "max_price": cap}
    size = f"size {p['size']}" if p["size"] else ""
    if p["size"]:
        f["size"] = p["size"]
    if len(search("", f, k=2)) != 1:
        return None, None
    lead, tail = random.choice(LEADS), random.choice(TAILS)
    c, b, cat_w = p["colour"], p["brand"], p["category"]
    if kind == "plain":
        text = f"{lead} {c} {b} {cat_w} {size} under {cap} {tail}"
    elif kind == "correction":
        wrong = random.choice([x for x in colours if x != c])
        text = f"{lead} {wrong} {b} {cat_w} {size} under {cap}, {random.choice(CUES)}, {c} {tail}"
    else:
        text = f"{lead} {b} {cat_w} {size} under {cap} and in {c} {tail}"
    return " ".join(text.split()), f


reqs, texts, tries = [], {}, 0
while len(reqs) < 300 and tries < 50000:
    tries += 1
    kind = KINDS[len(reqs) % 3]
    p = random.choice(cat)
    text, f = build(p, kind)
    if not text:
        continue
    rid = f"gen-{len(reqs)}"
    texts[rid] = text
    reqs.append({"id": rid, "words": text.split(), "target": p["product_id"], "tags": [kind]})

res, _ = run(load_agent("my_agent.py"), reqs)
s = summarise(res)
print(f"requests {s['requests']}  accuracy {s['accuracy']:.3f}  wrong commits {s['wrong_commits']}  "
      f"earliness {s['early_share']:.1%}  wasted searches {s['wasted']:.2f}  SCORE {s['score']:.1f}")
for k in KINDS:
    t = summarise([r for r in res if k in r["tags"]])
    print(f"  {k:16} accuracy {t['accuracy']:.3f}  wrong {t['wrong_commits']}  score {t['score']:.1f}")
print("\nwrong commits:")
for r in [x for x in res if x["wrong_commits"]][:10]:
    print(" ", r["id"], r["commits"], r["target"], "|", texts[r["id"]])
print("\nwrong final answers:")
for r in [x for x in res if not x["correct"]][:10]:
    print(" ", r["id"], r["final"], r["target"], "|", texts[r["id"]])