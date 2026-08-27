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

import json
import os
import pathlib
import sys

import numpy as np
import tifffile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from orch_chroma import banding, chroma_blotch          # noqa: E402
from orch_blotch import blotch_ratio, flattest, lum_of  # noqa: E402

SHIP = pathlib.Path(r"C:\dev\strehl-out\SHIP-V2")

# The arm to score is an ARGUMENT, not a constant. It was hard-coded to SHIP-V2
# and the first re-render made that a silent trap: the gate ran, printed a full
# 26-row table and a verdict, and every number in it described a fourteen-hour-old
# corpus rendered by a superseded binary. A gate that cannot fail to find input
# will happily certify the wrong input.
if len(sys.argv) > 1:
    SHIP = pathlib.Path(sys.argv[1])
if not SHIP.is_dir():
    sys.exit(f"no such arm directory: {SHIP}")

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
# THRESHOLD PROVENANCE. The 0.1% above was calibrated against the OLD channel-
# sample statistic, which BUILD-OUTPUT then showed was measuring the sRGB gamut
# wall. A threshold keeps no authority across a change of the statistic it
# guards, so here is the corpus distribution under the CORRECTED statistic,
# measured on SHIP-V3, 26/26 masters:
#
#   all-3-channel clip:  min 0.0000%   max 0.0691% (112MSDCF)   0 masters over
#   old channel count :  min 0.0000%   max 0.1430% (flowers-cpl)  1 master over
#
# 0.1% still sits above the corrected corpus and below the planted blow the
# commission uses, so it is retained -- but it is retained on this measurement,
# not on the older one, and it has never been tested against a master that
# genuinely deserved to fail. `commission_clip.py` is what keeps it honest.
BLOTCH_REVIEW = 0.02  # veil 98 commissioning: a 4-sigma planted blotch reads
                      # 0.0169 against a 0.0002 null. Above this, LOOK -- do not
                      # conclude. Seven corpus subjects sit above it innocently.
CHROMA_REVIEW = 0.015  # veil 101: null exactly 0.000000; the acquitted-by-render
                       # subjects run 0.0200-0.0557

# ---------------------------------------------------------------------------
# ADJUDICATED BASELINE (wired from V-REVIEW's source-frame arm)
#
# Nine subjects read REVIEW on the two subject-dependent statistics above and
# all nine were adjudicated ACQUIT by an independent lane, which registered each
# master against its own source frames and measured the SAME statistic on both.
# The finding that matters: on the acquitted subjects the master reads at or
# BELOW the worst source frame, so the statistic is reading a property the
# optics delivered rather than a defect the merge introduced.
#
# WHY AN ACQUITTAL IS PINNED TO A MEASUREMENT AND NOT TO A SUBJECT NAME.
# A gate that remembers "109MSDCF was acquitted" will pass 109MSDCF forever,
# including the render in which it finally breaks. That is a gate that has been
# switched off one subject at a time, and it would be indistinguishable from one
# that is working. So the acquittal is keyed to the VALUE that was adjudicated:
# if the statistic moves, the acquittal EXPIRES and the subject returns to
# REVIEW automatically, because nobody has looked at the new number.
#
# THE TOLERANCE, AND WHERE IT COMES FROM. The same lane measured this gate's own
# reproducibility and found it wanting: a 900 px window band-passed at 50-400 px
# holds only ~20 independent blobs, so a single-draw measurement carries +/-2-3%
# scatter that no re-run reproduces. ACQUIT_TOL is set just above that floor --
# tight enough that a real movement expires the acquittal, loose enough that the
# gate's own known scatter does not. It is NOT a claim that 5% is insignificant.
#
# The window is checked too. `flattest()` chooses where to measure, and two runs
# that pick different windows are not measuring the same thing -- comparing their
# values would be a category error, so a moved window expires the acquittal
# regardless of how close the numbers happen to land.
ACQUIT_TOL = 0.05
ACQUIT_WINDOW_TOL = 8  # px; flattest() ties can shift the window a few px
BASELINE_PATH = pathlib.Path(__file__).resolve().parents[1] / "V-REVIEW" / "vr_baseline.json"


