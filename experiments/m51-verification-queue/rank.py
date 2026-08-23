"""Rank the NOT INDEPENDENTLY VERIFIED backlog in SYNTHESIS.md by consequence.

Discipline 294's corollary is that the tag is a standing work queue. A queue
nobody has ordered is a queue nobody works, so this orders it.

Consequence proxy, in priority order:
  1. cited by shipped Rust source under crates/  (a wrong fact here is a shipped defect)
  2. cited by other facts/disciplines/questions in SYNTHESIS (structural load)
  3. neither (measured, recorded, currently load-bearing on nothing)

Both signals are proxies and the second is the weaker one: a fact can be
load-bearing through prose that never writes "fact N". Treat the ranking as a
starting order, not an authority. Read-only; writes only to data/.

Usage: python experiments/m51-verification-queue/rank.py
"""

import collections
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(".")
SYN = ROOT / "docs/research/SYNTHESIS.md"
OUT = pathlib.Path(__file__).parent / "data"
TAG = "NOT INDEPENDENTLY VERIFIED"

t = SYN.read_text(encoding="utf-8")

m = re.search(r"^## 4\. ", t, re.M)
if not m:
    sys.exit("FATAL: section 4 not found")
nxt = re.compile(r"^## ", re.M).search(t, m.end())
sec = t[m.end(): (nxt.start() if nxt else len(t))]

rows = {int(x.group(1)): x.group(2) for x in re.finditer(r"^\| (\d+) \|(.*)$", sec, re.M)}
if not rows:
    sys.exit("FATAL: no fact rows parsed")
tagged = sorted(n for n, r in rows.items() if TAG in r)

# The phrase also appears outside fact rows; count findings, not occurrences.
occurrences = t.count(TAG)

cites = collections.Counter()
for x in re.finditer(r"facts? (\d+(?:[-\u2013]\d+)?(?:,\s*\d+)*)", t):
    for part in re.split(r",\s*", x.group(1)):
        rng = re.match(r"^(\d+)[-\u2013](\d+)$", part)
        if rng:
            lo, hi = int(rng.group(1)), int(rng.group(2))
            if hi - lo < 60:  # a wide range is a gesture, not a citation
                for k in range(lo, hi + 1):
                    cites[k] += 1
        elif part.isdigit():
            cites[int(part)] += 1

code = "\n".join(
    p.read_text(encoding="utf-8", errors="replace") for p in ROOT.glob("crates/**/*.rs")
)
in_code = {int(x.group(1)) for x in re.finditer(r"fact (\d+)", code, re.I)}


def headline(row):
    h = re.search(r"\*\*(.+?)\*\*", row)
    return (h.group(1) if h else row.strip())[:150]


ranked = sorted(tagged, key=lambda n: (-int(n in in_code), -cites[n], n))
records = [
    {
        "fact": n,
        "in_code": n in in_code,
        "cited_by": cites[n],
        "headline": headline(rows[n]),
    }
    for n in ranked
]

OUT.mkdir(parents=True, exist_ok=True)
(OUT / "verification-queue.json").write_text(
    json.dumps(
        {
            "total_facts": len(rows),
            "tagged_facts": len(tagged),
            "tag_occurrences_in_file": occurrences,
            "tagged_and_in_code": sum(1 for r in records if r["in_code"]),
            "tagged_and_uncited": sum(
                1 for r in records if not r["in_code"] and r["cited_by"] == 0
            ),
            "queue": records,
        },
        indent=2,
    ),
    encoding="utf-8",
)

print(f"facts {len(rows)} | tagged {len(tagged)} | tag occurrences in file {occurrences}")
print(f"tagged AND relied on by shipped code: {sum(1 for r in records if r['in_code'])}")
print(f"tagged AND cited nowhere:             "
      f"{sum(1 for r in records if not r['in_code'] and r['cited_by'] == 0)}")
print()
print(f"{'fact':>5} {'code':>5} {'cites':>5}  headline")
for r in records[:20]:
    print(f"{r['fact']:>5} {'YES' if r['in_code'] else '':>5} {r['cited_by']:>5}  {r['headline'][:92]}")
