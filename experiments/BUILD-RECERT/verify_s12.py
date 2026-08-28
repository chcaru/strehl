"""Verify section 12 of docs/research/BUILD-OUTPUT.md against the measured JSON.

REPAIRED after this verifier read RED (54/67) with every failure an ANCHOR
failure. Nothing in section 12 had changed. The document had GROWN: sections 13
and 14 added rows naming the same subjects, and this file's section slice ran

    sec = text[text.index("# 12. ..."):]          # unbounded above

to the end of the document, so `| `coffee-bubbles` |` went from occurring once
to occurring five times. verify_s14.py already carries the fix and says why in
its own docstring -- section 14 did this to verify_s13.py, it was repaired
there, and the repair was never propagated back here. The lesson is not about
slicing: A VERIFIER THAT PASSED WHEN IT WAS WRITTEN IS NOT A VERIFIER THAT
PASSES NOW, and only re-running the whole suite discovers that. This suite had
not been re-run end to end since section 12 was written.

That failure was in the safe direction -- an ambiguous anchor reports ANCHOR and
exits 1, it does not silently certify. Two other defects found in the same pass
were NOT safe, and both are the shape ORCH asked every lane to hunt:

  1. SUBSTRING CONTAINMENT. The old check asked `if want in hits[0]`, i.e.
     whether the formatted value appears ANYWHERE in the matched row. A row of
     the exchange table is `| subj | blotch | sharp | bought | spent | rate |`;
     a value in column 2 would satisfy a check aimed at column 1. Every table
     claim is now addressed POSITIONALLY -- split the row, index the column,
     compare for equality.

  2. A SELF-SATISFYING ANCHOR. `foam` names a row in two different section-12
     tables, and the old code disambiguated with the anchor

         "| `foam` | 0.7662"

     then used that anchor to verify that foam's blotch_corr is 0.7662. The
     anchor contained the value it was checking, so the check could not fail:
     if the document's number changed, the anchor would stop matching and report
     ANCHOR rather than FAIL, and the check would never once have compared the
     document against the JSON. This file's own comment warns against exactly
     this shape. The ambiguity is now resolved by CELL COUNT (the tone table has
     4 cells, the exchange table 6), which carries no value at all.

Prose claims use a whitespace-collapsed view with prefix/suffix delimiters that
EXCLUDE the digits being verified, because the document is hard-wrapped and a
claim spanning a line break is invisible to line-wise matching.
"""
import json
import re
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
DOC = ROOT / "docs" / "research" / "BUILD-OUTPUT.md"
LOGS = Path(r"D:\strehl-out\BUILD-OUTPUT\BUILD-RECERT\logs")

text = DOC.read_text(encoding="utf-8")
# Bounded at BOTH ends. A future section 15 must not be able to widen this
# verifier's scope and turn its unique anchors ambiguous, which is precisely
# what sections 13-14 did to the previous version of this file.
_start = text.index("# 12. Is the shipping default")
_next = re.search(r"^# \d+\. ", text[_start + 1:], flags=re.M)
sec = text[_start:_start + 1 + _next.start()] if _next else text[_start:]
sec = re.sub(r"```.*?```", "", sec, flags=re.S)
flat = " ".join(sec.split())

flatexp = json.loads((LOGS / "flatexp.json").read_text(encoding="utf-8"))
gain = json.loads((LOGS / "gainbias.json").read_text(encoding="utf-8"))
by_g = {r["subject"]: r for r in gain}

checks = []


def med(vals):
    return float(np.median([v for v in vals if v is not None and np.isfinite(v)]))


def _row(name, anchor, ncells=None):
    hits = [ln for ln in sec.splitlines() if anchor in ln]
    if ncells is not None:
        hits = [h for h in hits
                if len(h.strip().strip("|").split("|")) == ncells]
    if len(hits) != 1:
        checks.append((name, "ANCHOR", f"{anchor!r} occurs {len(hits)}x, need 1"))
        return None
    return [c.strip() for c in hits[0].strip().strip("|").split("|")]


def check_cell(name, anchor, col, value, fmt="{:.4f}", ncells=None):
    """Compare column `col` of the anchored row for equality with `value`.

    The cell is compared on its LEADING TOKEN after bold markers are removed,
    because several rate cells carry a trailing annotation (`**0.34** best`).
    The check stays pinned to one column, so a value sitting in a neighbouring
    column cannot satisfy it -- which is the whole point of the repair.
    """
    cells = _row(name, anchor, ncells)
    if cells is None:
        return
    if col >= len(cells):
        checks.append((name, "ANCHOR", f"row has {len(cells)} cells, wanted {col}"))
        return
    tok = cells[col].replace("*", "").strip().split()
    got = tok[0] if tok else ""
    want = fmt.format(value)
    checks.append((name, "OK", want) if got == want
                  else (name, "FAIL", f"col {col} is {got!r}, want {want!r}"))


def check_flat(name, prefix, suffix, value, fmt="{:.4f}"):
    want = prefix + fmt.format(value) + suffix
    n = flat.count(want)
    checks.append((name, "OK", want) if n == 1
                  else (name, "FAIL", f"{want!r} occurs {n}x, need 1"))


