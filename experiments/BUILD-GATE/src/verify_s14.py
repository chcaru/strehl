"""Verify every TYPED number in section 14's prose against section 14's tables.

The chain this closes:

    TIFF masters -> ab_table.py / boot_head.py -> generated table files
                 -> s14_splice.py --check      -> the report's TABLES
                 -> THIS SCRIPT                -> the report's PROSE

`s14_splice.py --check` already proves the tables in the report are exactly
what the generators emit. What nothing checked until now is the prose, which
is where I type numbers by hand -- and hand-typed numbers in a print string
are precisely how floor_predict.py came to claim "b0 worst was 0.8%" long
after the real figure had become 4.3%.

Every check is anchored on a neighbouring literal, not on the bare value: a
short token like "1.42" or "4.3" occurs by chance elsewhere in a 71 KB report,
and an unanchored search would match a decoy and read green.

The summary partitions every claim into checked / failed / skipped and asserts
the three sum to the number of claims attempted, so a claim whose anchor
stopped matching cannot quietly read as a claim that passed.
"""
import os
import re
import sys

REPORT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                      "..", "..", "..", "docs", "research", "BUILD-GATE-4.md")
TOL = 5e-3


def text():
    with open(REPORT, "rb") as f:
        return f.read().decode("utf-8")


def s14(t):
    m = re.search(r"\n## 14\..*\Z", t, re.S)
    assert m, "section 14 not found"
    return m.group(0)


def sub(t, n):
    m = re.search(r"\n### %s[^\n]*\n(.*?)(?=\n### |\n## |\Z)" % re.escape(n),
                  t, re.S)
    assert m, "subsection %s not found" % n
    return m.group(1)


def _tol_for(s):
    """Half a unit in the last decimal place the prose actually quotes.

    A relative tolerance is wrong here. '0.997' and '0.998' differ by 7e-4,
    which any sane relative tolerance on a number near 1.0 will swallow, so a
    defect planted in the last quoted digit reads green. The precision the
    author wrote down is the precision the claim makes, and that is what gets
    checked. Commissioning caught exactly this: D1 and D7 were both missed
    until the tolerance was tied to the quoted decimal places.
    """
    s = s.strip()
    return 0.5 * 10 ** -(len(s.split(".")[1]) if "." in s else 0)


class Check:
    def __init__(self):
        self.ok = self.bad = self.skip = 0
        self.msgs = []

    def eq(self, name, derived, quoted, tol=None):
        """quoted is the matched STRING (or None when the anchor is gone)."""
        if quoted is None:
            self.skip += 1
            self.msgs.append("SKIP %s: anchor did not match in the report"
                             % name)
            return
        want = float(quoted)
        t = _tol_for(quoted) if tol is None else tol
        if abs(derived - want) <= t:
            self.ok += 1
        else:
            self.bad += 1
            self.msgs.append("FAIL %s: prose says %s, tables give %.6g "
                             "(tol %.6g)" % (name, quoted, derived, t))

    def le(self, name, derived, quoted):
        """Assert a derived value sits within a bound the prose states."""
        if quoted is None:
            self.skip += 1
            self.msgs.append("SKIP %s: anchor did not match in the report"
                             % name)
            return
        bound = float(quoted)
        if derived <= bound + _tol_for(quoted):
            self.ok += 1
        else:
            self.bad += 1
            self.msgs.append("FAIL %s: prose bounds it at %s, tables give %s"
                             % (name, quoted, derived))

    def report(self, attempted):
        tot = self.ok + self.bad + self.skip
        print("\n  checked %d  failed %d  skipped %d  = %d, claims attempted %d"
              % (self.ok, self.bad, self.skip, tot, attempted))
        if tot != attempted:
            print("  PARTITION BROKEN: outcomes %d != attempted %d"
                  % (tot, attempted))
            return 1
        for m in self.msgs:
            print("  " + m)
        if self.bad:
            print("\n  RED: %d prose number(s) disagree with the tables"
                  % self.bad)
            return 1
        if self.skip:
            print("\n  RED: %d claim(s) unverified (anchor drift)" % self.skip)
            return 1
        print("\n  GREEN: every typed number in section 14 re-derives from "
              "section 14's tables.")
        return 0


