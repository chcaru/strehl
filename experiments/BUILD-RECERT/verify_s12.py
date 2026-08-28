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

# --- the exchange-rate table, and the claim I had to retract ------------------
# Added after the first GREEN run. The original section 12 asserted that
# `coffee-bubbles` was "the worst trade in the entire corpus"; ranked by
# sharpness-spent-per-blotch-bought it is 7th of 26. The claim was an artefact
# of it being the only subject the RAW-basis verdict rule scored FLAT LOSES,
# which is itself basis-dependent. A verdict label is not a magnitude, and the
# error ran in the direction of my own conclusion, so it gets its own checks.
rate = {}
for r in gain:
    bought = (1 - r["blotch_corr"]) * 100
    rate[r["subject"]] = ((1 - r["sharp"]) * 100 / bought) if bought > 0 else float("inf")
order = sorted(rate, key=lambda s: -rate[s])

for subj in ("flat-on-ruler-cpl", "foam", "lead-1-cpl", "112MSDCF", "113MSDCF",
             "coffee-bubbles", "flower-bud-alone-cpl", "119MSDCF", "109MSDCF"):
    # `foam` also names a row in the section 12.7 tone table, so its anchor
    # needs the blotch cell to stay unique. The exactly-once rule caught this.
    a = "| `foam` | 0.7662" if subj == "foam" else f"| `{subj}` |"
    g = by_g[subj]
    check(f"{subj} bought%", a, (1 - g["blotch_corr"]) * 100, "{:.1f}")
    check(f"{subj} spent%", a, (1 - g["sharp"]) * 100, "{:.1f}")
    check(f"{subj} rate", a, rate[subj], "{:.2f}")

MOTTLE6 = ("coffee-bubbles", "lead-1-cpl", "113MSDCF", "flat-on-ruler-cpl",
           "112MSDCF", "foam")
worst6 = max(MOTTLE6, key=lambda s: rate[s])
next6 = sorted((rate[s] for s in MOTTLE6), reverse=True)[1]
checks.append(("coffee-bubbles worst of mottle6",
               "OK" if worst6 == "coffee-bubbles" else "FAIL", worst6))
# Anchors below deliberately EXCLUDE the digits they verify. An anchor that
# contains its own value is self-satisfying and can never fail -- a check that
# is structurally incapable of going RED is decoration, not verification.
check("mottle6 next-worst rate", "against the next-worst `113MSDCF` at", next6, "{:.2f}")
check("coffee-bubbles rank", "Ranked by exchange rate it is **",
      order.index("coffee-bubbles") + 1, "{:d}th of 26")

# the two worst rates in the corpus are the two subjects V-SOFTCHECK called soft
checks.append(("worst two rates are 109/119MSDCF",
               "OK" if set(order[:2]) == {"109MSDCF", "119MSDCF"} else "FAIL",
               ", ".join(order[:2])))
check("109MSDCF rate", "The two worst exchange rates in the whole corpus are",
      rate["109MSDCF"], "({:.2f})")
check("119MSDCF rate", "-- the exact two subjects V-SOFTCHECK measured as",
      rate["119MSDCF"], "({:.2f})")

# --- the basis disclosure -----------------------------------------------------
# The shipped verdict fires on RAW blotch. Recomputing the identical rule on the
# gain-corrected ratio must reproduce the shipped raw partition exactly (which
# proves the rule was reimplemented faithfully) and must yield the corrected
# partition the document claims.
NOISE_WIN, SHARP_HOLD = 0.97, 0.97


def verdict_of(b, s):
    if b < NOISE_WIN:
        return "FLAT WINS" if s >= SHARP_HOLD else "TRADE"
    if s < SHARP_HOLD:
        return "FLAT LOSES"
    return "FLAT LOSES" if b > 1 / NOISE_WIN else "NEUTRAL"


raw_p, cor_p = {}, {}
for r in gain:
    for d, key in ((raw_p, "blotch"), (cor_p, "blotch_corr")):
        v = verdict_of(r[key], r["sharp"])
        d[v] = d.get(v, 0) + 1
checks.append(("reimplemented rule reproduces shipped raw partition",
               "OK" if raw_p == {k: v for k, v in verdicts.items() if v} else "FAIL",
               f"{raw_p} vs shipped {verdicts}"))
check("corrected partition TRADE", "giving **", cor_p.get("TRADE", 0), "{:d} TRADE")
check("corrected partition LOSES", "giving **", cor_p.get("FLAT LOSES", 0),
      "{:d} FLAT LOSES")
check("coffee-bubbles raw blotch", "`coffee-bubbles`, raw blotch",
      by_g["coffee-bubbles"]["blotch"])

# 0 FLAT WINS is the load-bearing cell and must hold on BOTH bases
checks.append(("zero FLAT WINS on both bases",
               "OK" if raw_p.get("FLAT WINS", 0) == 0 and cor_p.get("FLAT WINS", 0) == 0
               else "FAIL",
               f"raw={raw_p.get('FLAT WINS', 0)} corr={cor_p.get('FLAT WINS', 0)}"))
check("corpus median softness", "against a corpus median of",
      (1 - s_rep) * 100, "{:.1f}%")

nfail = sum(1 for _, st, _ in checks if st != "OK")
for name, st, detail in checks:
    if st != "OK":
        print(f"  {st:<6} {name:<34} {detail}")
print(f"\n{len(checks) - nfail}/{len(checks)} section-12 claims verified "
      f"against the JSON  {'GREEN' if nfail == 0 else 'RED'}")
sys.exit(1 if nfail else 0)
