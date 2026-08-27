"""ORCH print-readiness: one verdict per master, from instruments already commissioned.

WHY THIS EXISTS AND WHY IT IS NOT BUILD-TRIAGE'S GATE

BUILD-TRIAGE shipped a print-readiness verdict and then proved by inspection
(commit d6e5a809) that it could not fail in the direction that mattered: every
term was a magnitude bounded below by zero, so a haloed merge could only ever
score at or ABOVE a clean one. Their commissioning never caught it because every
defect they planted made the image worse and they checked the number went down.

    A metric can be BLIND to a defect (reads nothing) or PERVERSE on it (reads
    better). Commissioning that plants only degradations cannot tell those apart,
    because both present as a pass.

The owner's loudest complaint about this product was halos. A gate that is
perverse on halos is worse than no gate, because it converts a defect into a
certificate. This file is the replacement, and its rule is:

    NO INSTRUMENT ENTERS THIS GATE THAT HAS NOT BEEN COMMISSIONED SEPARATELY,
    AND EVERY THRESHOLD NAMES THE MEASUREMENT THAT SET IT.

Nothing here is a new statistic. Each component was built, commissioned and
falsified on its own before it was allowed to contribute a verdict, and each
carries the section of ORCH-veiling.md that did it.

THE PARTITION IS THE DELIVERABLE

A master is PASS, FAIL or NOT EXAMINED, and the three sum to the number of
masters found. A master an instrument declined to examine is NOT a master that
read clean -- that conflation has produced a false all-clear three times in this
project. If a component cannot run on a subject, that subject is NOT EXAMINED
and it says which component abstained and why.

WHAT THIS GATE CANNOT SEE, stated up front rather than discovered later:

  - It measures the MASTER only. It cannot tell a defect the merge introduced
    from one the optics delivered. `orch_halosrc.py` is the instrument for that
    and it must be run on anything this gate flags, because section 96 showed a
    master reading 0.87 whose chosen source frame read 1.35 -- the merge
    inherited a specular rim rather than manufacturing one.
  - It has no instrument below 50 px or above 400 px of structure.
  - Sharpness is NOT included. It needs the source frames and takes minutes per
    subject; `orch_sharp1to1.py` carries it. A master can pass every check here
    and still be soft, so this gate certifies ABSENCE OF DEFECT, not quality.
  - Dust is not screened. It is a known, located, unfixed defect (BUILD-BLEND).
"""

import os
import pathlib
import sys

import numpy as np
import tifffile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from orch_chroma import banding, chroma_blotch          # noqa: E402
from orch_blotch import blotch_ratio, flattest, lum_of  # noqa: E402

SHIP = pathlib.Path(r"C:\dev\strehl-out\SHIP-V2")

# WHICH STATISTICS MAY ISSUE A VERDICT, AND WHICH MAY ONLY REPORT
#
# This distinction is the whole design, and getting it wrong is how the chroma
# scare of section 101 happened. A statistic earns an absolute threshold only if
# it was commissioned to be INVARIANT to the subject. Otherwise a threshold on it
# does not measure the merge, it measures how textured the subject is.
#
#   banding   MAY GATE. veil 101 v3 commissioned it exact (7.0 px predicted 7.0,
#             112.0 predicted 112.5) AND invariant at every slope and every
#             range -- which is precisely what killed v1 (measured gradient
#             steepness) and v2 (rejected 23 of 26 inputs).
#   clipping  MAY GATE. Physical, subject-independent, corpus runs 0.00-0.02%.
#   blotch    MAY NOT GATE. veil 98/99: corpus spans 0.00029 to 0.46019, a
#             1600x range, and the high end is subjects whose flattest window
#             still contains real structure. An absolute threshold here flags
#             foam, 112MSDCF, 113MSDCF, flat-on-ruler, coffee-bubbles,
#             flower-inner-edge and couch-fibers -- all innocent.
#   chroma    MAY NOT GATE. veil 101: the four subjects reading high are the
#             four most colourful, and orch_chromapair.py acquitted them by
#             render -- the source frames carry the same colour and the master
#             is CLEANER than its inputs.
#
# So blotch and chroma produce REVIEW, not FAIL, and REVIEW names the instrument
# that resolves it. A REVIEW is not a failure and is not a pass; it is a subject
# on which this gate has no standing to speak.
BAND_RUN_MIN = 4.0    # veil 101 v3: a band must be WIDE...
BAND_STEP_MIN = 4.0   # ...AND its step visible. 1 DN over 12 px is not banding.
CLIP_MAX = 0.001      # veil 102: measured corpus clipping is 0.00-0.02%
BLOTCH_REVIEW = 0.02  # veil 98 commissioning: a 4-sigma planted blotch reads
                      # 0.0169 against a 0.0002 null. Above this, LOOK -- do not
                      # conclude. Seven corpus subjects sit above it innocently.
CHROMA_REVIEW = 0.015  # veil 101: null exactly 0.000000; the acquitted-by-render
                       # subjects run 0.0200-0.0557


