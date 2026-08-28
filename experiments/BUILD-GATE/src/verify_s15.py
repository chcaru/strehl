"""Re-derive every typed number in section 15 from section 15's own tables.

The discipline is the same as `verify_s14.py`: a number that appears in prose
must be recomputable from a table in the same section, and a number that
appears in two tables must agree between them. Cross-table agreement is the
part that matters here, because 15.1 is a summary of rows that also appear in
15.2 and a summary can drift from what it summarises.

CONCLUSIONS is pinned in this file for the reason ORCH gave: a verifier that
re-derives numbers is blind to a reversed verdict, because a reversal changes
no number. Measured, not assumed -- see `negctl_s13.py`, where flipping
section 13's headline answer passed the number-only verifier.
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPORT = os.path.abspath(os.path.join(HERE, "..", "..", "..",
                                      "docs", "research", "BUILD-GATE-4.md"))

ORDER = ["bee-1-cpl", "flower-bud-alone-cpl", "119MSDCF", "109MSDCF",
         "coffee-bubbles"]

CONCLUSIONS = [
    ("15 headline: blotch falls without a sharpness cost",
     "The per-band gate floor: the first move that cuts blotch without "
     "costing sharpness",
     ["cuts blotch at a sharpness cost",
      "cuts sharpness without costing blotch"]),
    ("15.3 band 1 is the largest share, NOT the whole mechanism",
     "Band 1 is **the largest single share, not the whole mechanism**",
     ["Band 1 is **the whole mechanism**",
      "the mottle is a band-1 artifact.**"]),
    ("15.3 SRAMP is the corroborating negative result",
     "The `SRAMP` arm is the negative result that corroborates this.",
     ["The `SRAMP` arm is the strongest arm in the sweep."]),
    ("15.4 section 13.6 is falsified by this section's own arms",
     "**That was wrong, and this section's own arms are what falsify it.**",
     ["**That was right, and this section's own arms confirm it.**"]),
    ("15.4 the gate CAN fire at mottle scale",
     "The gate fires there perfectly well when the floor permits it.",
     ["The gate cannot fire there whatever the floor permits."]),
    ("15.4 duty cycle is not a quality claim",
     "**`averaged` is a duty cycle, not a quality metric**",
     ["`averaged` is a quality metric"]),
    ("15.5 not a shipping recommendation",
     "**This is not a shipping recommendation.**",
     ["**This is a shipping recommendation.**"]),
    ("15.5 not a print-gate result",
     "**This is not a print-gate result.**",
     ["**This is a print-gate result.**"]),
]


class Check:
    def __init__(self):
        self.ok = self.bad = self.skip = 0
        self.msgs = []

    def eq(self, name, derived, quoted, tol=5e-3, atol=None):
        if quoted is None:
            self.skip += 1
            self.msgs.append("SKIP %s: anchor did not match in the report"
                             % name)
            return
        lim = atol if atol is not None else tol * max(1.0, abs(quoted))
        if abs(derived - quoted) <= lim:
            self.ok += 1
        else:
            self.bad += 1
            self.msgs.append("FAIL %s: report %s, derived %s"
                             % (name, quoted, derived))

    def same(self, name, a, b, tol=1e-9):
        self.eq(name, a, b, tol)

    def verdict(self, name, hay, required, forbidden):
        n = hay.count(required)
        if n != 1:
            self.bad += 1
            self.msgs.append("FAIL %s: pinned verdict found %d times, "
                             "expected exactly 1: %r"
                             % (name, n, required[:60]))
            return
        hits = [f for f in forbidden if f in hay]
        if hits:
            self.bad += 1
            self.msgs.append("FAIL %s: reversed verdict present: %r"
                             % (name, hits[0][:60]))
            return
        self.ok += 1

    def report(self, attempted):
        tot = self.ok + self.bad + self.skip
        print("\n  checked %d  failed %d  skipped %d  = %d, claims "
              "attempted %d" % (self.ok, self.bad, self.skip, tot, attempted))
        if tot != attempted:
            print("  PARTITION BROKEN: outcomes %d != claims attempted %d"
                  % (tot, attempted))
            return 1
        for m in self.msgs:
            print("  " + m)
        return 1 if self.bad else 0


def s15(t):
    idx = t.find("\n## 15.")
    if idx < 0:
        sys.exit("FATAL: report has no section 15")
    tail = t[idx + 1:]
    nxt = re.search(r"(?m)^## ", tail[1:])
    return (tail[:nxt.start() + 1] if nxt else tail)


def f(m, g=1):
    return float(m.group(g)) if m else None


def half_ulp(s):
    """Half of the last printed digit.

    A value printed as `53%` carries no more precision than +-0.5, so
    comparing it against a derived 52.56 with a RELATIVE tolerance asks the
    report to be more precise than it prints. Deriving the tolerance from the
    printed form is the honest test and it tightens as precision rises.
    """
    if "." not in s:
        return 0.5
    return 0.5 * 10 ** -len(s.split(".")[1])


def main():
    t = s15(open(REPORT, encoding="utf-8").read())
    c = Check()
    n = 0

    # ---- 15.1 headline rows
    t1 = {}
    for m in re.finditer(
            r"\|\s*`([^`]+)`\s*\|\s*(\d+)\s*\|\s*\*\*([-+][\d.]+)%\*\*\s*\|\s*"
            r"\[([-+][\d.]+)%,\s*([-+][\d.]+)%\]\s*\|\s*([-+][\d.]+)%\s*\|\s*"
            r"\*\*([-+][\d.]+)%\*\*\s*\|", t):
        t1[m.group(1)] = (int(m.group(2)), float(m.group(3)),
                          float(m.group(4)), float(m.group(5)),
                          float(m.group(6)), float(m.group(7)))
    assert len(t1) == 5, "15.1 parsed %d rows" % len(t1)

    # ---- 15.2 sweep rows
    t2 = {}
    for m in re.finditer(
            r"\|\s*`([^`]+)`\s*\|\s*`(\w+)`\s*\|\s*`([\d,]+)`\s*\|\s*"
            r"([-+][\d.]+)%\s*\|\s*([-+][\d.]+)%\s*\|\s*([-+][\d.]+)%\s*\|",
            t):
        t2[(m.group(1), m.group(2))] = (float(m.group(4)), float(m.group(5)),
                                        float(m.group(6)))
    assert len(t2) == 35, "15.2 parsed %d rows" % len(t2)

    # The summary must agree with the rows it summarises. This is the check
    # that catches a hand-edited headline.
    for s in ORDER:
        b, g, sh = t2[(s, "S32")]
        n += 1
        c.same("15.1/15.2 blotch %s" % s, t1[s][1], b)
        n += 1
        c.same("15.1/15.2 grain %s" % s, t1[s][4], g)
        n += 1
        c.same("15.1/15.2 sharp %s" % s, t1[s][5], sh)

    sh1 = [t1[s][5] for s in ORDER]
    gr1 = [t1[s][4] for s in ORDER]
    n += 1
    c.eq("15.1 sharp min", min(sh1),
         f(re.search(r"rises on all 5 subjects \(([-+][\d.]+)%", t)))
    n += 1
    c.eq("15.1 sharp max", max(sh1),
         f(re.search(r"rises on all 5 subjects \([-+][\d.]+% to "
                     r"([-+][\d.]+)%", t)))
    n += 1
    c.eq("15.1 grain min", min(gr1),
         f(re.search(r"Grain spans ([-+][\d.]+)%", t)))
    n += 1
    c.eq("15.1 grain max", max(gr1),
         f(re.search(r"Grain spans [-+][\d.]+% to ([-+][\d.]+)%", t)))

    # every headline sharpness must actually be positive, or the section's
    # title is false
    n += 1
    c.eq("15.1 all sharp positive", 1.0 if all(x > 0 for x in sh1) else 0.0,
         1.0)

    # ---- 15.2 prose
    allsh = [v[2] for v in t2.values()]
    n += 1
    c.eq("15.2 lowest sharpness cell", min(allsh),
         f(re.search(r"Lowest sharpness cell anywhere in the sweep: "
                     r"\*\*[\d.]+x\*\* \(([-+][\d.]+)%\)", t)))
    n += 1
    c.eq("15.2 sign agreement count",
         float(len(t2)),
         f(re.search(r"agree on direction in \*\*(\d+) of \d+\*\* cells", t)))
    n += 1
    c.eq("15.2 cell count",
         float(len(t2)),
         f(re.search(r"agree on direction in \*\*\d+ of (\d+)\*\* cells", t)))

    # ---- 15.3 correlations
    t3 = {}
    for m in re.finditer(
            r"\|\s*`([^`]+)`\s*\|\s*([-+][\d.]+)\s*\|\s*([-+][\d.]+)\s*\|\s*"
            r"(\*\*no\*\*|yes)\s*\|", t):
        t3[m.group(1)] = (float(m.group(2)), float(m.group(3)),
                          m.group(4) == "yes")
    assert len(t3) == 5, "15.3 parsed %d rows" % len(t3)
    for s in ORDER:
        n += 1
        c.eq("15.3 independence flag %s" % s,
             1.0 if abs(t3[s][0]) <= 0.9 else 0.0,
             1.0 if t3[s][2] else 0.0)
    n += 1
    c.eq("15.3 flagged count",
         float(sum(1 for s in ORDER if abs(t3[s][0]) > 0.9)),
         f(re.search(r"`\|r\| > 0\.9` on (\d+) of \d+ subjects", t)))

    # ---- 15.4 decomposition: shares must follow from the same row
    t4 = {}
    for m in re.finditer(
            r"\|\s*`([^`]+)`\s*\|\s*([-+][\d.]+)%\s*\|\s*\*\*([-+][\d.]+)%"
            r"\*\*\s*\|\s*([-+][\d.]+)%\s*\|\s*\*\*(\d+)%\*\*\s*\|\s*"
            r"([-+][\d.]+)%\s*\|", t):
        t4[m.group(1)] = (float(m.group(2)), float(m.group(3)),
                          float(m.group(4)), float(m.group(5)),
                          float(m.group(6)), m.group(5), m.group(6))
    assert len(t4) == 5, "15.4 parsed %d rows" % len(t4)
    for s in ORDER:
        j, b1, nb, share, exc, share_s, exc_s = t4[s]
        n += 1
        c.eq("15.4 share %s" % s, 100.0 * b1 / (b1 + nb), share,
             atol=half_ulp(share_s))
        n += 1
        c.eq("15.4 excess %s" % s,
             100.0 * (abs(b1 + nb) - abs(j)) / abs(j), exc,
             atol=half_ulp(exc_s))
        # band 1 must actually beat bands 2-6, or the prose is false
        n += 1
        c.eq("15.4 band1 beats coarse %s" % s,
             1.0 if abs(b1) > abs(nb) else 0.0, 1.0)
        # 15.4's joint column must be the same number as 15.1's
        n += 1
        c.same("15.4/15.1 joint %s" % s, j, t1[s][1])
    shares = [t4[s][3] for s in ORDER]
    n += 1
    c.eq("15.4 share min", min(shares),
         f(re.search(r"Band 1 alone carries (\d+)%-\d+% of the two-arm", t)))
    n += 1
    c.eq("15.4 share max", max(shares),
         f(re.search(r"Band 1 alone carries \d+%-(\d+)% of the two-arm", t)))

    # ---- 15.5 duty cycle
    t5 = {}
    for m in re.finditer(
            r"\|\s*`([^`]+)`\s*\|\s*`(NULL|S32)`\s*\|\s*"
            + r"\s*\|\s*".join([r"([\d.]+)%"] * 7) + r"\s*\|", t):
        t5[(m.group(1), m.group(2))] = [float(m.group(i))
                                        for i in range(3, 10)]
    assert len(t5) == 10, "15.5 parsed %d rows" % len(t5)
    for s in ORDER:
        n += 1
        c.same("15.5 band0 identical %s" % s,
               t5[(s, "NULL")][0], t5[(s, "S32")][0], tol=1e-9)
        # the capability claim: S32 must exceed the null at levels 3-4
        n += 1
        c.eq("15.5 S32 fires at L3-4 %s" % s,
             1.0 if max(t5[(s, "S32")][3], t5[(s, "S32")][4])
             > max(t5[(s, "NULL")][3], t5[(s, "NULL")][4]) else 0.0, 1.0)
    coarse = [max(t5[(s, "S32")][3], t5[(s, "S32")][4]) for s in ORDER]
    n += 1
    c.eq("15.5 S32 coarse max", max(coarse),
         f(re.search(r"`S32` reads [\d.]+%-([\d.]+)%", t)))
    n += 1
    c.eq("15.5 S32 coarse min", min(coarse),
         f(re.search(r"`S32` reads ([\d.]+)%-[\d.]+%", t)))

    print("15.1 rows %d, 15.2 rows %d, 15.3 rows %d, 15.4 rows %d, "
          "15.5 rows %d" % (len(t1), len(t2), len(t3), len(t4), len(t5)))

    if os.environ.get("BG_NO_CONCLUSIONS") == "1":
        print("\n  *** BG_NO_CONCLUSIONS=1: conclusion checks DISABLED. "
              "This is the pre-fix verifier, for commissioning only. ***")
    else:
        flat = re.sub(r"\s+", " ", t)
        for name, required, forbidden in CONCLUSIONS:
            n += 1
            c.verdict(name, flat, re.sub(r"\s+", " ", required),
                      [re.sub(r"\s+", " ", x) for x in forbidden])

    rc = c.report(n)
    print("\nVERIFY SECTION 15: %s" % ("GREEN" if rc == 0 else "RED"))
    return rc


if __name__ == "__main__":
    sys.exit(main())
