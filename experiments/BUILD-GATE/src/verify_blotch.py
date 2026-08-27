"""Verifier for section 13 of BUILD-GATE-4.md.

Two properties this has to have, both learned the hard way in this project.

1. It PARSES THE REPORT. A verifier that recomputes numbers and compares them
   to its own hardcoded copies proves only that it agrees with itself. Every
   value checked below is read out of the markdown and compared against a fresh
   derivation from the artifacts on disk.

2. It PARTITIONS. Every table row found is counted into exactly one of
   checked / skipped / failed, and those must sum to the number of rows found.
   A count that does not move is the same glyph whether nothing was wrong or
   nothing was examined.
"""
import os
import re
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

REPORT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                      "..", "..", "..", "docs", "research", "BUILD-GATE-4.md")
TOL = 5e-4


class Check:
    def __init__(self):
        self.ok = self.bad = self.skip = 0
        self.msgs = []

    def eq(self, name, got, want, tol=TOL):
        if want is None:
            self.skip += 1
            self.msgs.append("SKIP %s: not found in report" % name)
            return
        if abs(got - want) <= tol * max(1.0, abs(want)):
            self.ok += 1
        else:
            self.bad += 1
            self.msgs.append("FAIL %s: report %s, derived %s"
                             % (name, want, got))

    def report(self, nfound):
        tot = self.ok + self.bad + self.skip
        print("\n  checked %d  failed %d  skipped %d  = %d, rows found %d"
              % (self.ok, self.bad, self.skip, tot, nfound))
        if tot != nfound:
            print("  PARTITION BROKEN: outcomes %d != rows found %d"
                  % (tot, nfound))
            return 1
        for m in self.msgs:
            print("  " + m)
        return 1 if self.bad else 0


def text():
    with open(REPORT, "rb") as f:
        return f.read().decode("utf-8")


def section(t, n):
    m = re.search(r"\n### %s[^\n]*\n(.*?)(?=\n### |\n## |\Z)" % re.escape(n),
                  t, re.S)
    assert m, "section %s not found" % n
    return m.group(1)