def verdict(path):
    """Return (state, detail). state is 'PASS', 'FAIL', 'REVIEW' or 'SKIP'."""
    a = tifffile.imread(str(path))
    if a.ndim != 3 or a.shape[2] < 3:
        return "SKIP", "not a 3-channel image (shape %s)" % (a.shape,)
    rgb = a[:, :, :3].astype(np.float32)

    clip = float((rgb >= 65500).mean())
    # A clipping gate that tests one end of the tone scale has tested half the
    # tone scale, and until this was added the half it skipped was the half
    # this corpus actually clips in: the whole-frame survey found 2.5-3.7% of
    # the frame crushed to black on three subjects, against a highlight norm of
    # 0.00-0.02%. No threshold is attached yet -- black crush is legitimate
    # against a deliberately black backdrop, so it has not earned one until the
    # corpus distribution says what is unusual. Reported, not gated.
    crush = float((rgb <= 35).mean())

    lum = lum_of(rgb)
    y, x = flattest(lum)
    br = blotch_ratio(lum[y:y + 900, x:x + 900])[0]

    ch = chroma_blotch(rgb)
    bd = banding(rgb)
    if ch is None or bd is None:
        return "SKIP", "orch_chroma abstained (no eligible window)"
    chroma = float(ch[0])
    run, step = float(bd[0]), float(bd[4])

    detail = "blotch %.5f  chroma %.4f  run %.1fpx step %.1fDN  clip %.3f%%  crush %.3f%%" % (
        br, chroma, run, step, clip * 100, crush * 100)

    if not np.isfinite(br):
        return "SKIP", "blotch ratio non-finite"

    fails = []
    if run >= BAND_RUN_MIN and step >= BAND_STEP_MIN:
        fails.append("banding run %.1f px step %.1f DN" % (run, step))
    if clip > CLIP_MAX:
        fails.append("clipped %.3f%% > %.1f%%" % (clip * 100, CLIP_MAX * 100))
    if fails:
        return "FAIL", detail + "   <== " + "; ".join(fails)

    review = []
    if br > BLOTCH_REVIEW:
        review.append("blotch %.4f (orch_blotch.py source arm)" % br)
    if chroma > CHROMA_REVIEW:
        review.append("chroma %.4f (orch_chromapair.py)" % chroma)
    if review:
        return "REVIEW", detail + "   <== " + "; ".join(review)
    return "PASS", detail


def main():
    if not SHIP.is_dir():
        raise SystemExit("no such directory: %s" % SHIP)
    paths = sorted(SHIP.glob("*--SHIP-V2.tiff"))
    if not paths:
        # The first run globbed "*.tif*" and swept in 52 sidecars -- each master
        # carries a ".tiff.ok" and a ".tiff.provenance.txt", so 26 masters glob to
        # 78 paths -- which the partition then honestly reported as NOT EXAMINED.
        # The partition was doing its job; the trailing wildcard was the defect.
        paths = sorted(SHIP.glob("*.tif*"))
        print("WARNING: no *--SHIP-V2.tiff masters; falling back to *.tif* and "
              "the NOT EXAMINED count will include sidecars.\n")
    if not paths:
        raise SystemExit("no masters in %s" % SHIP)
    print("ORCH print-readiness gate over %d master(s) in %s\n" % (len(paths), SHIP))
    print("thresholds: banding NOT(run>=%.0fpx AND step>=%.0fDN)  clip<=%.1f%%   "
          "| review: blotch>%.2f  chroma>%.3f"
          % (BAND_RUN_MIN, BAND_STEP_MIN, CLIP_MAX * 100, BLOTCH_REVIEW,
             CHROMA_REVIEW))
    print("-" * 116)
    n_pass = n_fail = n_skip = n_rev = 0
    failed, skipped, review = [], [], []
    for p in paths:
        try:
            state, detail = verdict(p)
        except Exception as exc:                                  # noqa: BLE001
            state, detail = "SKIP", "%s: %s" % (type(exc).__name__, exc)
        name = p.stem.replace("--SHIP-V2", "")
        print("%-6s %-34s %s" % (state, name[:34], detail))
        if state == "PASS":
            n_pass += 1
        elif state == "FAIL":
            n_fail += 1
            failed.append(name)
        elif state == "REVIEW":
            n_rev += 1
            review.append(name)
        else:
            n_skip += 1
            skipped.append(name)

    total = n_pass + n_fail + n_rev + n_skip
    print("-" * 116)
    print("partition: %d PASS, %d FAIL, %d REVIEW, %d NOT EXAMINED, %d total (found %d)"
          % (n_pass, n_fail, n_rev, n_skip, total, len(paths)))
    if total != len(paths):
        print("*** PARTITION DOES NOT SUM. The gate has lost track of its own "
              "inputs and no verdict above can be trusted. ***")
        return 2
    print("A NOT EXAMINED master is not a clean master, and a REVIEW is not a")
    print("failure -- it is a subject this gate has no standing to judge alone.")
    if failed:
        print("\nFAILED: %s" % ", ".join(failed))
        print("Run orch_halosrc.py on each before calling it a merge defect: a")
        print("master can inherit a defect the optics delivered (section 96).")
    if review:
        print("\nREVIEW: %s" % ", ".join(review))
        print("These read high on a SUBJECT-DEPENDENT statistic. Section 98 and")
        print("section 101 both began exactly here and both ended in acquittal:")
        print("the master was measured cleaner than the frames it was built from.")
        print("Resolve with the source-frame control named beside each, not by")
        print("tightening the threshold.")
    if skipped:
        print("\nNOT EXAMINED: %s" % ", ".join(skipped))
    print("\nThis gate certifies ABSENCE OF THE DEFECTS IT MEASURES. It does not")
    print("certify sharpness (orch_sharp1to1.py) and does not screen dust.")
    return 1 if n_fail else 0


if __name__ == "__main__":
    sys.exit(main())
