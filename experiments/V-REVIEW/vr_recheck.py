"""RECHECK the V-REVIEW acquittals against a masters directory.

  python vr_recheck.py [--masters DIR] [--suffix --SHIP-V3] [--tol 0.02]
                       [--baseline vr_baseline.json] [--only subj,subj]

Re-derives each adjudicated subject's MASTER statistics with the same imported
gate functions and compares them to the frozen baseline.  Every subject in the
baseline lands in exactly one bucket:

    HELD          master statistic reproduces the adjudicated value within tol
    MOVED         it does not -- the acquittal recorded in report.md is STALE
    MISSING       the master file is not in the directory
    NOT-EXAMINED  the file is there but could not be measured (named reason)

held + moved + missing + not_examined == subjects in baseline, and the checker
asserts that identity before printing.  GREEN requires held == total AND
total > 0: an empty directory, an empty baseline or an --only filter that
matches nothing all exit RED, because a count that did not move is not a pass.

SCOPE LIMIT, printed on every run: this re-derives the MASTER half only.  The
source-frame comparison is frozen from the original adjudication.  A GREEN run
means "the masters still read what was adjudicated", NOT "the merge is still
innocent" -- if the merge changed, the source arm (vr_source.py) must be re-run.
"""
import argparse, json, os, sys, traceback
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vr_lib as V

HERE = os.path.dirname(os.path.abspath(__file__))
HELD, MOVED, MISSING, NOTEX = "HELD", "MOVED", "MISSING", "NOT-EXAMINED"


def rel(new, old):
    if old == 0:
        return float("inf") if new != 0 else 0.0
    return abs(new - old) / abs(old)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--masters", default=V.SHIP)
    ap.add_argument("--suffix", default="--" + V.ARM)
    ap.add_argument("--tol", type=float, default=0.02)
    ap.add_argument("--baseline", default=os.path.join(HERE, "vr_baseline.json"))
    ap.add_argument("--only", default="")
    a = ap.parse_args()

    with open(a.baseline) as fh:
        base = json.load(fh)
    subs = base["subjects"]
    if a.only:
        want = set(x for x in a.only.split(",") if x)
        subs = {k: v for k, v in subs.items() if k in want}

    print("vr_recheck  baseline=%s  arm=%s" % (os.path.basename(a.baseline), base["arm"]))
    print("masters dir : %s" % a.masters)
    print("tolerance   : %.4g relative on each adjudicated master statistic" % a.tol)
    print("SCOPE       : re-derives the MASTER half only; the source-frame")
    print("              comparison is FROZEN from the original adjudication.")
    print("              GREEN != 'merge still innocent'; it means 'masters still")
    print("              read what was adjudicated'. If the merge changed, re-run")
    print("              vr_source.py before trusting any verdict here.")
    print("")
    print("%-22s %-12s %10s %10s %8s  %s"
          % ("subject", "bucket", "blotch", "chroma", "worst d", "note"))

    buckets = {HELD: [], MOVED: [], MISSING: [], NOTEX: []}
    for s in sorted(subs):
        b = subs[s]
        path = os.path.join(a.masters, "%s%s.tiff" % (s, a.suffix))
        if not os.path.exists(path):
            buckets[MISSING].append(s)
            print("%-22s %-12s %10s %10s %8s  %s"
                  % (s, MISSING, "-", "-", "-", "no %s%s.tiff" % (s, a.suffix)))
            continue
        try:
            rgb = V.read_rgb(path)
            nb = V.gate_blotch(rgb)["contrast"]
            nc = V.gate_chroma(rgb)
            nc = None if nc is None else nc["chroma"]
        except Exception as e:
            buckets[NOTEX].append(s)
            print("%-22s %-12s %10s %10s %8s  %s: %s"
                  % (s, NOTEX, "-", "-", "-", type(e).__name__, str(e)[:60]))
            continue
        if nc is None:
            buckets[NOTEX].append(s)
            print("%-22s %-12s %10.5f %10s %8s  %s"
                  % (s, NOTEX, nb, "-", "-", "chroma window unusable"))
            continue

        ob, oc = b["master"]["blotch"], b["master"]["chroma"]
        db, dc = rel(nb, ob), rel(nc, oc)
        worst = max(db, dc)
        if worst <= a.tol:
            buckets[HELD].append(s)
            note = "r_blotch %.3f r_chroma %.3f vs frozen source max" % (
                nb / b["source_frame_max"]["blotch"], nc / b["source_frame_max"]["chroma"])
            print("%-22s %-12s %10.5f %10.6f %7.3f%%  %s" % (s, HELD, nb, nc, 100 * worst, note))
        else:
            buckets[MOVED].append(s)
            rb = nb / b["source_frame_max"]["blotch"]
            rc = nc / b["source_frame_max"]["chroma"]
            el = base["gate_rule"]["elevated_multiple"]
            flags = []
            if db > a.tol:
                flags.append("blotch %.5f -> %.5f (%+.2f%%)" % (ob, nb, 100 * (nb - ob) / ob))
            if dc > a.tol:
                flags.append("chroma %.6f -> %.6f (%+.2f%%)" % (oc, nc, 100 * (nc - oc) / oc))
            if rb > el or rc > el:
                flags.append("NOW EXCEEDS gate %.1fx rule (r_blotch %.3f r_chroma %.3f)"
                             % (el, rb, rc))
            print("%-22s %-12s %10.5f %10.6f %7.3f%%  %s"
                  % (s, MOVED, nb, nc, 100 * worst, "; ".join(flags)))

    total = len(subs)
    n = {k: len(v) for k, v in buckets.items()}
    assert sum(n.values()) == total, "partition does not sum: %r vs %d" % (n, total)
    print("")
    print("PARTITION  held %d  moved %d  missing %d  not-examined %d  = %d subjects in baseline"
          % (n[HELD], n[MOVED], n[MISSING], n[NOTEX], total))

    green = (total > 0 and n[HELD] == total)
    if green:
        print("GREEN  all %d adjudicated masters still read what report.md ruled on." % total)
        return 0
    why = []
    if total == 0:
        why.append("no subjects examined (empty baseline or --only matched nothing)")
    if n[MOVED]:
        why.append("MOVED: " + ", ".join(buckets[MOVED]) + " -- acquittal is STALE, re-adjudicate")
    if n[MISSING]:
        why.append("MISSING: " + ", ".join(buckets[MISSING]))
    if n[NOTEX]:
        why.append("NOT-EXAMINED: " + ", ".join(buckets[NOTEX]))
    print("RED    " + "\n       ".join(why))
    return 2


if __name__ == "__main__":
    sys.exit(main())
