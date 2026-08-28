"""Verify every number in section 13 against headscore.json, recomputed.

Same discipline as verify_s12.py, for the same reason: writing section 12 I
introduced three transcription errors into a document whose underlying JSON was
correct, and later found a fourth claim ("worst trade in the entire corpus") that
was false and happened to flatter my own conclusion. A document is not verified
by having been written carefully.

Every check is pinned to a UNIQUE full-line anchor, and each anchor deliberately
EXCLUDES the digits it verifies where that is possible -- an anchor that contains
its own value is self-satisfying and can never go RED.
"""
import json
import re
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
DOC = ROOT / "docs" / "research" / "BUILD-OUTPUT.md"
LOGS = Path(r"C:\dev\strehl-out\BUILD-RECERT\logs")

text = DOC.read_text(encoding="utf-8")
# Bound the section ABOVE as well as below. The first version sliced from the
# heading to end-of-file, which was correct only while section 13 was last:
# adding section 14 put six more `| `leaf-2-cpl` |` rows inside the slice and
# three anchors that had been unique became ambiguous. A verifier whose scope
# silently grows with the document is a verifier that decays.
_start = text.index("# 13. The HEAD baseline against SHIP-V4")
_next = re.search(r"^# \d+\. ", text[_start + 1:], flags=re.M)
sec = text[_start:_start + 1 + _next.start()] if _next else text[_start:]
# Fenced code blocks are illustrations, not claims -- 13.8 quotes a mutated copy
# of the partition table's REGRESSED row to explain a defect, and that copy must
# not be mistaken for the table itself. Strip them before matching.
sec = re.sub(r"```.*?```", "", sec, flags=re.S)
# Prose in this document is hard-wrapped, so a claim that spans a line break is
# invisible to line-wise matching. Collapse whitespace for prose claims and keep
# the line-wise view for table rows.
flat = " ".join(sec.split())
rows = json.loads((LOGS / "headscore.json").read_text(encoding="utf-8"))
null = json.loads((LOGS / "headscore-null.json").read_text(encoding="utf-8"))
by = {r["subject"]: r for r in rows}
scored = [r for r in rows if r.get("state") == "SCORED"]

checks = []


def _row(name, anchor, also=None):
    """Return a markdown row's cells, or None after recording an anchor failure."""
    hits = [ln for ln in sec.splitlines() if anchor in ln
            and (also is None or also in ln)]
    if len(hits) != 1:
        checks.append((name, "ANCHOR", f"{anchor!r} occurs {len(hits)}x, need 1"))
        return None
    return [c.strip().strip("*").strip() for c in hits[0].strip().strip("|").split("|")]


def check_cell(name, anchor, col, value, fmt="{:.4f}", also=None):
    """Compare ONE cell by exact equality, not by substring containment.

    Commissioning caught this: the first version asked whether the formatted
    value appeared anywhere in the line, and a table row of single digits
    satisfies "0" no matter which cell holds the 0. Planting a regression into
    `| **REGRESSED** | **0** | **0** | **0** |` therefore read GREEN. A
    presence test on a short token is satisfied by any neighbour that happens to
    carry the same characters, so the cell is addressed positionally and
    compared for equality.
    """
    cells = _row(name, anchor, also)
    if cells is None:
        return
    if col >= len(cells):
        checks.append((name, "ANCHOR", f"row has {len(cells)} cells, wanted col {col}"))
        return
    want = fmt.format(value)
    checks.append((name, "OK", want) if cells[col] == want
                  else (name, "FAIL", f"col {col} is {cells[col]!r}, want {want!r}"))


def check_flat(name, prefix, suffix, value, fmt="{:.0f}"):
    """Verify a prose claim that may wrap across a line break.

    prefix and suffix must both EXCLUDE the digits being verified, so the check
    cannot be satisfied by its own anchor, and together they delimit the value
    exactly rather than merely containing it.
    """
    want = prefix + fmt.format(value) + suffix
    n = flat.count(want)
    checks.append((name, "OK", want) if n == 1
                  else (name, "FAIL", f"{want!r} occurs {n}x, need 1"))


def assert_(name, cond, detail):
    checks.append((name, "OK" if cond else "FAIL", detail))


def med(k):
    v = [r[k] for r in scored if r.get(k) is not None and np.isfinite(r[k])]
    return float(np.median(v))


# --- the partition table -----------------------------------------------------
KEYS = ("IMPROVED", "UNCHANGED", "REGRESSED", "REFUSED")
AXES = ("blotch_verdict", "sharp_verdict", "grain_verdict")
ANCHOR = {"IMPROVED": "| IMPROVED |", "UNCHANGED": "| UNCHANGED |",
          "REGRESSED": "| **REGRESSED** |", "REFUSED": "| REFUSED |"}
for k in KEYS:
    for col, a in enumerate(AXES, start=1):
        n = sum(1 for r in rows if r.get(a) == k)
        check_cell(f"partition {k} {a}", ANCHOR[k], col, n, "{:d}")
