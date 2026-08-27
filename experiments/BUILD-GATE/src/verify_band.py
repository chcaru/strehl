"""Re-derive every number quoted in BUILD-GATE-4 section 12. Exit 1 on mismatch.

Same discipline as `verify_tables.py`, which caught two real errors in the
section 4-9 draft: the report is checked against the artifacts rather than
against my memory of what the artifacts said. Numbers here are recomputed from
the band caches on disk, not copied from the run logs, so a stale log cannot
launder a wrong claim into the report.

It has already earned its place. Its first run rejected the draft's claim that
the analytic band fraction over-predicted by "2.7x"; the recomputed figure is
2.76x. The report text was corrected. The tolerance was not loosened.
"""
import os
import re
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bandboot                                                   # noqa: E402
from bandsweep import ARMS, do_score                              # noqa: E402

DOC = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__))))), "docs", "research",
    "BUILD-GATE-4.md")

SUBJ = ["bee-1-cpl", "flower-bud-alone-cpl", "119MSDCF", "coffee-bubbles",
        "109MSDCF"]

# section 12.1 -- the band split table
HI = {"bee-1-cpl": 0.1199, "119MSDCF": 0.1858, "109MSDCF": 0.3209,
      "flower-bud-alone-cpl": 0.3614, "coffee-bubbles": 0.4931}
MEAN_HI = 0.2962
OVERPRED = 2.76

# section 12.4 -- disjoint deltas and whether the 95% CI excludes zero
DISJ = {
    "bee-1-cpl":            [-0.02, -0.00, +0.01, -0.71, -1.19, -0.84],
    "flower-bud-alone-cpl": [-12.43, -2.24, +1.82, -17.41, -79.98, -87.30],
    "119MSDCF":             [+9.68, +16.57, +0.97, -26.79, -55.52, -69.12],
    "coffee-bubbles":       [+7.46, +11.74, +6.47, -9.87, -46.65, -59.20],
    "109MSDCF":             [+87.27, +43.80, -10.52, -39.93, -70.13, -82.02],
}
SIG = {
    "bee-1-cpl":            [0, 0, 0, 0, 0, 0],
    "flower-bud-alone-cpl": [1, 0, 0, 1, 1, 1],
    "119MSDCF":             [1, 1, 0, 1, 1, 1],
    "coffee-bubbles":       [1, 1, 1, 1, 1, 1],
    "109MSDCF":             [1, 1, 1, 1, 1, 1],
}


def parse_table(text, start, end, ncol):
    """Read the numbers OUT OF THE REPORT rather than trusting a transcription.

    Checking a computation against a constant I typed only proves I typed the
    constant twice. The claim under test is what the document says, so the
    document is what gets parsed. Unicode minus and the significance asterisk
    are normalised away; nothing else is.
    """
    seg = text.split(start, 1)[1].split(end, 1)[0]
    out = {}
    for line in seg.splitlines():
        m = re.match(r"^\|\s*`([^`]+)`\s*\|(.+)\|\s*$", line.strip())
        if not m:
            continue
        cells = [c.strip() for c in m.group(2).split("|")]
        if len(cells) != ncol:
            continue
        vals = []
        for c in cells:
            c = c.replace("\u2212", "-").replace("\\*", "").replace("*", "").strip()
            try:
                vals.append(float(c))
            except ValueError:
                vals = None
                break
        if vals is not None:
            out[m.group(1)] = vals
    return out


