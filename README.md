# AgentX: Anticipatory Commerce (Techfest 2026-27)

Shopping agent that predicts product filters from a partial request, searches early,
and commits only when confident.

**Team:** Abhinav Jaiswal
**Competition ID:** AX-283FB72B9A7E

## Approach
- Word-by-word filter extraction (category, colour, size, budget, brand)
- Synonyms and Hindi-English support ("floaters", "kaala", "saadhe teen hazaar")
- Confidence rule: commit only when one product matches on 3 words in a row
- Correction guard: stops committing on "wait", "actually", "I meant", "no, change that"
- Searches run only when the filters change

## Results (dev.jsonl, 300 requests)
| Version | Accuracy | Wrong commits | Earliness | Searches/req | Score |
|---|---|---|---|---|---|
| Baseline | 0.527 | 0 | 0.0% | 1.53 | 20.0 |
| Final | 1.000 | 0 | 2.0% | 1.90 | 39.4 |

## Run
```
python evaluate.py --agent my_agent.py
python demo.py "show me black running shoes size 9 under 2000"
```

See ARCHITECTURE.md for the better design.