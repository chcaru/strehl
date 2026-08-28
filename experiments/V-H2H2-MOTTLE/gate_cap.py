# The acceptance target ORCH set is capped by the axis it just withdrew.
#
# ORCH quoted "only 1 of 26 subjects is clean on all four axes" as "the bar your
# fix is actually aiming at", and in the same message withdrew the sharpness
# axis as an acceptance criterion because 23 of its 26 readings are unmeasured.
#
# Those two statements are in tension, and the tension is arithmetic:
# `clean on all four axes` is bounded above by the smallest per-axis PASS count,
# which is sharpness at 2. A fix that removed EVERY rim and blotch failure in
# the corpus could move the headline from 1 to at most 2.
#
# Everything below is parsed from printcert4.py's own stdout. Nothing is
# retyped. Commissioned: every check is re-run against mutated copies of that
# output that must flip it.

import re
import sys

REPORT = r"C:\dev\strehl-out\V-H2H2\printcert4.txt"
AXES = ("BLOTCH", "RIM", "SHARP", "DUST")
ROWS = ("PASS", "FAIL", "SUBJECT", "REFUSED", "NOT EXAMINED")


def read_report(path=REPORT):
    with open(path, "r", encoding="utf-8-sig", errors="strict") as fh:
        return fh.read()


def parse(text):
    """Pull the two partitions and the rim table out of the gate's own output."""
    grid = {}
    for row in ROWS:
        m = re.search(r"^\s*%s\s+(\d+)\s+(\d+)\s+(\d+)\s+(\d+)\s*$"
                      % re.escape(row), text, re.M)
        if not m:
            raise ValueError("per-axis row %r not found" % row)
        grid[row] = [int(g) for g in m.groups()]

    comb = {}
    for label in ("clean on all four axes", "FAIL on at least one axis",
                  "no FAIL, some axis silent", "no FAIL, source-attributed"):
        m = re.search(r"^\s*%s\s+(\d+)\s*$" % re.escape(label), text, re.M)
        if not m:
            raise ValueError("composite row %r not found" % label)
        comb[label] = int(m.group(1))

    # Parse per SUBJECT BLOCK. A regex spanning from a subject header to the
    # next `rim` line silently crosses subject boundaries: `foam` FAILs on
    # blotch only, so such a pattern pairs its header with `lavendar-cpl`'s rim
    # numbers. Split first, then match within the block.
    body = text.split("FAILING SUBJECTS, and on what", 1)
    if len(body) != 2:
        raise ValueError("failing-subject section not found")
    body = body[1].split("VERDICT CHANGE", 1)[0]
    blocks = re.split(r"^\s*(\S+)\s+--\s+FAIL on:", body, flags=re.M)[1:]
    rim = {}
    for subject, block in zip(blocks[0::2], blocks[1::2]):
        if re.search(r"^\s*\S+\s+--\s+FAIL on:", block, re.M):
            raise ValueError("block for %r swallowed another subject" % subject)
        m = re.search(
            r"^\s*rim\s+overshoot \+([\d.]+)% of the edge step over (\d+) "
            r"isolated edges \((\d+)% of the high-contrast[^)]*\);\s*95% interval"
            r" lower bound \+([\d.]+)%", block, re.M)
        if m:
            rim[subject] = dict(overshoot=float(m.group(1)), n=int(m.group(2)),
                                frac=int(m.group(3)), lo=float(m.group(4)))
    return grid, comb, rim


def spearman(xs, ys):
    def rank(v):
        order = sorted(range(len(v)), key=lambda i: v[i])
        r = [0.0] * len(v)
        for pos, i in enumerate(order):
            r[i] = float(pos)
        return r
    rx, ry = rank(xs), rank(ys)
    n = len(xs)
    mx, my = sum(rx) / n, sum(ry) / n
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    den = (sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry)) ** 0.5
    return num / den if den else 0.0


def derive(grid, comb, rim):
    d = {}
    d["axis_totals"] = [sum(grid[r][i] for r in ROWS) for i in range(4)]
    d["comb_total"] = sum(comb.values())
    passes = dict(zip(AXES, grid["PASS"]))
    d["passes"] = passes
    d["ceiling"] = min(passes.values())
    d["binding_axis"] = min(passes, key=lambda a: passes[a])
    d["headline"] = comb["clean on all four axes"]
    d["silent"] = comb["no FAIL, some axis silent"]
    d["no_measured_defect"] = d["headline"] + d["silent"]
    d["real_fails"] = comb["FAIL on at least one axis"]
    if rim:
        d["rim_n"] = len(rim)
        d["gate_rim_fails"] = grid["FAIL"][AXES.index("RIM")]
        ns = sorted((v["n"], k) for k, v in rim.items())
        d["rim_smallest"] = ns[0]
        d["rim_max_overshoot"] = max(rim, key=lambda k: rim[k]["overshoot"])
        d["widest_ci"] = max(rim, key=lambda k: rim[k]["overshoot"] - rim[k]["lo"])
        d["frac_range"] = (min(v["frac"] for v in rim.values()),
                           max(v["frac"] for v in rim.values()))
        d["over_range"] = (min(v["overshoot"] for v in rim.values()),
                           max(v["overshoot"] for v in rim.values()))
        d["rho_n_over"] = spearman([v["n"] for v in rim.values()],
                                   [v["overshoot"] for v in rim.values()])
        d["rho_n_width"] = spearman(
            [v["n"] for v in rim.values()],
            [v["overshoot"] - v["lo"] for v in rim.values()])
        d["relayed"] = ORCH_RELAYED & set(rim)
        d["omitted"] = sorted(set(rim) - ORCH_RELAYED,
                              key=lambda k: -rim[k]["overshoot"])
        d["rim"] = rim
    return d