def load_baseline():
    """Return (subjects_dict, provenance_str). Missing baseline is not fatal."""
    if not BASELINE_PATH.is_file():
        return {}, "NO BASELINE FILE at %s -- every REVIEW stands unadjudicated" % BASELINE_PATH
    try:
        with open(BASELINE_PATH, encoding="utf-8") as fh:
            doc = json.load(fh)
    except Exception as exc:                                      # noqa: BLE001
        return {}, "BASELINE UNREADABLE (%s: %s) -- every REVIEW stands" % (type(exc).__name__, exc)
    subs = doc.get("subjects") or {}
    prov = doc.get("provenance") or "(baseline carries no provenance string)"
    if isinstance(prov, dict):
        prov = "; ".join("%s=%s" % kv for kv in sorted(prov.items()))
    return subs, "%d adjudicated subject(s); %s" % (len(subs), prov)


def check_acquittal(name, meas, subs):
    """Does an adjudicated ACQUIT still apply to the numbers measured today?

    Returns (applies, note). `applies` False means the subject stays in REVIEW.
    """
    rec = subs.get(name)
    if rec is None:
        return False, "no adjudication on record"
    if str(rec.get("verdict", "")).upper() != "ACQUIT":
        return False, "on record as %s, not ACQUIT" % rec.get("verdict")
    master = rec.get("master") or {}
    drift = []
    for key in ("blotch", "chroma"):
        was, now = master.get(key), meas.get(key)
        if was is None or now is None:
            continue
        # Only the statistic that TRIPPED the review has to still agree. A
        # subject reviewed for chroma may drift in blotch below its own
        # threshold without that saying anything about the chroma adjudication.
        if now <= (BLOTCH_REVIEW if key == "blotch" else CHROMA_REVIEW):
            continue
        if was <= 0:
            drift.append("%s baseline is %.6g, cannot form a ratio" % (key, was))
            continue
        rel = abs(now - was) / was
        if rel > ACQUIT_TOL:
            drift.append("%s %.5f -> %.5f (%.1f%% > %.0f%%)"
                         % (key, was, now, rel * 100, ACQUIT_TOL * 100))
        wkey = key + "_window_yx"
        wwas, wnow = master.get(wkey), meas.get(wkey)
        if wwas and wnow and max(abs(a - b) for a, b in zip(wwas, wnow)) > ACQUIT_WINDOW_TOL:
            drift.append("%s window %s -> %s (measured somewhere else)" % (key, list(wwas), list(wnow)))
    if drift:
        return False, "ACQUITTAL EXPIRED: " + "; ".join(drift)
    ratio = rec.get("ratio") or {}
    rtxt = " ".join("%s %.3fx" % (k, v) for k, v in sorted(ratio.items())
                    if isinstance(v, (int, float)))
    return True, "%s [vs %d source frames%s]" % (
        rec.get("reason", "(no reason recorded)"),
        rec.get("n_source_frames_registered", 0),
        ("; master/best-source " + rtxt) if rtxt else "")


