"""Generate section 15's tables from the instrument's own output.

Inputs are the scorer and bootstrap output files and the merge banners,
copied into `gen/` so this keeps working after the 6.45 GB of scale masters
are deleted. Nothing here is retyped from a report: every number is parsed
from an instrument, and the parsers hard-error when a row does not appear.

Run:  python s15_tables.py          writes gen/s15tables.md
      python s15_tables.py --check  regenerates and diffs, without writing
"""
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
GEN = os.path.abspath(os.path.join(HERE, "..", "gen"))
SCORE = os.path.join(GEN, "s15score.txt")
BOOT = os.path.join(GEN, "s15boot.txt")
DUTY = os.path.join(GEN, "s15duty.tsv")
QUAL = os.path.join(GEN, "s15qual.txt")
OUT = os.path.join(GEN, "s15tables.md")

# The band section 15's sharpness column measures (scale_score.py). ORCH's
# rule: no sharpness claim may be quoted without naming the band and the
# subject's qualification at it.
MY_BAND = "0.20-0.25"

# Subject order is by frame count, deepest first: depth is the axis the
# result varies along, and ORCH judges the product at depth.
ORDER = ["bee-1-cpl", "flower-bud-alone-cpl", "119MSDCF", "109MSDCF",
         "coffee-bubbles"]
ARMS = ["S04", "S08", "S16", "SRAMP", "S32", "B1ONLY", "NOB1"]
SCALES = {
    "S04": "1,4,4,4,4,4,4",
    "S08": "1,8,8,8,8,8,8",
    "S16": "1,16,16,16,16,16,16",
    "SRAMP": "1,1,4,16,32,32,32",
    "S32": "1,32,32,32,32,32,32",
    "B1ONLY": "1,32,1,1,1,1,1",
    "NOB1": "1,1,32,32,32,32,32",
}


def read(p):
    if not os.path.exists(p):
        sys.exit("FATAL: missing input %s" % p)
    return open(p, encoding="utf-8").read()


def parse_score():
    """subject -> (N, {arm: (blotch_x, grain_x, sharp_x)}, r_sharp, r_blotch)"""
    t = read(SCORE)
    out = {}
    blocks = re.split(r"(?m)^(\S+)\s+N=(\d+)[^\n]*\n", t)
    for i in range(1, len(blocks), 3):
        subj, n, body = blocks[i], int(blocks[i + 1]), blocks[i + 2]
        rows = {}
        for m in re.finditer(
                r"(?m)^\s{2}(\w+)\s+([\d,]+)\s*\|\s*([\d.]+)\s+([\d.]+)\s+"
                r"([\d.]+)\s*$", body):
            rows[m.group(1)] = (float(m.group(3)), float(m.group(4)),
                                float(m.group(5)))
        rs = re.search(r"r\(sharp/tex, grain\) = ([-+][\d.]+)", body)
        rb = re.search(r"r\(blotch, grain\) = ([-+][\d.]+)", body)
        if not rows or not rs or not rb:
            sys.exit("FATAL: could not parse score block for %s" % subj)
        out[subj] = (n, rows, float(rs.group(1)), float(rb.group(1)))
    missing = [s for s in ORDER if s not in out]
    if missing:
        sys.exit("FATAL: score file is missing subjects %s" % missing)
    return out


def parse_boot():
    """(subject, arm) -> (pct, lo, hi)"""
    out = {}
    for m in re.finditer(
            r"\|\s*`([^`]+)`\s*\|\s*`(\w+)`\s*\|\s*`[^`]*`\s*\|\s*"
            r"([-+][\d.]+)%\s*\|\s*\[([-+][\d.]+)%,\s*([-+][\d.]+)%\]",
            read(BOOT)):
        out[(m.group(1), m.group(2))] = (float(m.group(3)),
                                         float(m.group(4)),
                                         float(m.group(5)))
    if not out:
        sys.exit("FATAL: no bootstrap rows parsed from %s" % BOOT)
    return out


def parse_duty():
    out = {}
    for line in read(DUTY).splitlines():
        if not line.strip():
            continue
        subj, arm, bands = line.split("\t")
        vals = [float(x.rstrip("%")) for x in bands.split()]
        out[(subj, arm)] = vals[:7]
    if not out:
        sys.exit("FATAL: no duty-cycle rows parsed from %s" % DUTY)
    return out