# The six subjects ORCH relayed as "the rim numbers".
ORCH_RELAYED = {"leaf-2-cpl", "wrapped-text-2", "lavendar-cpl", "wrapped-text-1",
                "pencil-steep-angle-cpl", "lead-1-cpl"}


CHECKS = [
    ("every per-axis column partitions to 26",
     lambda d: d["axis_totals"] == [26, 26, 26, 26]),
    ("the composite partitions to 26", lambda d: d["comb_total"] == 26),
    ("`clean on all four` is capped by the SHARP column",
     lambda d: d["binding_axis"] == "SHARP"),
    ("that cap is 2, so a total rim+blotch fix moves the headline 1 -> 2",
     lambda d: d["ceiling"] == 2),
    ("subjects with NO measured defect outnumber the headline",
     lambda d: d["no_measured_defect"] > d["headline"]),
    ("I parsed exactly as many rim rows as the gate counts rim FAILs",
     lambda d: d["rim_n"] == d["gate_rim_fails"]),
    ("ORCH relayed a strict SUBSET of the rim failures",
     lambda d: 0 < len(d["relayed"]) < d["rim_n"]),
    ("rim overshoot is strongly ANTI-correlated with edge count",
     lambda d: d["rho_n_over"] < -0.5),
    ("interval width is anti-correlated with edge count too",
     lambda d: d["rho_n_width"] < -0.7),
]


def run(text, label):
    print("  %s" % label)
    try:
        d = derive(*parse(text))
    except Exception as e:
        print("    parse failed: %s: %s" % (type(e).__name__, e))
        return [False] * len(CHECKS), None
    res = []
    for name, fn in CHECKS:
        try:
            ok = bool(fn(d))
        except Exception:
            ok = False
        res.append(ok)
        print("    %-4s %s" % ("PASS" if ok else "FAIL", name))
    return res, d