def verdict(path):
    """Return (state, detail, meas). state is 'PASS', 'FAIL', 'REVIEW' or 'SKIP'.

    `meas` carries the measured values an adjudication can be pinned to. It is
    empty on SKIP, because a subject nobody measured cannot be acquitted.
    """
    a = tifffile.imread(str(path))
    if a.ndim != 3 or a.shape[2] < 3:
        return "SKIP", "not a 3-channel image (shape %s)" % (a.shape,), {}
    rgb = a[:, :, :3].astype(np.float32)

    # CORRECTED after BUILD-OUTPUT. The old statistic was
    #   clip = (rgb >= 65500).mean()
    # taken over the FLATTENED three-channel array, i.e. a count of CHANNEL
    # samples. That is not a measure of blown highlights, and BUILD-OUTPUT
    # showed it by mechanism rather than by argument: `image_out::gamut_map`
    # blends an out-of-gamut triple toward the neutral of equal luminance and
    # takes the SMALLEST blend that works, which lands the offending channel on
    # EXACTLY 65535. So every out-of-gamut COLOUR pixel contributed to `clip`
    # BY CONSTRUCTION with nothing blown at all -- the gate was reading the
    # sRGB gamut wall and calling it highlight clipping.
    #
    # What it cost: the gate FAILED `dry-erase-marker-head-cpl`, the corpus's
    # ONLY master with zero blown highlights (clipALL3 = 0.0000%), and PASSED
    # sixteen subjects carrying more genuine clipping than the one it failed
    # (112MSDCF at 0.0693% against flowers-cpl's 0.0131%).
    #
    # A neutral highlight -- all three channels at the ceiling together -- is a
    # specular or a blown white, and no renderer can recover it. That is the
    # thing worth gating, so that is what is gated.
    hi = rgb >= 65500
    clip = float((hi.sum(axis=2) == 3).mean())          # ALL THREE channels
    clip_ch = float(hi.mean())                          # the old number, kept
    # A clipping gate that tests one end of the tone scale has tested half the
    # tone scale, and until this was added the half it skipped was the half
    # this corpus actually clips in: the whole-frame survey found 2.5-3.7% of
    # the frame crushed to black on three subjects, against a highlight norm of
    # 0.00-0.02%. No threshold is attached yet -- black crush is legitimate
    # against a deliberately black backdrop, so it has not earned one until the
    # corpus distribution says what is unusual. Reported, not gated.
    #
    # AND IT MUST STAY UNGATED. BUILD-OUTPUT adjudicated all three flagged
    # subjects and found them innocent, with a mechanism: the flagged pixels sit
    # at median luma 0.2406 / 0.2463 / 0.3306 across 33k-53k distinct surviving
    # levels, against `flowers-cpl`'s genuine black at luma 0.0011 across 122
    # levels. The source frames carry 93-112% of the effect -- on
    # `flower-inner-edge-cpl` the merge REDUCES it. So this statistic is
    # anti-correlated with the property its name claims: it reads high on
    # subjects whose shadows are open and well-separated, and low on the one
    # subject with a genuinely crushed black. Gating it would fail the good
    # masters and pass the bad one.
    crush = float((rgb <= 35).mean())

    lum = lum_of(rgb)
    y, x = flattest(lum)
    br = blotch_ratio(lum[y:y + 900, x:x + 900])[0]

    ch = chroma_blotch(rgb)
    bd = banding(rgb)
    if ch is None or bd is None:
        return "SKIP", "orch_chroma abstained (no eligible window)", {}
    chroma = float(ch[0])
    run, step = float(bd[0]), float(bd[4])

    meas = {"blotch": br, "chroma": chroma, "blotch_window_yx": [int(y), int(x)],
            "clip": clip, "crush": crush, "band_run": run, "band_step": step}

    detail = "blotch %.5f  chroma %.4f  run %.1fpx step %.1fDN  clip %.4f%% (gamut %.3f%%)  crush %.3f%%" % (
        br, chroma, run, step, clip * 100, clip_ch * 100, crush * 100)

    if not np.isfinite(br):
        return "SKIP", "blotch ratio non-finite", {}

    fails = []
    if run >= BAND_RUN_MIN and step >= BAND_STEP_MIN:
        fails.append("banding run %.1f px step %.1f DN" % (run, step))
    if clip > CLIP_MAX:
        fails.append("clipped %.4f%% > %.1f%% (all-3-channel, neutral blown)"
                     % (clip * 100, CLIP_MAX * 100))
    if fails:
        return "FAIL", detail + "   <== " + "; ".join(fails), meas

    review = []
    if br > BLOTCH_REVIEW:
        review.append("blotch %.4f (orch_blotch.py source arm)" % br)
    if chroma > CHROMA_REVIEW:
        review.append("chroma %.4f (orch_chromapair.py)" % chroma)
    if review:
        return "REVIEW", detail + "   <== " + "; ".join(review), meas
    return "PASS", detail, meas


