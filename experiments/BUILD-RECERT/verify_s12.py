"""Verify section 12 of docs/research/BUILD-OUTPUT.md against the measured JSON.

Each check is pinned to its own ANCHOR -- a neighbouring literal unique to the
claim's canonical site -- rather than to the bare number. A presence test on a
short token like `0.8037` is satisfied by any duplicate of that value anywhere in
a 1800-line document, so it verifies nothing; this project has already shipped a
verifier that read GREEN for exactly that reason.

Derived percentages are RECOMPUTED from the JSON here rather than compared to
themselves, so a transcription error in the document cannot be laundered by
copying it into the checker.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DOC = ROOT / "docs" / "research" / "BUILD-OUTPUT.md"
LOGS = Path(r"C:\dev\strehl-out\BUILD-RECERT\logs")

text = DOC.read_text(encoding="utf-8")
sec = text[text.index("# 12. Is the shipping default"):]
flat = json.loads((LOGS / "flatexp.json").read_text(encoding="utf-8"))
gain = json.loads((LOGS / "gainbias.json").read_text(encoding="utf-8"))
by_g = {r["subject"]: r for r in gain}

import numpy as np


def med(vals):
    return float(np.median([v for v in vals if v is not None and np.isfinite(v)]))


checks = []


def check(name, anchor, value, fmt="{:.4f}"):
    """Anchor must occur exactly once in section 12, and carry the value."""
    hits = [ln for ln in sec.splitlines() if anchor in ln]
    if len(hits) != 1:
        checks.append((name, "ANCHOR", f"anchor {anchor!r} occurs {len(hits)}x, need 1"))
        return
    want = fmt.format(value)
    if want in hits[0]:
        checks.append((name, "OK", want))
    else:
        checks.append((name, "FAIL", f"want {want} in: {hits[0].strip()[:90]}"))


# --- corpus roll-ups, recomputed ---------------------------------------------
b_rep = med([r.get("blotch") for r in flat])
s_rep = med([r.get("sharp") for r in flat])
b_cor = med([r["blotch_corr"] for r in gain])
g_cor = med([r["grain_corr"] for r in gain])
g_med = med([r["gain"] for r in gain])

check("blotch as reported", "| blotch, mottle 21-61 px floor |", b_rep)
check("blotch gain-corrected", "| blotch, mottle 21-61 px floor |", b_cor)
check("sharp median", "| sharpness, struct 5-13 px", s_rep)
check("grain corrected", "| grain, <=3 px floor |", g_cor)
check("median gain", "median FLAT1/DEF gain is **", g_med)

check("blotch improvement pct", "| blotch improvement |", (1 - b_cor) * 100, "{:.2f}%")
check("sharpness cost pct", "| sharpness cost |", (1 - s_rep) * 100, "{:.2f}%")
check("exchange rate", "| sharpness spent per unit of blotch bought |",
      (1 - s_rep) / (1 - b_cor), "{:.2f}")

# --- partition ---------------------------------------------------------------
verdicts = {}
for r in flat:
    v = (r.get("verdict") or r.get("state") or "?").split(" --")[0]
    verdicts[v] = verdicts.get(v, 0) + 1
check("partition TRADE", "**Partition:", verdicts.get("TRADE", 0), "{:d}")
check("partition LOSES", "**Partition:", verdicts.get("FLAT LOSES", 0), "{:d}")

basis = {}
for r in flat:
    basis[(r.get("registration") or {}).get("basis", "?")] = \
        basis.get((r.get("registration") or {}).get("basis", "?"), 0) + 1
check("basis SSD-WELL", "`SSD-WELL=", basis.get("SSD-WELL", 0), "{:d}")
check("basis MEDIAN-ONLY", "`SSD-WELL=", basis.get("MEDIAN-ONLY", 0), "{:d}")

# --- named per-subject claims -------------------------------------------------
for subj, anchor in (("coffee-bubbles", "| `coffee-bubbles` |"),
                     ("flat-on-ruler-cpl", "| `flat-on-ruler-cpl` |"),
                     ("foam", "| `foam` | 0.7662"),
                     ("lead-1-cpl", "| `lead-1-cpl` |"),
                     ("112MSDCF", "| `112MSDCF` |"),
                     ("113MSDCF", "| `113MSDCF` |"),
                     ("flower-bud-alone-cpl", "| `flower-bud-alone-cpl` |")):
    g = by_g[subj]
    check(f"{subj} blotch_corr", anchor, g["blotch_corr"])
    check(f"{subj} sharp", anchor, g["sharp"])

# softness percentages quoted in prose
for subj, anchor in (("dry-erase-marker-head-cpl", "`dry-erase-marker-head-cpl` at **"),
                     ("flower-bud-alone-cpl", "**35.4% softer**")):
    pct = (1 - by_g[subj]["sharp"]) * 100
    check(f"{subj} softness pct", anchor, pct, "{:.1f}%")
check("corpus median softness", "against a corpus median of",
      (1 - s_rep) * 100, "{:.1f}%")

nfail = sum(1 for _, st, _ in checks if st != "OK")
for name, st, detail in checks:
    if st != "OK":
        print(f"  {st:<6} {name:<34} {detail}")
print(f"\n{len(checks) - nfail}/{len(checks)} section-12 claims verified "
      f"against the JSON  {'GREEN' if nfail == 0 else 'RED'}")
sys.exit(1 if nfail else 0)