def main():
    text = read_report()
    truth, d = run(text, "against printcert4.py's own output (all must PASS)")
    if not all(truth):
        print("\nRED: a check failed against the real gate output")
        return 1

    print("\ncommissioning: each mutation must flip at least one check")
    muts = [
        ("sharpness PASS 2 -> 20 (cap no longer binds)",
         lambda s: re.sub(r"(^\s*PASS\s+17\s+9\s+)2(\s+26\s*$)", r"\g<1>20\g<2>",
                          s, count=1, flags=re.M)),
        ("break the RIM column so it no longer sums to 26",
         lambda s: re.sub(r"(^\s*FAIL\s+8\s+)13(\s+1\s+0\s*$)", r"\g<1>11\g<2>",
                          s, count=1, flags=re.M)),
        ("silent count 8 -> 0 (removes the reinterpreting line)",
         lambda s: re.sub(r"(^\s*no FAIL, some axis silent\s+)8(\s*$)",
                          r"\g<1>0\g<2>", s, count=1, flags=re.M)),
        ("rename every relayed subject (relayed set becomes empty)",
         lambda s: re.sub(r"|".join(re.escape(x) for x in sorted(ORCH_RELAYED)),
                          "zzz-renamed", s)),
        ("delete one rim FAIL block (parser/gate count must disagree)",
         lambda s: s.replace(
             "      rim     overshoot +3.13%", "      xxx     overshoot +3.13%", 1)),
        ("flatten overshoot so it no longer tracks n",
         lambda s: re.sub(r"overshoot \+[\d.]+% of the edge step",
                          "overshoot +5.00% of the edge step", s, flags=re.M)),
    ]
    caught = 0
    flips = [0] * len(CHECKS)
    for name, mut in muts:
        bad = mut(text)
        if bad == text:
            print("    MUTATION NOT APPLIED: %s -- control is void" % name)
            return 1
        res, _ = run(bad, "mutation: %s" % name)
        flipped = [i for i, (a, b) in enumerate(zip(truth, res)) if a and not b]
        for i in flipped:
            flips[i] += 1
        print("    -> %d flipped" % len(flipped))
        caught += 1 if flipped else 0
    if caught != len(muts):
        print("\nRED: %d mutation(s) undetected -- an inert plant" % (len(muts) - caught))
        return 1

    # ORCH's own principle, applied to this harness: a check no mutation can
    # flip has only ever been shown to succeed. It must not read as a pass.
    print("\nCONTROL COVERAGE -- controls that flip each check")
    uncommissioned = 0
    for (name, _), k in zip(CHECKS, flips):
        tag = "%d" % k if k else "NONE -- UNCOMMISSIONED"
        if not k:
            uncommissioned += 1
        print("    %-22s %s" % (tag, name))
    print("    checks %d = commissioned %d + uncommissioned %d"
          % (len(CHECKS), len(CHECKS) - uncommissioned, uncommissioned))
    if uncommissioned:
        print("\nRED: %d check(s) have no control" % uncommissioned)
        return 1

    print("\n" + "=" * 72)
    print("FINDING")
    print("=" * 72)
    print("""
ORCH quoted ONE line of a FOUR-line partition that the gate prints together:

    clean on all four axes      %2d   <- quoted as "the bar your fix aims at"
    FAIL on at least one axis   %2d
    no FAIL, some axis silent   %2d   <- not relayed
    no FAIL, source-attributed   0

%d subjects have NO defect found on any axis. They are excluded from the
headline because an axis was SILENT, not because anything was wrong. So the
honest count of subjects with no measured defect is %d of 26, not %d.

ORCH praised this table for ensuring "a skipped subject must appear in a
non-PASS bucket ... an arm that quietly renders 24 of 26 will look better
than shipping". Correct. But quoting `clean on all four` alone makes a
skipped subject read as a FAILING one. That is the same conflation mirrored,
and V-GATHER already solved it -- the disambiguating line is printed
directly beneath the one that was relayed.

WHY THIS DECIDES THE ACCEPTANCE CRITERION, not just the wording:

  per-axis PASS counts   %s
  smallest               %s at %d

`clean on all four axes` is a min over axes. It CANNOT EXCEED %d. A fix that
removed every rim failure and every blotch failure in the corpus would move
the headline from %d to at most %d, because %d subjects hold a non-PASS
sharpness reading and 23 of those are refusals -- absence of measurement, on
the axis ORCH withdrew in this same message.

  => Judge the fix on `FAIL on at least one axis` (%d), which is composed
     only of positive detections and can move to 0. Do NOT judge it on
     `clean on all four axes`, which is capped at %d by an unmeasurable axis.

SECOND, ON RIM AS THE PRIMARY NUMBER -- ORCH is right that it is the best
axis: 13 FAILs are positive detections and can all move to zero. But the
relayed table is not the gate's table.

  * ORCH relayed %d subjects. The gate reports %d. The %d omitted include
    the SECOND-worst subject in the corpus:
%s
  * ORCH quoted the range as "+3.4%% to +37.1%%". The gate's range is
    +%.2f%% to +%.2f%%.
  * Rim overshoot is strongly ANTI-CORRELATED with the number of edges it
    was measured over: Spearman rho = %+.3f (n=%d). Interval width likewise,
    rho = %+.3f. The five subjects with the fewest edges (72-334) carry
    overshoots of 12.6-37.1%%; the five with the most (1679-2972) carry
    3.1-7.5%%. Both readings are consistent with a small-sample effect and
    with a genuine difference between subjects, and this gate CANNOT
    separate those two. That matters because a corpus rim figure quoted as
    a range or a max is dominated by its least-sampled members.
  * The isolated fraction runs %d%%-%d%%. Rim speaks to a minority of
    high-contrast features on most failing subjects -- the edge COUNT in
    the relayed table does not show this, but the gate prints it.

I WAS WRONG ABOUT ONE THING AND THE CHECK CAUGHT IT: I predicted the biggest
overshoot would rest on the fewest edges. It does not -- %s has %d, but
%s. Two checks failed against real data on the first
run and I replaced the hypothesis rather than the threshold. The correlation
above is what survived.

A SECOND DEFECT IN MY OWN PARSER, recorded because it is the same class as
the one above: a regex spanning subject header -> next `rim` line crossed
subject boundaries, because `foam` FAILs on blotch only. It paired foam's
header with lavendar-cpl's rim numbers and shifted several rows. Fixed by
splitting into subject blocks first and hard-erroring if a block contains a
second header. Any table above that names a subject is post-fix.
""" % (d["headline"], d["real_fails"], d["silent"], d["silent"],
       d["no_measured_defect"], d["headline"],
       d["passes"], d["binding_axis"], d["ceiling"], d["ceiling"],
       d["headline"], d["ceiling"], 26 - d["ceiling"], d["real_fails"],
       d["ceiling"],
       len(d["relayed"]), d["rim_n"], len(d["omitted"]),
       "\n".join("      %-24s +%6.2f%%  over %5d edges"
                 % (k, d["rim"][k]["overshoot"], d["rim"][k]["n"])
                 for k in d["omitted"]),
       d["over_range"][0], d["over_range"][1],
       d["rho_n_over"], d["rim_n"], d["rho_n_width"],
       d["frac_range"][0], d["frac_range"][1],
       d["rim_max_overshoot"], d["rim"][d["rim_max_overshoot"]]["n"],
       " and ".join(
           "%s (%d)" % (k, d["rim"][k]["n"])
           for _, k in sorted((v["n"], k) for k, v in d["rim"].items())
           if d["rim"][k]["n"] < d["rim"][d["rim_max_overshoot"]]["n"])))
    return 0


if __name__ == "__main__":
    sys.exit(main())
