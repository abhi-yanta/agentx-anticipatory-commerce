# Architecture: SafeCommit (AgentX Challenge 1)

**Competition ID:** AX-283FB72B9A7E

## How it works
Word arrives -> clean text and convert numbers (English and Hindi) -> extract filters
-> if the filters changed, run a local search -> if exactly one product matches,
update the confidence counter -> commit or wait. When the request ends, finish()
re-parses the full request and gives the final answer.

## Components
1. **Normaliser:** converts number words ("two thousand five hundred", "saadhe teen
   hazaar" = 3500), "3.5k" and "double XL" (= XXL).
2. **Extractor:** aliases are built from catalogue.csv plus a synonym table
   ("floaters" = sandals, "kaala" = black). The longest match wins and a matched span
   cannot be reused, so "navy blue" is not read as "blue".
3. **Size and budget parser:** reads "size 9", "UK 10", "das number", "under / within /
   not more than", "1500 tak".
4. **Commit rule (confidence score):** commit only when category and budget are known,
   the search returns exactly one product, and the same product holds on 3 words in a
   row (NEED = 3).
5. **Correction guard:** after cues like "wait", "actually", "sorry", "I meant",
   "no, change that", "matlab", the agent stops committing. The answer then comes from
   finish(), which re-parses the whole request (the last mention wins).
6. **Search budget:** a search runs only when the extracted filters change.

## Why these choices
- A wrong commit costs -1.0, while earliness is worth at most 0.6 x its share of the
  request, so the agent commits only when the match is unique and stable.
- We tested NEED = 2: 4 wrong commits. NEED = 3: 0 wrong commits. We kept 3.
- Rule-based with no LLM: about 0.14 ms per word, no running cost, deterministic.

## Results (dev.jsonl, 300 requests)
| Version | Accuracy | Wrong commits | Earliness | Searches/req | Score |
|---|---|---|---|---|---|
| Baseline | 0.527 | 0 | 0.0% | 1.53 | 20.0 |
| v1 | 0.623 | 6 | 1.0% | 2.19 | 21.1 |
| v2 | 0.883 | 16 | 3.6% | 2.11 | 29.9 |
| v3 | 0.947 | 0 | 1.6% | 2.30 | 36.2 |
| v4 | 1.000 | 0 | 2.1% | 2.59 | 38.1 |
| v5 (final) | 1.000 | 0 | 2.0% | 1.90 | 39.4 |

## Limitations
The vocabulary is rule-based and was tuned on the dev set, so unseen phrasings can
fail. Next steps: an LLM fallback for unknown phrases, and a learned commit-confidence
model.