def main():
    bad = []
    text = open(DOC, encoding="utf-8").read()
    flat = re.sub(r"\s+", " ", text)

    doc_hi = parse_table(text, "### 12.1", "### 12.2", 1)
    doc_disj = parse_table(text, "### 12.4", "### 12.5", 6)
    if set(doc_hi) != set(SUBJ):
        bad.append("12.1 table in the report lists %r, expected %r"
                   % (sorted(doc_hi), sorted(SUBJ)))
    if set(doc_disj) != set(SUBJ):
        bad.append("12.4 table in the report lists %r, expected %r"
                   % (sorted(doc_disj), sorted(SUBJ)))
    for s in SUBJ:
        if s in doc_hi and abs(doc_hi[s][0] - HI[s]) > 5e-5:
            bad.append("REPORT 12.1 says %s=%.4f, verifier expects %.4f"
                       % (s, doc_hi[s][0], HI[s]))
        if s in doc_disj:
            for i, a in enumerate(ARMS[1:]):
                if abs(doc_disj[s][i] - DISJ[s][i]) > 5e-3:
                    bad.append("REPORT 12.4 says %s/%s=%.2f, verifier expects %.2f"
                               % (s, a, doc_disj[s][i], DISJ[s][i]))
    print("parsed from the report: %d rows in 12.1, %d rows in 12.4"
          % (len(doc_hi), len(doc_disj)))

    print("%-22s %9s %9s  %s" % ("subject", "hi_frac", "claimed", "verdict"))
    for s in SUBJ:
        _, hi = do_score(s)
        ok = abs(hi - HI[s]) <= 5e-4
        if not ok:
            bad.append("%s hi_fraction %.4f != claimed %.4f" % (s, hi, HI[s]))
        print("%-22s %9.4f %9.4f  %s" % (s, hi, HI[s], "ok" if ok else "MISMATCH"))

    mean_hi = float(np.mean(list(HI.values())))
    if abs(mean_hi - MEAN_HI) > 5e-4:
        bad.append("mean hi_fraction %.4f != quoted %.4f" % (mean_hi, MEAN_HI))
    if abs(0.8183 / mean_hi - OVERPRED) > 0.005:
        bad.append("over-prediction %.2fx != quoted %.2fx"
                   % (0.8183 / mean_hi, OVERPRED))
    print("mean hi_fraction %.4f, analytic 0.8183 is %.2fx it"
          % (mean_hi, 0.8183 / mean_hi))

    print()
    print("%-22s %-6s %9s %9s  %-5s %-5s" %
          ("subject", "arm", "disj d%", "claimed", "sig", "claim"))
    for s in SUBJ:
        o, _ = bandboot.run(s)
        for i, a in enumerate(ARMS[1:]):
            if a not in o:
                bad.append("%s missing arm %s" % (s, a))
                continue
            pd, ld, hd = o[a][1]
            sig = 0 if (ld <= 0 <= hd) else 1
            if abs(pd - DISJ[s][i]) > 0.02:
                bad.append("%s %s disj %.2f != claimed %.2f" % (s, a, pd, DISJ[s][i]))
            if sig != SIG[s][i]:
                bad.append("%s %s significance %d != claimed %d (CI %.2f..%.2f)"
                           % (s, a, sig, SIG[s][i], ld, hd))
            print("%-22s %-6s %9.2f %9.2f  %-5d %-5d"
                  % (s, a, pd, DISJ[s][i], sig, SIG[s][i]))

    # Claims stated in prose that a table cannot check.
    prose = [
        ("bee-1 null across the sweep", all(x == 0 for x in SIG["bee-1-cpl"])),
        ("G200 significant on 4 of 5", sum(SIG[s][3] for s in SUBJ) == 4),
        ("G170 insignificant on 3 of 5",
         sum(1 for s in SUBJ if SIG[s][2] == 0) == 3),
        ("G200 negative on all 5", all(DISJ[s][3] < 0 for s in SUBJ)),
        ("G170 worst is 109MSDCF at -10.52",
         min(DISJ[s][2] for s in SUBJ) == DISJ["109MSDCF"][2]),
        ("section 12 present in the report", "## 12." in text),
        ("section 11 marks its item retired", "RETIRES THIS ITEM" in flat),
        ("report quotes the corrected 2.76x", "2.76" in flat),
    ]
    print()
    for name, ok in prose:
        print("%-40s %s" % (name, "ok" if ok else "FAILED"))
        if not ok:
            bad.append(name)

    print()
    if bad:
        print("MISMATCHES (%d):" % len(bad))
        for b in bad:
            print("  " + b)
        return 1
    print("SECTION 12 VERIFIED -- every quoted number re-derived from the caches")
    return 0


if __name__ == "__main__":
    sys.exit(main())