def main():
    t = text()
    c = Check()
    nrows = 0

    # --- 13.4, the deliverable table -------------------------------------
    import blotch as bl
    import blotch_boot as bb
    import blotch_sweep as bs
    from blotch_table import DISJ, ORDER, CONVICTED

    body = section(t, "13.4").replace("**", "")
    cur = None
    got = {}
    for line in body.split("\n"):
        m = re.match(r"^\|\s*(`[^`]+`)?\s*\|[^|]*\|\s*(WHITE200|G\d+)\s*\|"
                     r"\s*([\d.]+)[^|]*\|\s*([\d.]+)(?:\s*\[([\d.]+),\s*([\d.]+)\])?"
                     r"[^|]*\|\s*([-+][\d.]+)%[^|]*\|\s*([\d.]+)\s*\|", line)
        if not m:
            continue
        if m.group(1):
            cur = m.group(1).strip("`")
        arm = m.group(2)
        got[(cur, arm)] = (float(m.group(4)),
                           float(m.group(5)) if m.group(5) else None,
                           float(m.group(6)) if m.group(6) else None,
                           float(m.group(7)), float(m.group(8)))
    nrows += len(got)
    print("13.4 parsed %d arm rows from the report" % len(got))

    for s in ORDER:
        rows, _, _, _, _ = bs.run(s)
        bo, _ = bb.run(s)
        b = rows["WHITE200"]
        for i, a in enumerate(bl.ARMS):
            key = (s, a)
            if key not in got:
                c.skip += 1
                c.msgs.append("SKIP %s %s: row absent from report" % (s, a))
                nrows += 1
                continue
            g = got[key]
            m, lo, hi = bo[a]
            d = 0.0 if a == "WHITE200" else DISJ[s][i - 1][0]
            sub = Check()
            sub.eq("blotch", m, g[0])
            if g[1] is not None:
                sub.eq("lo", lo, g[1])
                sub.eq("hi", hi, g[2])
            sub.eq("sharp", d, g[3], tol=5e-3)
            sub.eq("grain", rows[a][1] / b[1], g[4])
            if sub.bad:
                c.bad += 1
                c.msgs.append("FAIL %s %s: %s" % (s, a, "; ".join(sub.msgs)))
            else:
                c.ok += 1

    # --- 13.5, the knees --------------------------------------------------
    body = section(t, "13.5").replace("**", "")
    kn = {}
    for line in body.split("\n"):
        m = re.match(r"^\|\s*`([^`]+)`\s*\|\s*(\d+)\s*\|\s*(G\d+|none)\s*\|"
                     r"\s*(?:\*\*)?([-+][\d.]+)%|^\|\s*`([^`]+)`\s*\|\s*(\d+)"
                     r"\s*\|\s*none\s*\|", line)
        if not m:
            continue
        if m.group(1):
            kn[m.group(1)] = (m.group(3), float(m.group(4)))
        else:
            kn[m.group(5)] = ("none", None)
    nrows += len(kn)
    print("13.5 parsed %d knee rows" % len(kn))
    for s in ORDER:
        if s not in kn:
            c.skip += 1
            c.msgs.append("SKIP knee %s: absent" % s)
            nrows += 1
            continue
        rows, _, _, _, _ = bs.run(s)
        bo, _ = bb.run(s)
        cand = []
        for i, a in enumerate(bl.ARMS):
            if a == "WHITE200":
                continue
            d, star = DISJ[s][i - 1]
            if bo[a][2] < 1.0 and (star == 0 or d > 0):
                cand.append((bo[a][0], a))
        best = min(cand) if cand else None
        want_arm, want_pct = kn[s]
        if best is None:
            if want_arm == "none":
                c.ok += 1
            else:
                c.bad += 1
                c.msgs.append("FAIL knee %s: report %s, derived none"
                              % (s, want_arm))
        elif want_arm != best[1]:
            c.bad += 1
            c.msgs.append("FAIL knee %s: report %s, derived %s"
                          % (s, want_arm, best[1]))
        elif abs((best[0] - 1) * 100 - want_pct) > 5e-3:
            c.bad += 1
            c.msgs.append("FAIL knee %s pct: report %s, derived %.4f"
                          % (s, want_pct, (best[0] - 1) * 100))
        else:
            c.ok += 1

    # --- 13.7, the degeneracy correlations --------------------------------
    body = section(t, "13.7")
    cor = {}
    for line in body.split("\n"):
        m = re.match(r"^\|\s*`([^`]+)`\s*\|\s*(?:\*\*)?([\d.]+)(?:\*\*)?\s*\|"
                     r"\s*(?:\*\*)?([\d.]+)(?:\*\*)?\s*\|", line)
        if m:
            cor[m.group(1)] = (float(m.group(2)), float(m.group(3)))
    nrows += len(cor)
    print("13.7 parsed %d correlation rows" % len(cor))
    for s in ORDER:
        if s not in cor:
            c.skip += 1
            c.msgs.append("SKIP corr %s: absent" % s)
            nrows += 1
            continue
        rows, _, _, _, _ = bs.run(s)
        g = np.array([rows[a][1] for a in bl.ARMS if a in rows])
        f = np.array([rows[a][2] for a in bl.ARMS if a in rows])
        x = np.array([rows[a][3] for a in bl.ARMS if a in rows])
        sub = Check()
        sub.eq("flat", float(np.corrcoef(g, f)[0, 1]), cor[s][0])
        sub.eq("tex", float(np.corrcoef(g, x)[0, 1]), cor[s][1])
        if sub.bad:
            c.bad += 1
            c.msgs.append("FAIL corr %s: %s" % (s, "; ".join(sub.msgs)))
        else:
            c.ok += 1

    # --- 13.8, authority and Spearman -------------------------------------
    body = section(t, "13.8")
    au = {}
    for line in body.split("\n"):
        m = re.match(r"^\|\s*`([^`]+)`\s*\|\s*(\d+)\s*\|\s*([\d.]+)%\s*\|", line)
        if m:
            au[m.group(1)] = (int(m.group(2)), float(m.group(3)))
    nrows += len(au)
    print("13.8 parsed %d authority rows" % len(au))
    ns, sp = [], []
    for s in ORDER:
        d = [0.0] + [x[0] for x in DISJ[s]]
        v = max(d) - min(d)
        ns.append(bl.NFRAMES[s])
        sp.append(v)
        if s not in au:
            c.skip += 1
            c.msgs.append("SKIP authority %s: absent" % s)
            nrows += 1
            continue
        sub = Check()
        sub.eq("N", float(bl.NFRAMES[s]), float(au[s][0]))
        sub.eq("span", v, au[s][1], tol=5e-3)
        if sub.bad:
            c.bad += 1
            c.msgs.append("FAIL authority %s: %s" % (s, "; ".join(sub.msgs)))
        else:
            c.ok += 1

    m = re.search(r"Spearman\(N, sharpness authority\) = ([-+][\d.]+)", body)
    nrows += 1
    r = float(np.corrcoef(np.argsort(np.argsort(ns)),
                          np.argsort(np.argsort(sp)))[0, 1])
    c.eq("spearman", r, float(m.group(1)) if m else None, tol=5e-3)

    # --- headline arithmetic ----------------------------------------------
    need = (1.0 / CONVICTED - 1.0) * 100.0
    body = section(t, "13.6").replace("**", "")
    m = re.search(r"needs -([\d.]+)%", t)
    nrows += 1
    c.eq("needed reduction", need, -float(m.group(1)) if m else None, tol=5e-3)

    m = re.search(r"\*\*6\.1%\*\*", t)
    nrows += 1
    bo, _ = bb.run("bee-1-cpl")
    share = 100 * (1 - bo["G400"][0]) / (1 - 1 / CONVICTED)
    c.eq("bee-1 knee share", share, 6.1 if m else None, tol=1e-2)

    rc = c.report(nrows)
    print("\nVERIFY SECTION 13: %s" % ("GREEN" if rc == 0 else "RED"))
    return rc


if __name__ == "__main__":
    sys.exit(main())
