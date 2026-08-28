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
import argparse, json, os, re, sys, traceback
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vr_lib as V

HERE = os.path.dirname(os.path.abspath(__file__))
HELD, MOVED, MISSING, NOTEX = "HELD", "MOVED", "MISSING", "NOT-EXAMINED"
BOUND, CONTRA, UNPARSED, NOROW = "BOUND", "CONTRADICTED", "UNPARSED", "NO-ROW"

# Row: | subject | stat | master | source (max of N) | **ratio** | VERDICT | note |
ROW_RE = re.compile(
    r"^\|\s*([A-Za-z0-9_.-]+)\s*\|\s*(blotch|chroma)\s*\|\s*([0-9.]+)\s*\|"
    r"\s*([0-9.]+)\s*\(max of (\d+)\)\s*\|\s*\*\*([0-9.]+)\*\*\s*\|"
    r"\s*([A-Z]+)\s*\|", re.M)
HEAD_RE = re.compile(r"\*\*([A-Za-z]+) ACQUIT, ([A-Za-z]+) CONVICT\.\*\*")
WORDS = {"zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
         "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
         "eleven": 11, "twelve": 12, "thirteen": 13}


def bind_report(base, path, tol=2e-3):
    """Check report.md's stated verdicts and numbers against the baseline.

    A verifier that re-derives numbers but never opens the report cannot detect
    a REVERSED CONCLUSION: flipping ACQUIT to CONVICT leaves every number intact
    and every such checker green. Measured on this very script -- 3 of 3
    conclusion flips MISSED -- which is why this exists. See vp_flipcommission.py.
    """
    out = {BOUND: [], CONTRA: [], UNPARSED: [], NOROW: []}
    notes = []
    if not os.path.exists(path):
        return out, ["report not found: %s" % path], None
    text = open(path, encoding="utf-8").read()
    subs = base["subjects"]
    elev = base["gate_rule"]["elevated_multiple"]

    seen = set()
    for m in ROW_RE.finditer(text):
        subj, stat, mv, sv, nsrc, ratio, verdict = m.groups()
        tag = "%s/%s" % (subj, stat)
        if subj not in subs:
            out[UNPARSED].append(tag)
            notes.append("%s: row for a subject absent from the baseline" % tag)
            continue
        seen.add(tag)
        b = subs[subj]
        bad = []
        for label, got, want in (
                ("master", float(mv), b["master"][stat]),
                ("source", float(sv), b["source_frame_max"][stat]),
                ("ratio", float(ratio), b["ratio"][stat])):
            if want and abs(got - want) / abs(want) > tol:
                bad.append("%s %s != measured %.6g" % (label, got, want))
        if int(nsrc) != b["n_source_frames_registered"]:
            bad.append("source frame count %s != %d" % (nsrc, b["n_source_frames_registered"]))
        if verdict != b["verdict"]:
            bad.append("VERDICT %s != adjudicated %s" % (verdict, b["verdict"]))
        implied = "ACQUIT" if float(ratio) <= elev else "CONVICT"
        if verdict != implied:
            bad.append("VERDICT %s contradicts the %.2fx rule on its own ratio %s"
                       % (verdict, elev, ratio))
        if bad:
            out[CONTRA].append(tag)
            notes.append("%s: %s" % (tag, "; ".join(bad)))
        else:
            out[BOUND].append(tag)

    for s, b in subs.items():
        for stat in ("blotch", "chroma"):
            if b["ratio"].get(stat) is None:
                continue
            tag = "%s/%s" % (s, stat)
            if tag not in seen and b.get("flagged_for") in (stat, "both"):
                out[NOROW].append(tag)
                notes.append("%s: adjudicated but no row states it in the report" % tag)

    hm = HEAD_RE.search(text)
    head = None
    if hm is None:
        notes.append("headline 'N ACQUIT, M CONVICT' not found -- cannot bind the count")
    else:
        acq = WORDS.get(hm.group(1).lower())
        con = WORDS.get(hm.group(2).lower())
        real_a = len({t.split("/")[0] for t in out[BOUND] + out[CONTRA]
                      if subs[t.split("/")[0]]["verdict"] == "ACQUIT"})
        real_c = len({t.split("/")[0] for t in out[BOUND] + out[CONTRA]
                      if subs[t.split("/")[0]]["verdict"] == "CONVICT"})
        head = (acq, con, real_a, real_c)
        if acq != real_a or con != real_c:
            notes.append("HEADLINE says %s ACQUIT / %s CONVICT; the baseline holds "
                         "%d / %d" % (hm.group(1), hm.group(2), real_a, real_c))
    return out, notes, head



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
    ap.add_argument("--report", default=os.path.join(HERE, "report.md"))
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

    rb, rnotes, head = bind_report(base, a.report)
    rtot = sum(len(v) for v in rb.values())
    print("")
    print("REPORT BINDING  %s  (verdicts and numbers checked against the baseline)"
          % os.path.basename(a.report))
    print("PARTITION  bound %d  contradicted %d  unparsed %d  no-row %d  = %d rows"
          % (len(rb[BOUND]), len(rb[CONTRA]), len(rb[UNPARSED]), len(rb[NOROW]), rtot))
    if head:
        print("HEADLINE   states %d ACQUIT / %d CONVICT; baseline holds %d / %d"
              % head)
    for ln in rnotes:
        print("   ! " + ln)

    report_ok = (rtot > 0 and not rb[CONTRA] and not rb[UNPARSED]
                 and not rb[NOROW] and not rnotes)
    green = (total > 0 and n[HELD] == total and report_ok)
    if green:
        print("GREEN  %d masters reproduce their adjudicated statistics AND %d report "
              "rows state the verdict the measurements support." % (total, len(rb[BOUND])))
        return 0
    why = []
    if rtot == 0:
        why.append("REPORT: no rows parsed -- a report that states nothing cannot be checked")
    if rb[CONTRA]:
        why.append("REPORT CONTRADICTS MEASUREMENT: " + ", ".join(rb[CONTRA]))
    if rb[UNPARSED]:
        why.append("REPORT UNPARSED ROWS: " + ", ".join(rb[UNPARSED]))
    if rb[NOROW]:
        why.append("ADJUDICATED BUT UNSTATED: " + ", ".join(rb[NOROW]))
    if rnotes and not (rb[CONTRA] or rb[UNPARSED] or rb[NOROW]):
        why.append("REPORT: " + "; ".join(rnotes))
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