def assert_(name, cond, detail):
    checks.append((name, "OK" if cond else "FAIL", detail))


def check_verdict(name, cond, if_true, if_false):
    """Require the document to state the conclusion THE DATA supports.

    Added after negctl_report.py measured this suite catching 3 of 3 planted
    arithmetic defects and 0 of 2 planted CONCLUSION flips: deleting "do not"
    from section 12.9's recommendation reversed the section's verdict, changed
    no digit anywhere, and passed all 191 checks. That is the shape ORCH found
    in V-NEVERWORSE's verifier, where flipping "refuted" to "confirmed" passed
    712 green checks.

    A presence test cannot detect a reversed conclusion -- the flipped sentence
    satisfies it as readily as the original, and so does any paraphrase
    elsewhere in the document. Pinning a DIRECTION needs both halves: the
    supported claim present exactly once AND its negation absent.

    `cond` is recomputed from the JSON on every run rather than hard-coded, so
    if the measurement ever reverses, this check demands that the document
    reverse with it. A verdict check that froze today's answer into the checker
    would be a different defect wearing the same clothes -- it would certify
    that the document still says what it said, not that it still says what the
    data shows.
    """
    want, unwanted = (if_true, if_false) if cond else (if_false, if_true)
    nw, nu = flat.count(want), flat.count(unwanted)
    checks.append((name, "OK", want[:52]) if (nw == 1 and nu == 0)
                  else (name, "FAIL", f"supported claim occurs {nw}x (need 1), "
                                      f"its negation occurs {nu}x (need 0)"))


# --- corpus roll-ups, recomputed from the JSON -------------------------------
b_rep = med([r.get("blotch") for r in flatexp])
s_rep = med([r.get("sharp") for r in flatexp])
b_cor = med([r["blotch_corr"] for r in gain])
g_cor = med([r["grain_corr"] for r in gain])
g_med = med([r["gain"] for r in gain])

ROLL = "| blotch, mottle 21-61 px floor |"
check_cell("blotch as reported", ROLL, 1, b_rep)
check_cell("blotch gain-corrected", ROLL, 2, b_cor)
check_cell("sharp median", "| sharpness, struct 5-13 px", 1, s_rep)
check_cell("grain corrected", "| grain, <=3 px floor |", 2, g_cor)
check_flat("median gain", "median FLAT1/DEF gain is **", "**", g_med)

check_cell("blotch improvement pct", "| blotch improvement |", 2,
           (1 - b_cor) * 100, "{:.2f}%")
check_cell("sharpness cost pct", "| sharpness cost |", 2,
           (1 - s_rep) * 100, "{:.2f}%")
check_cell("exchange rate", "| sharpness spent per unit of blotch bought |", 2,
           (1 - s_rep) / (1 - b_cor), "{:.2f}")

# --- partition ---------------------------------------------------------------
verdicts = {}
for r in flatexp:
    v = (r.get("verdict") or r.get("state") or "?").split(" --")[0]
    verdicts[v] = verdicts.get(v, 0) + 1
check_flat("partition TRADE", "**Partition: ", " TRADE",
           verdicts.get("TRADE", 0), "{:d}")
check_flat("partition LOSES", "TRADE, ", " FLAT LOSES",
           verdicts.get("FLAT LOSES", 0), "{:d}")

basis = {}
for r in flatexp:
    k = (r.get("registration") or {}).get("basis", "?")
    basis[k] = basis.get(k, 0) + 1
check_flat("basis SSD-WELL", "`SSD-WELL=", ",", basis.get("SSD-WELL", 0), "{:d}")
check_flat("basis MEDIAN-ONLY", "MEDIAN-ONLY=", "`", basis.get("MEDIAN-ONLY", 0),
           "{:d}")

# --- the exchange-rate table, addressed positionally --------------------------
# ncells=6 selects the exchange table. `foam` also names a 4-cell row in the
# 12.7 tone table; cell count separates them without an anchor that carries a
# value, which is what the previous version did.
EXCH = 6
COL = {"blotch_corr": 1, "sharp": 2, "bought": 3, "spent": 4, "rate": 5}

rate = {}
for r in gain:
    bought = (1 - r["blotch_corr"]) * 100
    rate[r["subject"]] = ((1 - r["sharp"]) * 100 / bought) if bought > 0 else float("inf")
order = sorted(rate, key=lambda s: -rate[s])

TABLED = ("flat-on-ruler-cpl", "foam", "lead-1-cpl", "112MSDCF", "113MSDCF",
          "coffee-bubbles", "flower-bud-alone-cpl", "119MSDCF", "109MSDCF")
