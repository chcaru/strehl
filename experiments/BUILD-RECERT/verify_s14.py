"""Verify section 14's numbers against the JSON they came from, recomputed.

Same discipline and the same helpers as verify_s13.py, whose own commissioning
found a check that could not fail: comparing a formatted value by SUBSTRING
CONTAINMENT against a whole table row is satisfied by any neighbouring cell that
happens to carry the same characters. Every table claim here is therefore
addressed POSITIONALLY -- split the row, index the column, compare for equality.

Prose claims use whitespace-collapsed matching with prefix/suffix delimiters
that exclude the digits being verified, because this document is hard-wrapped
and a claim that spans a line break is invisible to line-wise matching.
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
# Bounded above as well as below, so a future section 15 cannot silently widen
# this verifier's scope and turn its unique anchors ambiguous. That is exactly
# what section 14 did to verify_s13.py.
_start = text.index("# 14. The gatefloor fix")
_next = re.search(r"^# \d+\. ", text[_start + 1:], flags=re.M)
sec = text[_start:_start + 1 + _next.start()] if _next else text[_start:]
sec = re.sub(r"```.*?```", "", sec, flags=re.S)
flat = " ".join(sec.split())

ban = [r for r in json.loads((LOGS / "bannercensus.json").read_text(encoding="utf-8"))]
ok = [r for r in ban if r["state"] == "OK"]
byb = {r["subject"]: r for r in ok}
dec = {r["subject"]: r for r in
       json.loads((LOGS / "gatefloor-decomp.json").read_text(encoding="utf-8"))
       if r.get("state") == "SCORED"}
hs = {r["subject"]: r for r in
      json.loads((LOGS / "headscore.json").read_text(encoding="utf-8"))
      if r.get("state") == "SCORED"}
gf = {r["subject"]: r for r in
      json.loads((LOGS / "gatefloor-score.json").read_text(encoding="utf-8"))
      if r.get("state") == "SCORED"}

checks = []


def _row(name, anchor, also=None, ncells=None):
    hits = [ln for ln in sec.splitlines() if anchor in ln
            and (also is None or also in ln)]
    if ncells is not None:
        # Two tables in 14.2 both have rows beginning `| 0 |`. Cell count
        # separates them without inventing an anchor that carries a value.
        hits = [h for h in hits
                if len(h.strip().strip("|").split("|")) == ncells]
    if len(hits) != 1:
        checks.append((name, "ANCHOR", f"{anchor!r} occurs {len(hits)}x, need 1"))
        return None
    return [c.strip().strip("*").strip() for c in hits[0].strip().strip("|").split("|")]


def check_cell(name, anchor, col, value, fmt="{:.4f}", also=None, ncells=None):
    cells = _row(name, anchor, also, ncells)
    if cells is None:
        return
    if col >= len(cells):
        checks.append((name, "ANCHOR", f"row has {len(cells)} cells, wanted {col}"))
        return
    want = fmt.format(value)
    checks.append((name, "OK", want) if cells[col] == want
                  else (name, "FAIL", f"col {col} is {cells[col]!r}, want {want!r}"))


def check_flat(name, prefix, suffix, value, fmt="{:.0f}"):
    want = prefix + fmt.format(value) + suffix
    n = flat.count(want)
    checks.append((name, "OK", want) if n == 1
                  else (name, "FAIL", f"{want!r} occurs {n}x, need 1"))


def assert_(name, cond, detail):
    checks.append((name, "OK" if cond else "FAIL", detail))


# -- 14.1 the per-level x_white table ----------------------------------------
for lvl, anchor in ((0, "| **0** |"), (1, "| 1 |"), (2, "| 2 |"), (3, "| 3 |")):
    v = np.array([r["x_white"][lvl] for r in ok])
    a = anchor
    also = "of 25" if lvl else None
    check_cell(f"L{lvl} n", a, 1, len(v), "{:d}", also=also)
    check_cell(f"L{lvl} min", a, 2, v.min(), also=also)
    check_cell(f"L{lvl} median", a, 3, np.median(v), also=also)
    check_cell(f"L{lvl} max", a, 4, v.max(), also=also)
    check_cell(f"L{lvl} below1", a, 5, int((v < 1.0).sum()),
               "{:d} of 25", also=also)

allx = np.array([v for r in ok for v in r["x_white"]])
check_flat("total entries below 1.0", "", " of 100 entries are below 1.0",
           int((allx < 1.0).sum()), "{:d}")
assert_("every L0 entry above 1.0",
        all(r["x_white"][0] > 1.0 for r in ok),
        f"min L0 = {min(r['x_white'][0] for r in ok):.4f}")
assert_("banner subjects = 25 of 26", len(ok) == 25 and len(ban) == 26,
        f"{len(ok)} of {len(ban)}")
assert_("the missing subject is the alignment-REFUSED one",
        [r["subject"] for r in ban if r["state"] != "OK"]
        == ["highly-angled-ruler-mm-cpl"],
        str([r["subject"] for r in ban if r["state"] != "OK"]))

# -- 14.2 the averaged table --------------------------------------------------
lvl0 = np.array([r["averaged_pct"][0] for r in ok])
mid = np.array([[r["averaged_pct"][i] for i in range(1, 7)] for r in ok])
check_cell("avg L0 min", "| 0 | 0.0% |", 1, lvl0.min(), "{:.1f}%")
check_cell("avg L0 median", "| 0 | 0.0% |", 2, np.median(lvl0), "{:.1f}%")
check_cell("avg L0 max", "| 0 | 0.0% |", 3, lvl0.max(), "{:.1f}%")
check_cell("avg mid min", "| 1-6 |", 1, mid.min(), "{:.1f}%")
check_cell("avg mid median", "| 1-6 |", 2, np.median(mid), "{:.1f}%")
check_cell("avg mid max", "| 1-6 |", 3, mid.max(), "{:.1f}%")
check_cell("avg mid nonzero", "| 1-6 |", 4, int((mid > 0).sum()), "{:d} of 150")
check_flat("dry-erase L1-L4", "gates 2.2 / 1.9 / 1.5 / ",
           "% across L1-L4", byb["dry-erase-marker-head-cpl"]["averaged_pct"][4],
           "{:.1f}")
assert_("flat-on-ruler gates 0.0% at every level",
        all(v == 0.0 for v in byb["flat-on-ruler-cpl"]["averaged_pct"][:7]),
        str(byb["flat-on-ruler-cpl"]["averaged_pct"]))

# -- 14.2 the band noise gain table ------------------------------------------
g = np.array([r["band_noise_gain"] for r in ok])
for lvl in range(4):
    med = np.median(g[:, lvl])
    # ncells=3 selects the band-noise-gain table; the averaged table's `| 0 |`
    # row has 5 cells and would otherwise win the anchor.
    check_cell(f"gain L{lvl}", f"| {lvl} |", 1, med, ncells=3)
    check_cell(f"gain ratio L{lvl}", f"| {lvl} |", 2,
               med / np.median(g[:, 0]), "{:.5f}", ncells=3)

# -- 14.3 the A/B table -------------------------------------------------------
for s, on, off in (("leaf-2-cpl", 54.4, 7.1), ("coffee-bubbles", 36.4, 26.1)):
    check_cell(f"{s} x_white", f"| `{s}` | 1.", 1, byb[s]["x_white"][0])
    check_cell(f"{s} averaged ON", f"| `{s}` | 1.", 2,
               byb[s]["averaged_pct"][0], "{:.1f}%")

# -- 14.3 the decomposition table --------------------------------------------
BAND_ANCHOR = {"grain": "| grain <=3 px |", "struct": "| struct 5-13 px |",
               "mottle": "| mottle 21-61 px |"}
for band, a in BAND_ANCHOR.items():
    b = dec["leaf-2-cpl"]["bands"][band]
    check_cell(f"leaf {band} struct_x", a, 2, b["struct_x"])
    check_cell(f"leaf {band} floor_x", a, 3, b["floor_x"])
    assert_(f"leaf {band}: fix ON wins on BOTH",
            b["struct_x"] < 1.0 and b["floor_x"] > 1.0,
            f"struct_x {b['struct_x']:.4f} < 1 and floor_x {b['floor_x']:.4f} > 1")
sx = dec["leaf-2-cpl"]["bands"]["struct"]["struct_x"]
fx = dec["leaf-2-cpl"]["bands"]["struct"]["floor_x"]
check_flat("struct cost pct", "costs ", "% of absolute structure",
           (1 - sx) * 100, "{:.1f}")
check_flat("floor rise pct", "raises the noise floor by ", "%", (fx - 1) * 100,
           "{:.0f}")

# -- 14.4 the reciprocity and the pixel test ---------------------------------
check_flat("s13 sharp restated", "to HEAD at sharp **", "** and grain",
           hs["leaf-2-cpl"]["sharp"], "{:.4f}")
check_flat("s13 grain restated", "** and grain **", "**, and attributed",
           hs["leaf-2-cpl"]["grain_corr"], "{:.4f}")
check_flat("gf sharp", "gives sharp **", "** and grain",
           gf["leaf-2-cpl"]["sharp"], "{:.4f}")
check_flat("gf grain", "and grain **", "** -- reciprocals",
           gf["leaf-2-cpl"]["grain_corr"], "{:.4f}")
for s, axis, lbl in (("leaf-2-cpl", "sharp", "0.999991"),
                     ("leaf-2-cpl", "grain_corr", "1.000000")):
    r = hs[s][axis] / (1.0 / gf[s][axis])
    assert_(f"reciprocity {axis} within 1e-4", abs(r - 1) < 1e-4, f"{r:.9f}")

# -- 14.5 the correlations ----------------------------------------------------
common = sorted(set(byb) & set(hs))


def spearman(a, b):
    ra = np.argsort(np.argsort(a)).astype(float)
    rb = np.argsort(np.argsort(b)).astype(float)
    ra -= ra.mean(); rb -= rb.mean()
    return float((ra @ rb) / np.sqrt((ra @ ra) * (rb @ rb)))


x = np.array([byb[s]["x_white"][0] for s in common])
rg = spearman(x, np.array([hs[s]["grain_corr"] for s in common]))
rs = spearman(x, np.array([hs[s]["sharp"] for s in common]))
check_cell("rho grain", "| grain ratio FALLS", 1, rg, "{:+.4f}")
check_cell("rho sharp", "| sharp ratio RISES", 1, rs, "{:+.4f}")
assert_("rho signs match the stated prediction", rg < 0 < rs,
        f"grain {rg:+.4f} < 0 < sharp {rs:+.4f}")
top2 = sorted(common, key=lambda s: -byb[s]["x_white"][0])[:2]
best2 = sorted(common, key=lambda s: hs[s]["grain_corr"])[:2]
assert_("top 2 by floor excess ARE top 2 by grain improvement",
        set(top2) == set(best2) == {"leaf-2-cpl", "lead-1-cpl"},
        f"{top2} vs {best2}")
check_flat("lead-1 x_white", "`lead-1-cpl` ", ") are **exactly** the top two",
           byb["lead-1-cpl"]["x_white"][0], "{:.4f}")

bad = [n for n, s, d in checks if s != "OK"]
w = max(len(n) for n, _, _ in checks)
for n, s, d in checks:
    if s != "OK":
        print(f"  {s:<7}{n:<{w}}  {d}")
print(f"\n{len(checks) - len(bad)}/{len(checks)} section-14 claims verified "
      f"against the JSON  {'GREEN' if not bad else 'RED'}")
sys.exit(0 if not bad else 1)