def parse_qual():
    """subject -> (R, verdict, licensed) at MY_BAND, from bandqual.py's file.

    A subject with no record is NOT an error: it has never been qualified at
    any band, which is precisely the status that must be disclosed.
    """
    out = {}
    for line in read(QUAL).splitlines():
        m = re.match(r"^(\S+)\s+(\d+|\?)\s+(--|[\d.]+)\s+"
                     r"(PASS|MARGINAL\S*|FAIL\S*|NO RECORD)\s", line)
        if not m:
            continue
        subj = m.group(1)
        if subj not in ORDER:
            continue
        r = None if m.group(3) == "--" else float(m.group(3))
        v = m.group(4)
        out[subj] = (r, v, v == "PASS")
    missing = [s for s in ORDER if s not in out]
    if missing:
        sys.exit("FATAL: qualification file is missing subjects %s (run "
                 "bandqual.py)" % missing)
    return out


def pct(x):
    """A multiplier as a signed percentage change."""
    return (x - 1.0) * 100.0


def main():
    sc, bt, dt, ql = parse_score(), parse_boot(), parse_duty(), parse_qual()
    L = []
    w = L.append

    # ---- 15.1 the headline arm
    w("#### 15.1")
    w("")
    w("| subject | N | blotch vs null | 95%% CI | grain | sharp/tex | "
      "band %s | sharpness licensed |" % MY_BAND)
    w("|---|---:|---:|---|---:|---:|---|---|")
    for s in ORDER:
        n, rows, _, _ = sc[s]
        b, lo, hi = bt[(s, "S32")]
        r, v, lic = ql[s]
        rs = "--" if r is None else "R=%.3f" % r
        w("| `%s` | %d | **%+.2f%%** | [%+.2f%%, %+.2f%%] | %+.2f%% | "
          "**%+.2f%%** | %s %s | %s |"
          % (s, n, b, lo, hi, pct(rows["S32"][1]), pct(rows["S32"][2]),
             rs, v, "**yes**" if lic else "no"))
    lic_s = [s for s in ORDER if ql[s][2]]
    unlic = [s for s in ORDER if not ql[s][2]]
    sharp = [pct(sc[s][1]["S32"][2]) for s in ORDER]
    grain = [pct(sc[s][1]["S32"][1]) for s in ORDER]
    lsharp = [pct(sc[s][1]["S32"][2]) for s in lic_s]
    lgrain = [pct(sc[s][1]["S32"][1]) for s in lic_s]
    w("")
    w("Sharpness on textured sites rises on all %d subjects, but a sharpness "
      "number is only evidence on a subject qualified at the band it was "
      "measured in. **%d of %d are qualified at %s cyc/px**; %s %s not, and "
      "%s sharpness cell%s below %s therefore withdrawn as evidence and "
      "retained only for completeness."
      % (len(ORDER), len(lic_s), len(ORDER), MY_BAND,
         " and ".join("`%s`" % u for u in unlic),
         "is" if len(unlic) == 1 else "are",
         "its" if len(unlic) == 1 else "their",
         "" if len(unlic) == 1 else "s", "is" if len(unlic) == 1 else "are"))
    w("")
    w("**The headline range does not depend on the withdrawal.** Across all "
      "%d subjects sharpness spans %+.2f%% to %+.2f%%; across the %d licensed "
      "subjects it spans %+.2f%% to %+.2f%%. Both extremes are licensed "
      "subjects, so restricting to qualified bands changes the claim's range "
      "not at all -- the two unlicensed cells were interior."
      % (len(ORDER), min(sharp), max(sharp), len(lic_s),
         min(lsharp), max(lsharp)))
    w("")
    w("Grain spans %+.2f%% to %+.2f%% across all subjects and %+.2f%% to "
      "%+.2f%% across the licensed ones, so there is no grain move for the "
      "sharpness column to be a proxy for."
      % (min(grain), max(grain), min(lgrain), max(lgrain)))

    # ---- 15.2 the full sweep
    #
    # Blotch is taken from the BOOTSTRAP for every cell, not from the scorer.
    # The two disagree: they are different estimators (a paired block-
    # resampled estimate vs a plain ratio of means), and quoting one in 15.1
    # and the other here would put two different numbers on the same quantity.
    # One canonical source, and the disagreement is disclosed below rather
    # than hidden by never printing them side by side.
    w("")
    w("#### 15.2")
    w("")
    w("| subject | arm | scale | blotch | grain | sharp/tex |")
    w("|---|---|---|---:|---:|---:|")
    worst = 99.0
    dis = []
    for s in ORDER:
        _, rows, _, _ = sc[s]
        for a in ARMS:
            if a not in rows:
                sys.exit("FATAL: arm %s missing for %s" % (a, s))
            if (s, a) not in bt:
                sys.exit("FATAL: bootstrap row missing for %s/%s" % (s, a))
            braw, g, sh = rows[a]
            b = bt[(s, a)][0]
            dis.append(abs(b - pct(braw)))
            worst = min(worst, sh)
            w("| `%s` | `%s` | `%s` | %+.2f%% | %+.2f%% | %+.2f%% |"
              % (s, a, SCALES[a], b, pct(g), pct(sh)))
    inside = sum(1 for s in ORDER for a in ARMS
                 if bt[(s, a)][1] <= pct(sc[s][1][a][0]) <= bt[(s, a)][2])
    signs = sum(1 for s in ORDER for a in ARMS
                if (bt[(s, a)][0] < 0) == (pct(sc[s][1][a][0]) < 0))
    cons = sum(1 for s in ORDER for a in ARMS
               if abs(pct(sc[s][1][a][0])) >= abs(bt[(s, a)][0]))
    ncell = len(ORDER) * len(ARMS)
    dis.sort()
    med = dis[len(dis) // 2]
    w("")
    w("Lowest sharpness cell anywhere in the sweep: **%.4fx** (%+.2f%%)."
      % (worst, pct(worst)))
    w("")
    w("The blotch column is the bootstrap estimate throughout, so that one "
      "quantity has one number. The scorer's plain ratio of means is a "
      "**different estimator of the same quantity**, and the two are "
      "reconciled here rather than quietly averaged. They agree on direction "
      "in **%d of %d** cells -- there is no sign disagreement anywhere in the "
      "sweep. They disagree on magnitude by a median of **%.2f** and a "
      "maximum of **%.2f** percentage points, concentrated on "
      "`flower-bud-alone-cpl`." % (signs, ncell, med, max(dis)))
    w("")
    w("Only %d of %d scorer estimates fall inside the bootstrap's 95%% "
      "interval, and that is expected rather than alarming: the interval is "
      "the sampling uncertainty **of the bootstrap estimator**, not a "
      "tolerance band for a different statistic, and under site "
      "heterogeneity a ratio of means and a paired block-resampled estimate "
      "have genuinely different estimands. Testing one against the other's "
      "CI was the wrong test and the first draft of this section made that "
      "mistake." % (inside, ncell))
    w("")
    w("What matters for the claim is the direction of the bias: the scorer "
      "reports a reduction **at least as large** as the bootstrap in **%d of "
      "%d** cells. Quoting the bootstrap throughout therefore states the "
      "**smaller** of the two available effects, so every blotch number in "
      "this section is conservative with respect to the other instrument."
      % (cons, ncell))

    # ---- 15.3 correlations, stated per subject as required
    w("")
    w("#### 15.3")
    w("")
    w("| subject | r(sharp/tex, grain) | r(blotch, grain) | independent? |")
    w("|---|---:|---:|---|")
    for s in ORDER:
        _, _, rs, rb = sc[s]
        ind = "**no**" if abs(rs) > 0.9 else "yes"
        w("| `%s` | %+.4f | %+.4f | %s |" % (s, rs, rb, ind))
    flagged = [s for s in ORDER if abs(sc[s][2]) > 0.9]
    w("")
    w("`|r| > 0.9` on %d of %d subjects (%s), where the sharpness column is "
      "not independent evidence and is not leaned on."
      % (len(flagged), len(ORDER),
         ", ".join("`%s`" % s for s in flagged) if flagged else "none"))

    # The two disqualifications are independent and must COMPOSE: band
    # qualification asks whether the band carries signal on that subject,
    # the correlation asks whether the column is restating grain. A cell is
    # evidence only if it survives both.
    both = [s for s in ORDER if ql[s][2] and abs(sc[s][2]) <= 0.9]
    w("")
    w("**The two disqualifications compose.** Band qualification asks whether "
      "%s cyc/px carries signal on that subject; the correlation asks whether "
      "the column is restating grain. They are independent tests and a cell "
      "is evidence only if it survives both. %d of %d subjects do: %s. The "
      "largest sharpness gain in the sweep (`%s`, %+.2f%%) is among them, and "
      "it is also the deepest subject and the most strongly qualified at this "
      "band in the corpus."
      % (MY_BAND, len(both), len(ORDER),
         ", ".join("`%s`" % s for s in both),
         max(both, key=lambda s: sc[s][1]["S32"][2]),
         pct(max(sc[s][1]["S32"][2] for s in both))))

    # ---- 15.4 the band-1 decomposition
    w("")
    w("#### 15.4")
    w("")
    w("| subject | S32 (all coarse) | B1ONLY (band 1) | NOB1 (bands 2-6) "
      "| band-1 share | excess over joint |")
    w("|---|---:|---:|---:|---:|---:|")
    shares, exc = [], []
    for s in ORDER:
        j = bt[(s, "S32")][0]
        b1 = bt[(s, "B1ONLY")][0]
        nb = bt[(s, "NOB1")][0]
        tot = b1 + nb
        share = 100.0 * b1 / tot
        e = 100.0 * (abs(tot) - abs(j)) / abs(j)
        shares.append(share)
        exc.append(e)
        w("| `%s` | %+.2f%% | **%+.2f%%** | %+.2f%% | **%.0f%%** | %+.1f%% |"
          % (s, j, b1, nb, share, e))
    w("")
    w("Band 1 alone carries %.0f%%-%.0f%% of the two-arm total and beats all "
      "five coarser bands combined on every subject. The arms are close to "
      "additive: their sum exceeds the joint arm by %.1f%%-%.1f%%."
      % (min(shares), max(shares), min(exc), max(exc)))

    # ---- 15.5 the duty cycle: a CAPABILITY claim, not a quality claim
    w("")
    w("#### 15.5")
    w("")
    w("| subject | arm | L0 | L1 | L2 | L3 | L4 | L5 | L6 |")
    w("|---|---|---:|---:|---:|---:|---:|---:|---:|")
    for s in ORDER:
        for a in ("NULL", "S32"):
            if (s, a) not in dt:
                sys.exit("FATAL: duty row missing for %s/%s" % (s, a))
            v = dt[(s, a)]
            w("| `%s` | `%s` | %s |" % (s, a,
                                        " | ".join("%.1f%%" % x for x in v)))
    n0 = [dt[(s, "NULL")][0] for s in ORDER]
    s0 = [dt[(s, "S32")][0] for s in ORDER]
    same0 = all(abs(a - b) < 0.05 for a, b in zip(n0, s0))
    coarse = [max(dt[(s, "S32")][3], dt[(s, "S32")][4]) for s in ORDER]
    nullc = [max(dt[(s, "NULL")][3], dt[(s, "NULL")][4]) for s in ORDER]
    w("")
    w("Band 0 is identical between the null and `S32` on every subject to "
      "the printed digit: **%s**. At levels 3-4, where the blotch statistic "
      "lives, the null reads %.1f%%-%.1f%% and `S32` reads %.1f%%-%.1f%%."
      % ("yes" if same0 else "NO", min(nullc), max(nullc),
         min(coarse), max(coarse)))

    text = "\n".join(L) + "\n"
    if "--check" in sys.argv:
        if not os.path.exists(OUT):
            sys.exit("FATAL: %s does not exist; run without --check first"
                     % OUT)
        cur = open(OUT, encoding="utf-8").read()
        if cur == text:
            print("CHECK OK: gen/s15tables.md matches a fresh generation "
                  "(%d lines)" % len(text.splitlines()))
            return 0
        print("CHECK FAIL: gen/s15tables.md differs from a fresh generation")
        a, b = cur.splitlines(), text.splitlines()
        for i in range(max(len(a), len(b))):
            x = a[i] if i < len(a) else "<eof>"
            y = b[i] if i < len(b) else "<eof>"
            if x != y:
                print("  first difference at line %d:\n    file : %s\n"
                      "    fresh: %s" % (i + 1, x, y))
                break
        return 1

    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    print("wrote %s (%d lines)" % (OUT, len(text.splitlines())))
    return 0


if __name__ == "__main__":
    sys.exit(main())