def grab(body, pattern, group=1):
    """Anchored extraction, returning the matched STRING.

    The string is kept rather than a float so the checker can see how many
    decimal places the prose committed to and hold the claim to exactly that
    precision. Returns None if the anchor is gone.
    """
    m = re.search(pattern, body.replace("**", ""), re.S)
    return m.group(group) if m else None


def fgrab(body, pattern, group=1):
    """grab() for the few places a value is needed for arithmetic."""
    s = grab(body, pattern, group)
    return float(s) if s is not None else None


def sweep_rows(body):
    """{subject: {arm: (blotch, grain, sharp, avg)}} from the 14.2 tables."""
    out, cur = {}, None
    for line in body.replace("**", "").split("\n"):
        m = re.match(r"^`([A-Za-z0-9-]+)`, N=(\d+),", line)
        if m:
            cur = m.group(1)
            out[cur] = {}
            continue
        m = re.match(r"^\|\s*`?(WHITE200|G\d+)`?[^|]*\|[^|]*\|[^|]*\|"
                     r"\s*([-+][\d.]+)%\s*\|\s*([-+][\d.]+)%\s*\|"
                     r"\s*([-+][\d.]+)%\s*\|\s*([\d.]+)%\s*\|", line)
        if m and cur:
            out[cur][m.group(1)] = (float(m.group(2)), float(m.group(3)),
                                    float(m.group(4)), float(m.group(5)))
    return out


def corrs(body):
    """{subject: r(sharp,grain)} from the 14.2 caption lines."""
    body = body.replace("**", "")
    subs = re.findall(r"^`([A-Za-z0-9-]+)`, N=", body, re.M)
    rs = re.findall(r"`r\(sharp/tex, grain\)` = ([-+][\d.]+)", body)
    return dict(zip(subs, [float(x) for x in rs]))


