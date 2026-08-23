"""Tabulate M62's focus guard across every corpus stack it was run on.

Reads only the JSON `11-focus-guard.py` already wrote. Scores nothing and
re-measures nothing: the observable is the binary's own reported `mean n_eff`,
exactly as M62's Requirement G defines it.

Requirement G asks for `n_eff/N < 0.95` on ONE real through-focus stack. M64
ships a CONSTANT default gate, and M52 measured the gate-to-n_eff mapping
varying 28.9x across the corpus, so one stack does not cover the shipped
default. This runs G's own observable over all seven.

    python src/21-guard-corpus.py
"""

from __future__ import annotations

import glob
import json
import os
import pathlib

THRESHOLD = 0.95  # M62 Requirement G

here = pathlib.Path(__file__).resolve().parents[1]
rows = []
for f in sorted(glob.glob(str(here / "out" / "11-focus-guard-m64*.json"))):
    d = json.load(open(f))
    stack = os.path.basename(d["stack"].rstrip("\\/"))
    for r in d["ladder"]:
        rows.append((stack, d["frames"], r["gate"], r["tolerance"],
                     r["mean_n_eff"], r["n_eff_over_N"], r["pred_sigma_gain"]))

rows.sort(key=lambda r: r[5])

hdr = ("stack", "N", "gate", "tol", "mean n_eff", "n_eff/N", "sigma gain")
print("%-16s%5s%7s%10s%12s%10s%12s" % hdr)
for stack, n, gate, tol, n_eff, ratio, sg in rows:
    print("%-16s%5d%7.1f%10.6f%12.3f%10.5f%11.4fx"
          % (stack, n, gate, tol, n_eff, ratio, sg))

worst = max(r[5] for r in rows)
best = min(r[5] for r in rows)
npass = sum(1 for r in rows if r[5] < THRESHOLD)

print()
print("worst (max) n_eff/N : %.5f   threshold %.2f   margin %.2fx"
      % (worst, THRESHOLD, THRESHOLD / worst))
print("best  (min) n_eff/N : %.5f" % best)
print("spread across corpus: %.2fx" % (worst / best))
print("rows below threshold: %d / %d" % (npass, len(rows)))
print()
print("VERDICT:", "PASS -- the shipped default discriminates focus on every"
      " corpus stack" if npass == len(rows) else "FAIL -- at least one stack is"
      " degenerate at the shipped default")
