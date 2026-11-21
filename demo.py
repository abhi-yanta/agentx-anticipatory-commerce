import sys, time
from evaluate import Tools
from my_agent import Agent
from search import load_catalogue

req = " ".join(sys.argv[1:])
cat = {p["product_id"]: p for p in load_catalogue()}
agent = Agent(Tools())
agent.start("demo")
for i, w in enumerate(req.split(), 1):
    out = agent.observe(w)
    _, f = agent.parse()
    note = f"  >>> COMMIT {out['commit']}" if out else ""
    print(f"{i:2} {w:12} {f}{note}")
    time.sleep(0.5)
pid = agent.finish()
print("\nFINAL:", pid, cat[pid]["title"] if pid else None)