def main():
    t = s14(text())
    c = Check()
    n = 0

    # The generated table blocks are numbered by their own scheme and are
    # spliced under prose headers that do NOT match. Bind by meaning, not by
    # number, so the mapping is visible and cannot drift silently.
    b1 = sub(t, "14.1")           # summary and retraction
    b2 = sub(t, "14.2")           # the sweep tables
    b3 = sub(t, "14.3")           # matched grain
    bboot = sub(t, "14.4")        # blotch with intervals
    bcomp = sub(t, "14.5")        # compensation formula
    bwl = sub(t, "14.6")          # weight law
    brt = sub(t, "14.7")          # runtime

    rows = sweep_rows(b2)
    rr = corrs(b2)
    assert len(rows) == 5 and len(rr) == 5, (len(rows), len(rr))
    print("14.2 parsed %d subjects, %d correlations" % (len(rows), len(rr)))

    # --- 14.1: the correlation range, and the count of degenerate subjects
    hi = sorted(v for v in rr.values() if v > 0.9)
    n += 1
    c.eq("14.1 r lower bound", min(hi),
         grab(b1, r"correlates with my grain column at\s+\+([\d.]+)\s+to"))
    n += 1
    c.eq("14.1 r upper bound", max(hi),
         grab(b1, r"at\s+\+[\d.]+\s+to\s+\+([\d.]+)\s*\n?\s*on"))
    n += 1
    c.eq("14.1 degenerate subject count", float(len(hi)),
         "4" if re.search(r"on\s*\n?\s*four of five subjects", b1)
         else None)

    # bee-1's decoupled correlation, quoted in 14.3
    n += 1
    c.eq("14.3 bee-1 r", rr["bee-1-cpl"],
         grab(b3, r"`bee-1-cpl` at\s*\n?\s*\+([\d.]+)"))

    # --- 14.3 roots: the matched-grain range and the +/-1.1% claim
    # The root readings are the ONLY bolded signed percentages in 14.3, so
    # the bold markers are the anchor and must not be stripped here.
    roots = [float(x) for x in
             re.findall(r"\*\*([-+][\d.]+)%\*\*", b3)]
    assert len(roots) == 6, "expected 6 root readings, parsed %d" % len(roots)
    n += 1
    c.eq("14.1 matched-grain min", min(roots),
         grab(b1, r"the fix costs\s*\n?\s*([-+][\d.]+)% to"))
    n += 1
    c.eq("14.1 matched-grain max", max(roots),
         grab(b1, r"the fix costs\s*\n?\s*[-+][\d.]+% to ([-+][\d.]+)%"))
    n += 1
    c.eq("14.7 roots inside 1.1pct",
         float(sum(1 for r in roots if abs(r) <= 1.1)),
         "5" if re.search(r"five of the six root readings", brt) else None)
    n += 1
    c.eq("14.7 root count", float(len(roots)),
         "6" if re.search(r"of the six root readings", brt) else None)

    # --- bee-1's flat sharpness span and its grain
    bee = rows["bee-1-cpl"]
    span = max(abs(v[2]) for v in bee.values())
    n += 1
    c.eq("14.1 bee-1 sharp span", span,
         grab(b1, r"`bee-1-cpl`'s ([\d.]+)% arm span"))
    n += 1
    c.eq("14.3 bee-1 worst grain", abs(min(v[1] for v in bee.values())),
         grab(b3, r"by up to -([\d.]+)% --"))
    worst_arm = min(bee, key=lambda a: bee[a][1])
    n += 1
    c.eq("14.3 bee-1 sharp at worst-grain arm", bee[worst_arm][2],
         grab(b3, r"that removes the most grain moves sharpness by "
                  r"([-+][\d.]+)%"))

    # --- 14.5 weight law: eligible rows only
    elig = []
    for line in bwl.replace("**", "").split("\n"):
        m = re.match(r"^\|\s*`([A-Za-z0-9-]+)`\s*\|\s*([-+][\d.]+)%\s*\|"
                     r"\s*([-+][\d.]+)%\s*\|\s*([-+][\d.]+)%\s*\|"
                     r"\s*([\d.]+)%\s*\|\s*(yes|no[^|]*)\s*\|", line)
        if m and m.group(6).strip() == "yes":
            elig.append((float(m.group(2)), float(m.group(3)),
                         float(m.group(4)), float(m.group(5))))
    assert len(elig) == 4, len(elig)
    n += 1
    c.eq("14.1 grain move max", max(e[1] for e in elig),
         grab(b1, r"moves grain by up to ([\d.]+)%"))
    n += 1
    c.eq("14.1 blotch move max", max(e[0] for e in elig),
         grab(b1, r"blotch by up to ([\d.]+)%"))
    n += 1
    c.eq("14.6 grain move min", min(e[1] for e in elig),
         grab(bwl, r"grain moves ([\d.]+)% to"))
    bound = grab(bwl, r"both arms gate under ([\d.]+)% of coefficients")
    fbound = float(bound) if bound is not None else None
    n += 1
    c.le("14.6 worst level within stated bound",
         max(e[3] for e in elig), bound)
    n += 1
    c.eq("14.6 one-in-N", 1.0 / (fbound / 100.0) if fbound else 0.0,
         grab(bwl, r"at most 1 in\s*\n?\s*(\d+)"), tol=0.5)

    # --- 14.4 blotch: the largest interval-backed cut
    moved = []
    for line in bboot.replace("**", "").split("\n"):
        m = re.match(r"^\|\s*`([A-Za-z0-9-]+)`\s*\|\s*`(G\d+)`\s*\|"
                     r"\s*([-+][\d.]+)%\s*\|\s*\[([-+][\d.]+)%,\s*"
                     r"([-+][\d.]+)%\]\s*\|\s*(yes|no)\s*\|", line)
        if m:
            moved.append((m.group(1), m.group(2), float(m.group(3)),
                          m.group(6) == "yes"))
    assert len(moved) == 35, len(moved)
    best = min(v for _, _, v, ok in moved if ok)
    n += 1
    c.eq("14.4 largest cut", best,
         grab(bboot, r"([-+][\d.]+)%\s*\[", 1))
    n += 1
    c.eq("14.1 largest cut", best,
         grab(b1, r"blotch cut anywhere in the sweep is\s*([-+][\d.]+)%"))
    req = fgrab(bboot, r"needs\s*\n?\s*-([\d.]+)%")
    n += 1
    c.eq("14.4 share of requirement", 100.0 * abs(best) / req if req else 0.0,
         grab(bboot, r"that is ([\d.]+)% of the requirement"))
    n += 1
    c.eq("14.4 arms moved", float(sum(1 for _, _, _, ok in moved if ok)),
         grab(bboot, r"(\d+) of 35 measured-floor arms moved", 1))
    n += 1
    c.eq("14.4 flower G260 grain", rows["flower-bud-alone-cpl"]["G260"][1],
         grab(bboot, r"costs ([-+][\d.]+)% grain"))
    n += 1
    c.eq("14.4 flower r", rr["flower-bud-alone-cpl"],
         grab(bboot, r"correlates\s*\n?\s*\+([\d.]+) with grain"))

    # --- 14.5 compensation: k_obs range, decoy range, margin
    kobs, kpred, errs, decoy = [], [], [], []
    for line in bcomp.split("\n"):
        m = re.match(r"^\|\s*`([A-Za-z0-9-]+)`\s*\|\s*([\d.]+)\s*\|"
                     r"\s*([\d.]+)\s*\|\s*([\d.]+)\s*\|\s*([-+][\d.]+)%\s*\|"
                     r"\s*([-+][\d.]+)%\s*\|", line)
        if m:
            kpred.append(float(m.group(3)))
            kobs.append(float(m.group(4)))
            errs.append(abs(float(m.group(5))))
            decoy.append(abs(float(m.group(6))))
    assert len(kobs) == 5, len(kobs)
    b5c = bcomp
    n += 1
    c.eq("14.1 k_obs min", min(kobs),
         grab(b1, r"compensating `k` is\s*\n?\s*([\d.]+)-"))
    n += 1
    c.eq("14.1 k_obs max", max(kobs),
         grab(b1, r"compensating `k` is\s*\n?\s*[\d.]+-([\d.]+)"))
    n += 1
    c.eq("14.1 worst b0 err", max(errs),
         grab(b1, r"gating rate to within ([\d.]+)%"))
    n += 1
    c.eq("14.1 decoy min", min(decoy),
         grab(b1, r"decoy that misses by\s*\n?\s*([\d.]+)-"))
    n += 1
    c.eq("14.1 decoy max", max(decoy),
         grab(b1, r"decoy that misses by\s*\n?\s*[\d.]+-([\d.]+)%"))
    n += 1
    c.eq("14.5 decoy min", min(decoy),
         grab(b5c, r"misses by ([\d.]+)-"))
    n += 1
    c.eq("14.5 decoy max", max(decoy),
         grab(b5c, r"misses by [\d.]+-([\d.]+)%"))
    n += 1
    c.eq("14.5 b0 worst", max(errs),
         grab(b5c, r"against band 0's worst of ([\d.]+)%"))
    n += 1
    c.eq("14.5 margin", max(decoy) / max(errs),
         grab(b5c, r"a ([\d.]+)x\s*\n?\s*margin"))
    n += 1
    c.eq("14.5 k_pred min", min(kpred),
         grab(b5c, r"strictness was `2.0/xw` -- about ([\d.]+) to"))
    n += 1
    c.eq("14.5 k_pred max", max(kpred),
         grab(b5c, r"about [\d.]+ to ([\d.]+)"))

    # --- 14.7 runtime
    ratios = [float(x) for x in
              re.findall(r"\|\s*([\d.]+)x\s*\|", brt)]
    assert len(ratios) == 5, len(ratios)
    srt = sorted(ratios)
    n += 1
    c.eq("14.7 median", srt[2], grab(brt, r"Median ([\d.]+)x"))
    n += 1
    c.eq("14.7 range min", min(ratios), grab(brt, r"range ([\d.]+)-"))
    n += 1
    c.eq("14.7 range max", max(ratios), grab(brt, r"range [\d.]+-([\d.]+)x"))
    n += 1
    c.eq("14.7 coffee ratio", max(ratios),
         grab(brt, r"`coffee-bubbles` at ([\d.]+)x"))

    print("14.3 roots %d, 14.4 boot rows %d, 14.5 subjects %d, 14.7 ratios %d"
          % (len(roots), len(moved), len(kobs), len(ratios)))
    return c.report(n)


if __name__ == "__main__":
    sys.exit(main())