# and the TOTAL row, which is the claim that each column covers the whole corpus
for col, a in enumerate(AXES, start=1):
    check_cell(f"total {a}", "| TOTAL |", col, len(rows), "{:d}")

# each axis must partition all 26
for a in AXES:
    tot = sum(sum(1 for r in rows if r.get(a) == k) for k in KEYS)
    assert_(f"axis {a} sums to 26", tot == len(rows), f"{tot} == {len(rows)}")
assert_("zero regressions on every axis",
        all(sum(1 for r in rows if r.get(a) == "REGRESSED") == 0 for a in AXES),
        "REGRESSED count is 0 on blotch, sharp and grain")

# --- corpus medians ----------------------------------------------------------
check_flat("median blotch", "gain-corrected: blotch **", "**, sharp",
           med("blotch_corr"), "{:.4f}")
check_flat("median sharp", "**, sharp **", "**, grain", med("sharp"), "{:.4f}")
check_flat("median grain", "**, grain **", "**. Every axis", med("grain_corr"), "{:.4f}")

# --- the ranked per-subject table -------------------------------------------
# columns: | subject | grain | sharp | blotch | reading |
for s in ("leaf-2-cpl", "lead-1-cpl", "flowers-cpl", "109MSDCF",
          "flower-inner-edge-cpl", "bee-2-cpl",
          "flower-bud-with-background-fern-cpl"):
    a = f"| `{s}` |"
    # `109MSDCF` also appears in the 13.1 bit-identity table, so disambiguate on
    # a cell that only the ranked table's rows carry.
    also = "| quieter |" if s == "109MSDCF" else None
    check_cell(f"{s} grain", a, 1, by[s]["grain_corr"], also=also)
    check_cell(f"{s} sharp", a, 2, by[s]["sharp"], also=also)
    check_cell(f"{s} blotch", a, 3, by[s]["blotch_corr"], also=also)

# the ranking claim itself: those seven must be the seven best grain movers
best7 = sorted(scored, key=lambda r: r["grain_corr"])[:7]
assert_("the seven listed subjects ARE the seven largest grain improvements",
        [r["subject"] for r in best7] ==
        ["leaf-2-cpl", "lead-1-cpl", "flowers-cpl", "109MSDCF",
         "flower-inner-edge-cpl", "bee-2-cpl",
         "flower-bud-with-background-fern-cpl"],
        ", ".join(r["subject"] for r in best7))

# --- the two headline percentages -------------------------------------------
q = lambda s: (1 - by[s]["grain_corr"]) * 100
x = lambda s: (by[s]["sharp"] - 1) * 100
check_flat("leaf quieter pct", "are **", "% and ", q("leaf-2-cpl"))
check_flat("lead quieter pct", "% and ", "% quieter in fine grain", q("lead-1-cpl"))
check_flat("leaf sharper pct", "while carrying ", "% and ", x("leaf-2-cpl"))
check_flat("lead sharper pct", "% and ", "% MORE structure", x("lead-1-cpl"))

# --- registration on the movers ---------------------------------------------
for s in ("leaf-2-cpl", "lead-1-cpl"):
    g = by[s]["registration"]
    assert_(f"{s} registration clean",
            g["basis"] == "SSD-WELL" and g["median"] == [0, 0] and g["worst"] == 0
            and g["n_informative"] == 5,
            f"{g['basis']} median={g['median']} worst={g['worst']} n={g['n_informative']}")

# --- the null control --------------------------------------------------------
n_unchanged = sum(1 for r in null
                  if r.get("blotch_verdict") == "UNCHANGED"
                  and r.get("sharp_verdict") == "UNCHANGED"
                  and r.get("grain_verdict") == "UNCHANGED")
assert_("null control 26/26 UNCHANGED on all three axes",
        n_unchanged == len(null) == 26, f"{n_unchanged}/{len(null)}")
exact = all(abs(r["blotch"] - 1) < 1e-9 and abs(r["sharp"] - 1) < 1e-9
            and abs(r["grain"] - 1) < 1e-9
            for r in null if r.get("state") == "SCORED")
assert_("null control ratios are EXACTLY 1.0000", exact,
        "every blotch/sharp/grain ratio == 1 to 1e-9")

# --- render count ------------------------------------------------------------
assert_("26 subjects scored, none unscored",
        len(scored) == 26 == len(rows), f"{len(scored)} scored of {len(rows)}")

bad = [n for n, s, d in checks if s != "OK"]
w = max(len(n) for n, _, _ in checks)
for n, s, d in checks:
    if s != "OK":
        print(f"  {s:<7}{n:<{w}}  {d}")
print(f"\n{len(checks) - len(bad)}/{len(checks)} section-13 claims verified "
      f"against the JSON  {'GREEN' if not bad else 'RED'}")
sys.exit(0 if not bad else 1)

