"""Re-derive every number Amendment 6 quotes, straight from out/snr-w2.json.

Rule 35: a checker that carries its own answer tests nothing. So this recomputes
each figure from the survey's saved records and compares it to the literal text
parsed out of PREREGISTRATION.md. Nothing is hardcoded on both sides.

Exit code 0 only if every quoted figure reproduces.
"""

import json
import os
import re
import sys

import numpy as np

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(HERE, "out")
DOC = os.path.join(HERE, "PREREGISTRATION.md")

TOL = 0.02   # 2% relative, or half a unit in the last quoted place


def med(recs, tag, band, key="snr"):
    v = [r["bands"][band][key] for r in recs if r["aperture"] == tag]
    return float(np.median(v))


def rows_after(text, heading, n):
    """The n table rows following a heading, as lists of stripped cells."""
    i = text.index(heading)
    out, seen = [], 0
    for line in text[i:].splitlines():
        s = line.strip()
        if not s.startswith("|"):
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        if all(set(c) <= set("- :") for c in cells):
            continue
        seen += 1
        if seen == 1:      # header
            continue
        out.append(cells)
        if len(out) == n:
            break
    return out


def num(cell):
    m = re.search(r"-?\d+\.?\d*", cell.replace("**", ""))
    return float(m.group()) if m else float("nan")


def check(name, got, want, tol=TOL):
    rel = abs(got - want) / max(abs(want), 1e-9)
    # The absolute escape hatch exists for the A4 table, whose values sit near
    # zero where a relative tolerance is meaningless. It must NOT apply to large
    # numbers, or a checker that looks strict silently stops discriminating.
    ok = rel <= tol or (abs(want) < 1.0 and abs(got - want) <= 0.02)
    print(f"  {'ok ' if ok else 'FAIL'} {name:44s} doc {want:10.3f}  "
          f"recomputed {got:10.3f}")
    return ok


def main():
    doc_path = sys.argv[1] if len(sys.argv) > 1 else DOC
    with open(os.path.join(OUT, "snr-w2.json"), encoding="utf-8") as fh:
        d = json.load(fh)
    with open(doc_path, encoding="utf-8") as fh:
        text = fh.read()
    recs = d["records"]
    tags = ["f5.6", "f8", "f11", "f14", "f18"]
    ok = True

    print("Amendment 6, the non-monotone SNR table")
    band_rows = rows_after(text, "**The measured spectral SNR is not monotone", 2)
    for row, band in zip(band_rows, ["knee", "low"]):
        for t, cell in zip(tags, row[1:]):
            ok &= check(f"{band} band, {t}", med(recs, t, band), num(cell))

    print("\nAmendment 6, the equalisation cost table")
    eq = d["equalise"]
    cost_rows = rows_after(text, "**What equalisation then costs, measured.**", 6)
    for row in cost_rows:
        i = row[0]
        e = eq[i]
        for t, cell in (("f11", row[1]), ("f14", row[2])):
            got = (e[t]["floor"] + e[t]["add_var"]) / e[t]["floor"]
            ok &= check(f"ROI {i} {t} floor multiplier", got, num(cell))
        before = [e[t]["knee_before"] for t in ("f11", "f14", "f18")]
        after = [e[t]["knee_after"] for t in ("f11", "f14", "f18")]
        ok &= check(f"ROI {i} knee ratio before",
                    max(before) / min(before), num(row[3]))
        ok &= check(f"ROI {i} knee ratio after",
                    max(after) / min(after), num(row[4]))

    print("\nAmendment 6, the units table")
    prim = ["f11", "f14", "f18"]
    for band, label in (("low", "low band, the artefact alone"),
                        ("knee", "knee band, contaminated by the signal")):
        per = []
        for i in sorted({r["roi"] for r in recs}):
            v = [r["bands"][band]["snr"] for r in recs
                 if r["roi"] == i and r["aperture"] in prim]
            per.append(max(v) / min(v))
        ratio = float(np.median(per))
        row = rows_after(text, "| read from | ratio | differential bias |", 2)
        which = 0 if band == "low" else 1
        ok &= check(f"{band} primary-arm ratio", ratio, num(row[which][1]))
        ok &= check(f"{band} differential points", 5.7 * np.log(ratio),
                    num(row[which][2]), tol=0.05)

    print("\nAmendment 6a, the A4 table")
    a4 = rows_after(text, "### Amendment 6a", 1)
    for t, cell in zip(tags, a4[0]):
        ok &= check(f"high band, {t}", med(recs, t, "high"), num(cell), tol=0.03)

    print("\nAmendment 6, ranges quoted in prose (parsed from the doc, not hardcoded)")
    m = re.search(r"The floor rises by ([\d.]+)x to ([\d.]+)x", text)
    if not m:
        print("  FAIL floor-multiplier prose sentence not found")
        ok = False
    else:
        mults = [(eq[i][t]["floor"] + eq[i][t]["add_var"]) / eq[i][t]["floor"]
                 for i in eq for t in ("f11", "f14")]
        ok &= check("min floor multiplier", min(mults), float(m.group(1)))
        ok &= check("max floor multiplier", max(mults), float(m.group(2)))
    m = re.search(r"knee-band ratio of ([\d.]+)x to ([\d.]+)x", text)
    if not m:
        print("  FAIL residual-ratio prose sentence not found")
        ok = False
    else:
        afters = []
        for i in eq:
            a = [eq[i][t]["knee_after"] for t in ("f11", "f14", "f18")]
            afters.append(max(a) / min(a))
        ok &= check("min residual knee ratio", min(afters), float(m.group(1)))
        ok &= check("max residual knee ratio", max(afters), float(m.group(2)))

    print()
    print("all Amendment 6 figures reproduce" if ok else "SOME FIGURES DO NOT REPRODUCE")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