for subj in TABLED:
    a = f"| `{subj}` |"
    g = by_g[subj]
    check_cell(f"{subj} blotch_corr", a, COL["blotch_corr"], g["blotch_corr"],
               ncells=EXCH)
    check_cell(f"{subj} sharp", a, COL["sharp"], g["sharp"], ncells=EXCH)
    check_cell(f"{subj} bought%", a, COL["bought"], (1 - g["blotch_corr"]) * 100,
               "{:.1f}", ncells=EXCH)
    check_cell(f"{subj} spent%", a, COL["spent"], (1 - g["sharp"]) * 100,
               "{:.1f}", ncells=EXCH)
    check_cell(f"{subj} rate", a, COL["rate"], rate[subj], "{:.2f}", ncells=EXCH)

# softness percentages quoted in prose, anchored on text that excludes the digits
for subj in ("dry-erase-marker-head-cpl", "flower-bud-alone-cpl"):
    check_flat(f"{subj} softness pct", f"`{subj}` at **", "% softer**",
               (1 - by_g[subj]["sharp"]) * 100, "{:.1f}")

# --- the claim I had to retract, and its guards -------------------------------
# The original section 12 asserted `coffee-bubbles` was "the worst trade in the
# entire corpus"; ranked by sharpness-spent-per-blotch-bought it is 7th of 26.
# The error ran in the direction of my own conclusion, so it keeps its checks.
MOTTLE6 = ("coffee-bubbles", "lead-1-cpl", "113MSDCF", "flat-on-ruler-cpl",
           "112MSDCF", "foam")
worst6 = max(MOTTLE6, key=lambda s: rate[s])
next6 = sorted((rate[s] for s in MOTTLE6), reverse=True)[1]
assert_("coffee-bubbles worst of mottle6", worst6 == "coffee-bubbles", worst6)
check_flat("mottle6 next-worst rate", "against the next-worst `113MSDCF` at ", "",
           next6, "{:.2f}")
check_flat("coffee-bubbles rank", "Ranked by exchange rate it is **", " of 26**",
           order.index("coffee-bubbles") + 1, "{:d}th")

assert_("worst two rates are 109/119MSDCF", set(order[:2]) == {"109MSDCF", "119MSDCF"},
        ", ".join(order[:2]))
check_flat("109MSDCF rate", "`109MSDCF` (", ")", rate["109MSDCF"], "{:.2f}")
check_flat("119MSDCF rate", "`119MSDCF` (", ")", rate["119MSDCF"], "{:.2f}")

# --- the basis disclosure -----------------------------------------------------
# The shipped verdict fires on RAW blotch. Recomputing the identical rule on the
# gain-corrected ratio must reproduce the shipped raw partition exactly (proving
# the rule was reimplemented faithfully) and must yield the corrected partition
# the document claims.
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
assert_("reimplemented rule reproduces shipped raw partition",
        raw_p == {k: v for k, v in verdicts.items() if v},
        f"{raw_p} vs shipped {verdicts}")
check_flat("corrected partition TRADE", "giving **", " TRADE",
           cor_p.get("TRADE", 0), "{:d}")
check_flat("corrected partition LOSES", "TRADE, ", " FLAT LOSES",
           cor_p.get("FLAT LOSES", 0), "{:d}")
check_flat("coffee-bubbles raw blotch", "`coffee-bubbles`, raw blotch ", "",
           by_g["coffee-bubbles"]["blotch"])

# 0 FLAT WINS is the load-bearing cell and must hold on BOTH bases
assert_("zero FLAT WINS on both bases",
        raw_p.get("FLAT WINS", 0) == 0 and cor_p.get("FLAT WINS", 0) == 0,
        f"raw={raw_p.get('FLAT WINS', 0)} corr={cor_p.get('FLAT WINS', 0)}")
check_flat("corpus median softness", "against a corpus median of ", "%",
           (1 - s_rep) * 100, "{:.1f}")

# --- the two load-bearing CLAIMS, pinned to the data that supports them -------
# Section 12 exists to answer one question, and the answer is a recommendation.
# Until now nothing in this file read that recommendation; the suite would have
# certified the opposite one.
check_verdict(
    "12.9 recommendation matches the measurement",
    cor_p.get("FLAT WINS", 0) == 0 and s_rep < 1.0,
    "## 12.9 Recommendation: do not move the default constant tonight",
    "## 12.9 Recommendation: move the default constant tonight")

# The hull axis is unmeasured because no hull key exists in either JSON. If a
# future run adds one, this check flips and demands the disclosure be withdrawn,
# rather than letting a stale "NOT MEASURED" outlive the gap it described.
_hull_measured = any("hull" in k.lower() for r in flatexp for k in r)
check_verdict(
    "12.8 hull disclosure matches the data",
    not _hull_measured,
    "## 12.8 The hull axis is NOT MEASURED, and that is a hole in this recommendation",
    "## 12.8 The hull axis is MEASURED, and that is not a hole in this recommendation")

bad = [n for n, s, d in checks if s != "OK"]
w = max(len(n) for n, _, _ in checks)
for n, s, d in checks:
    if s != "OK":
        print(f"  {s:<7}{n:<{w}}  {d}")
print(f"\n{len(checks) - len(bad)}/{len(checks)} section-12 claims verified "
      f"against the JSON  {'GREEN' if not bad else 'RED'}")
sys.exit(0 if not bad else 1)