def main():
    if not SHIP.is_dir():
        raise SystemExit("no such directory: %s" % SHIP)
    # The arm suffix is derived from the directory rather than frozen, so this
    # gate scores whatever arm it was pointed at instead of silently finding
    # nothing and falling through to the sidecar-sweeping wildcard below.
    arm = sys.argv[2] if len(sys.argv) > 2 else SHIP.name
    paths = sorted(SHIP.glob("*--%s.tiff" % arm))
    if not paths:
        # The first run globbed "*.tif*" and swept in 52 sidecars -- each master
        # carries a ".tiff.ok" and a ".tiff.provenance.txt", so 26 masters glob to
        # 78 paths -- which the partition then honestly reported as NOT EXAMINED.
        # The partition was doing its job; the trailing wildcard was the defect.
        paths = sorted(SHIP.glob("*.tif*"))
        print("WARNING: no *--%s.tiff masters; falling back to *.tif* and "
              "the NOT EXAMINED count will include sidecars.\n" % arm)
    if not paths:
        raise SystemExit("no masters in %s" % SHIP)
    print("ORCH print-readiness gate over %d master(s) in %s\n" % (len(paths), SHIP))
    subs, prov = load_baseline()
    print("thresholds: banding NOT(run>=%.0fpx AND step>=%.0fDN)  clip<=%.1f%%   "
          "| review: blotch>%.2f  chroma>%.3f"
          % (BAND_RUN_MIN, BAND_STEP_MIN, CLIP_MAX * 100, BLOTCH_REVIEW,
             CHROMA_REVIEW))
    print("adjudications: %s" % prov)
    print("-" * 116)
    n_pass = n_fail = n_skip = n_rev = n_acq = n_exp = 0
    failed, skipped, review, acquitted, expired = [], [], [], [], []
    for p in paths:
        try:
            state, detail, meas = verdict(p)
        except Exception as exc:                                  # noqa: BLE001
            state, detail, meas = "SKIP", "%s: %s" % (type(exc).__name__, exc), {}
        # The subject key must match the adjudication file, which records BARE
        # subject names. The first wiring stripped only "--SHIP-V2" and every
        # lookup missed -- and the gate printed "no adjudication on record" nine
        # times rather than passing them, which is the direction a lookup miss
        # must fail in. Derive it from the arm instead of hard-coding a version.
        name = p.stem
        for suffix in ("--%s" % arm, "--SHIP-V4", "--SHIP-V3", "--SHIP-V2"):
            if name.endswith(suffix):
                name = name[: -len(suffix)]
                break
        note = ""
        if state == "REVIEW":
            applies, note = check_acquittal(name, meas, subs)
            if applies:
                state = "ACQUIT"
            elif note.startswith("ACQUITTAL EXPIRED"):
                state = "EXPIRED"
        print("%-7s %-34s %s" % (state, name[:34], detail))
        if note and state in ("ACQUIT", "EXPIRED", "REVIEW"):
            print("%-7s %-34s   %s" % ("", "", note))
        if state == "PASS":
            n_pass += 1
        elif state == "FAIL":
            n_fail += 1
            failed.append(name)
        elif state == "ACQUIT":
            n_acq += 1
            acquitted.append(name)
        elif state == "EXPIRED":
            n_exp += 1
            expired.append(name)
        elif state == "REVIEW":
            n_rev += 1
            review.append(name)
        else:
            n_skip += 1
            skipped.append(name)

    total = n_pass + n_fail + n_rev + n_acq + n_exp + n_skip
    print("-" * 116)
    print("partition: %d PASS, %d FAIL, %d ACQUITTED, %d ACQUITTAL EXPIRED, "
          "%d REVIEW, %d NOT EXAMINED, %d total (found %d)"
          % (n_pass, n_fail, n_acq, n_exp, n_rev, n_skip, total, len(paths)))
    if total != len(paths):
        print("*** PARTITION DOES NOT SUM. The gate has lost track of its own "
              "inputs and no verdict above can be trusted. ***")
        return 2
    print("A NOT EXAMINED master is not a clean master, and a REVIEW is not a")
    print("failure -- it is a subject this gate has no standing to judge alone.")
    print("An ACQUITTED master read high on a subject-dependent statistic and was")
    print("then measured against its OWN source frames and found no worse. That")
    print("acquittal is pinned to the number that was adjudicated: if the render")
    print("moves more than %.0f%%, it EXPIRES and the subject returns to REVIEW."
          % (ACQUIT_TOL * 100))
    if failed:
        print("\nFAILED: %s" % ", ".join(failed))
        print("Run orch_halosrc.py on each before calling it a merge defect: a")
        print("master can inherit a defect the optics delivered (section 96).")
    if expired:
        print("\nACQUITTAL EXPIRED: %s" % ", ".join(expired))
        print("These carry an ACQUIT on record, but the statistic has moved since")
        print("it was adjudicated. THIS IS NOT A PASS. Nobody has looked at the")
        print("new number. Re-run the source-frame arm and re-adjudicate, or find")
        print("out what changed in the render -- do not widen ACQUIT_TOL to make")
        print("it go away, which converts the gate into a record of past opinions.")
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
