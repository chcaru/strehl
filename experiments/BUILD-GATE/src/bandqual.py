"""Qualify section 15's sharpness band on section 15's own subjects.

ORCH's rule, issued after it broadcast a difference measured in an
unqualified band twice: no sharpness, softening or acuity claim may be
quoted without naming the band and the subject's qualification AT THAT
BAND. The signal/noise boundary is a property of the subject and moves
0.17-0.48 cyc/px across this corpus, so a band that is signal on one
subject is noise on another.

Section 15's sharpness column is `fine_on`, band **0.20-0.25 cyc/px** at
textured sites (scale_score.py). That is a DIFFERENT and COARSER band than
the 0.30-0.35 slice ORCH withdrew its own numbers from, and coarser means
more signal -- but that is an argument, and this file exists because this
lane does not settle band questions by argument.

Qualification is READ, not recomputed: it comes from V-LINEAR's committed
`bandsweep-far20*.json`, the same records `depthqual.py` (dc8c16b5) reads,
so BUILD-GATE and V-LINEAR cannot drift into two different verdicts for the
same subject. This lane only selects the band. V-LINEAR's files are read
strictly read-only.

Absence is a verdict here, not an error: a subject with no record has never
been qualified at any band, and that is exactly the status ORCH's rule
requires be disclosed rather than passed over.

Run:  python bandqual.py            writes gen/s15qual.txt
"""
import glob
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
GEN = os.path.abspath(os.path.join(HERE, "..", "gen"))
VLINEAR = os.path.abspath(os.path.join(HERE, "..", "..", "V-LINEAR"))
OUT = os.path.join(GEN, "s15qual.txt")

# The band section 15's sharpness column actually measures.
MY_BAND = "0.20-0.25"
# The slice ORCH's withdrawn -44.6% / 27.2% sit in, carried for contrast.
ORCH_BAND = "0.30-0.40"
ORCH_FINE = "0.30-0.35"

# Same exclusions depthqual.py applies, so the two agree by construction.
SKIP = ("simdecim", "bandsweep-far20-leaf-2-cpl")

ORDER = ["bee-1-cpl", "flower-bud-alone-cpl", "119MSDCF", "109MSDCF",
         "coffee-bubbles"]


def load():
    recs, src = {}, {}
    pat = os.path.join(VLINEAR, "bandsweep-far20*.json")
    files = sorted(glob.glob(pat))
    if not files:
        sys.exit("FATAL: no V-LINEAR bandsweep records at %s" % pat)
    for p in files:
        if any(s in os.path.basename(p) for s in SKIP):
            continue
        for r in json.load(open(p, encoding="utf-8")):
            if r["key"] not in recs:
                recs[r["key"]] = r
                src[r["key"]] = os.path.basename(p)
    return recs, src, len(files)


def cell(rec, band):
    if rec is None or band not in rec["bands"]:
        return None
    v = rec["bands"][band]
    return float(v["R"]), str(v["verdict"])


def main():
    recs, src, nfiles = load()
    lines = []
    w = lines.append

    w("Section 15 sharpness-band qualification.")
    w("")
    w("Band measured by section 15's sharp/tex column: %s cyc/px." % MY_BAND)
    w("Band ORCH's withdrawn numbers sit in: %s (fine slice %s)."
      % (ORCH_BAND, ORCH_FINE))
    w("Source: V-LINEAR's committed bandsweep-far20*.json (%d files), the "
      "same records depthqual.py reads at dc8c16b5. Verdicts are READ from "
      "those records, not recomputed here." % nfiles)
    w("")
    hdr = ("%-24s %5s %10s %12s %10s %12s" %
           ("subject", "N", "R@" + MY_BAND, "verdict",
            "R@" + ORCH_BAND, "verdict"))
    w(hdr)
    w("-" * len(hdr))

    npass = nmarg = nabsent = 0
    for s in ORDER:
        rec = recs.get(s)
        mine = cell(rec, MY_BAND)
        theirs = cell(rec, ORCH_BAND)
        if rec is None:
            nabsent += 1
            w("%-24s %5s %10s %12s %10s %12s"
              % (s, "?", "--", "NO RECORD", "--", "--"))
            continue
        if mine is None:
            sys.exit("FATAL: %s has a record but no %s band" % (s, MY_BAND))
        r, v = mine
        if v == "PASS":
            npass += 1
        elif v.startswith("MARGINAL"):
            nmarg += 1
        tr, tv = theirs if theirs else (float("nan"), "--")
        w("%-24s %5d %10.3f %12s %10.3f %12s"
          % (s, rec["n_real"], r, v, tr, tv))

    w("")
    w("PASS at %s: %d of %d subjects.  MARGINAL: %d.  no record at any "
      "band: %d." % (MY_BAND, npass, len(ORDER), nmarg, nabsent))
    w("")
    w("LICENSED for a sharpness claim (PASS at the measured band): %s"
      % ", ".join(s for s in ORDER
                  if recs.get(s) and
                  recs[s]["bands"][MY_BAND]["verdict"] == "PASS"))
    w("NOT LICENSED: %s"
      % ", ".join(s for s in ORDER
                  if not recs.get(s) or
                  recs[s]["bands"][MY_BAND]["verdict"] != "PASS"))

    # ORCH stated coffee-bubbles "has never been band-qualified at all".
    # It is in the committed records, so that is checked here rather than
    # repeated.
    w("")
    cb = recs.get("coffee-bubbles")
    if cb is None:
        w("coffee-bubbles: no record, consistent with ORCH's statement.")
    else:
        c = cell(cb, ORCH_FINE)
        if c is None:
            w("coffee-bubbles: record present but no %s slice." % ORCH_FINE)
        else:
            w("coffee-bubbles IS band-qualified, in %s: %s R=%.3f %s. ORCH's "
              "statement that it 'has never been band-qualified at all' does "
              "not hold against the committed records."
              % (src["coffee-bubbles"], ORCH_FINE, c[0], c[1]))

    text = "\n".join(lines) + "\n"
    os.makedirs(GEN, exist_ok=True)
    if "--check" in sys.argv:
        old = open(OUT, encoding="utf-8").read() if os.path.exists(OUT) else ""
        if old != text:
            print("CHECK FAIL: gen/s15qual.txt differs from a fresh read")
            sys.exit(1)
        print("CHECK OK: gen/s15qual.txt matches a fresh read (%d lines)"
              % len(lines))
        return
    open(OUT, "w", encoding="utf-8", newline="\n").write(text)
    print(text)
    print("wrote %s" % OUT)


if __name__ == "__main__":
    main()
