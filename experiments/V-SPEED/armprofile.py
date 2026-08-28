"""Print the radial luma profile of several arms of one subject side by side,
ALL SEGMENTED WITH THE SAME (baseline) SUBJECT MASK.

WHY THIS FILE EXISTS
--------------------
decompose.py produced a result that refutes its own model: on
dry-erase-marker-head-cpl the *fix* arm (--pyramid-bands 5, 61.0 DN) scored
BELOW the *no-selection floor* arm (plain mean, 584.5 DN).  If the floor were
a floor that is impossible, so one of three things is true:

  1. the fix really does beat de-selection, and "floor" is the wrong name for
     the plain-mean arm (it bounds selection knobs, not band-geometry knobs);
  2. abscore.py's fixed-window prominence is wrong for one of the arms;
  3. the two arms are not being measured on the same pixels.

(3) is excluded by construction here: every arm is measured with the mask
segmented from the BASELINE render, which is also what abscore.py does.
Running aura.py standalone over a sweep directory does NOT do this -- it
re-segments each arm, and a blurrier arm with a lifted black level segments
differently, so its numbers are not comparable across arms.  That is a real
trap; it is the first thing I did and it produced a spurious disagreement.

This file does not compute a verdict.  It prints the numbers the verdict is
made of, because on this task reasoning about profile shapes has been wrong
every time it was checked and printing them has been right every time.
"""
import argparse
import pathlib
import sys

import numpy as np
import tifffile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from aura import SUB, deficit, luma, radial, segment, surplus, width_px  # noqa: E402

# A difference profile whose full width at half prominence is below this is a
# LOCAL change; above it, a broad one.  The value is not tuned to make a
# subject pass: it is set from the annulus geometry.  Adjacent band midpoints
# near the subject are 5,8,10,14,18,23,29,36,45,56 px, so a feature confined
# to two or three neighbouring bands has a FWHM under ~40 px, and one spanning
# the whole measured field has a FWHM of hundreds.  The measured separation on
# real subjects is 6x, far wider than the gate's placement.
LOCAL_PX = 80.0


def delta_shape(mids, dv):
    """Peak of a difference profile, and whether it is local or broad.

    WHY THIS EXISTS.  abscore.py scores each arm with a prominence at a fixed
    band.  That statistic cannot tell "the ring got smaller" from "the whole
    background got tilted the other way", because both reduce a prominence.
    The distinction is not academic: --pyramid-bands 5 moves the pyramid's
    base band from 1/128 to 1/32 of full scale, so it necessarily re-renders
    the background's LOW frequencies, and a broad tilt is exactly what it
    should be expected to produce as a side effect.

    Measured on dry-erase-marker-head-cpl, bands5 scored -91.2% by the fixed
    prominence -- the best halo number in the corpus -- and the difference
    profile is a smooth monotone decay from -1222 DN at 71 px to -82 DN at
    380 px.  Nothing was removed from a ring there; the background was tilted
    until an existing 695 DN decline stopped being a local maximum.

    So the arm's difference profile is measured the same way the image's own
    profile is: extremum, prominence, full width at half prominence.
    """
    dv = np.asarray(dv, float)
    mids = np.asarray(mids, float)
    dn_lo, i_lo = deficit(dv)
    dn_hi, i_hi = surplus(dv)
    if dn_hi >= dn_lo:
        p, i, sign, direction = dn_hi, i_hi, +1, "brighter"
    else:
        p, i, sign, direction = dn_lo, i_lo, -1, "darker"
    w = width_px(dv, mids, i, p, sign=sign)
    return {"dn": round(float(p), 1), "at_px": float(mids[i]),
            "w_px": round(float(w), 1), "dir": direction,
            "shape": "local" if 0 < w <= LOCAL_PX else "broad",
            "far_dn": round(float(np.median(dv[mids >= 250.0])), 1)
            if np.any(mids >= 250.0) else None}


def selftest():
    """Two plants: a ring removal and a background tilt.

    The load-bearing assertion is not that either width hits a number, it is
    that they SEPARATE -- because the claim this statistic makes is always a
    contrast between two arms, never an absolute width.
    """
    mids = np.array([5, 8, 10, 14, 18, 23, 29, 36, 45, 56, 71, 90, 110, 135,
                     168, 208, 255, 310, 380], float)
    base = 40000.0 + 30.0 * mids           # a rising background
    ok = True

    # plant 1: remove a narrow ring centred at 36 px, +-1 band.
    ring = np.zeros_like(mids)
    ring[[6, 7, 8]] = [-400.0, -1000.0, -350.0]
    r1 = delta_shape(mids, ring)
    hit = r1["shape"] == "local"
    ok &= hit
    print(f"  plant 1  narrow ring removal   w={r1['w_px']:7.1f} px  "
          f"{r1['shape']:5}  {'PASS' if hit else 'FAIL'}")

    # plant 2: a broad tilt of the same peak amplitude, spread across the
    # whole field.  Same DN at its extremum as plant 1, so amplitude cannot
    # tell them apart and only width can.
    #
    # An earlier version of this plant multiplied the inner bands by 0.3,
    # which put a cliff at 36 px and made a "broad" feature measure 66.8 px
    # FWHM -- inside the local gate.  The selftest failed and it was right
    # to: the plant had a sharp inner edge, so it was not the thing it
    # claimed to be.  The shape used now is the one actually observed on
    # dry-erase-marker-head-cpl, a smooth decay with no interior edge.
    tilt = -1000.0 * np.exp(-(((mids - 71.0) / 120.0) ** 2))
    r2 = delta_shape(mids, tilt)
    hit = r2["shape"] == "broad"
    ok &= hit
    print(f"  plant 2  broad background tilt w={r2['w_px']:7.1f} px  "
          f"{r2['shape']:5}  {'PASS' if hit else 'FAIL'}")

    # plant 2b: a purely monotone tilt has no interior extremum at all and
    # must not be scored as a feature of any width.
    r2b = delta_shape(mids, -1000.0 * mids / mids.max())
    hit = r2b["shape"] == "broad"
    ok &= hit
    print(f"  plant 2b monotone tilt         w={r2b['w_px']:7.1f} px  "
          f"{r2b['shape']:5}  {'PASS' if hit else 'FAIL'}")

    sep = r2["w_px"] / r1["w_px"] if r1["w_px"] > 0 else 0.0
    hit = sep >= 2.0
    ok &= hit
    print(f"  plant 3  the two SEPARATE      ratio={sep:5.1f}x        "
          f"{'PASS' if hit else 'FAIL'}")

    # plant 4: a flat offset is not a feature at all and must not be scored
    # as one.  This is the null.
    r4 = delta_shape(mids, np.full_like(mids, -500.0))
    hit = r4["dn"] <= 1.0
    ok &= hit
    print(f"  plant 4  flat offset (null)    dn={r4['dn']:8.1f} DN     "
          f"{'PASS' if hit else 'FAIL'}")

    print(f"\nselftest: {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("dir", nargs="?")
    ap.add_argument("--base", default="baseline")
    ap.add_argument("--arms", default="plainmean,bands5")
    ap.add_argument("--max-px", type=int, default=400)
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()

    if a.selftest:
        return selftest()
    if not a.dir:
        ap.error("dir is required unless --selftest")
    d = pathlib.Path(a.dir)
    arms = [a.base] + [x for x in a.arms.split(",") if x]

    yb = luma(tifffile.imread(str(d / (a.base + ".tiff"))))
    sub = segment(yb[::SUB, ::SUB])
    print(f"subject dir : {d}")
    print(f"mask        : segmented from '{a.base}', reused for every arm")
    print(f"mask px     : {int(sub.sum())} of {sub.size} at 1/{SUB} scale")

    prof = {}
    for tag in arms:
        p = d / (tag + ".tiff")
        if not p.exists():
            print(f"  MISSING {p}")
            continue
        y = yb if tag == a.base else luma(tifffile.imread(str(p)))
        # radial() takes an ALREADY-SUBSAMPLED array; `scale` is the px
        # conversion factor, not an instruction to resample.  Passing the
        # full-res array silently shape-mismatches against the mask.
        mids, meds, _ = radial(y[::SUB, ::SUB], sub, scale=SUB)
        prof[tag] = (np.asarray(mids), np.asarray(meds))
        if tag != a.base:
            del y

    if a.base not in prof:
        print("no baseline profile")
        return 1

    mids = prof[a.base][0]
    keep = mids <= a.max_px

    w = 12
    print()
    print("radial median luma (DN), same mask, same annuli")
    print("  d px  " + "".join(f"{t:>{w}}" for t in arms)
          + "".join(f"{('d ' + t):>{w}}" for t in arms[1:]))
    print("  " + "-" * (6 + w * (2 * len(arms) - 1)))
    for i in np.nonzero(keep)[0]:
        row = f"  {mids[i]:5.0f} "
        for t in arms:
            row += f"{prof[t][1][i]:{w}.1f}" if t in prof else " " * w
        for t in arms[1:]:
            if t in prof:
                row += f"{prof[t][1][i] - prof[a.base][1][i]:+{w}.1f}"
        print(row)

    print()
    print("SHAPE OF EACH ARM'S DIFFERENCE FROM BASELINE")
    print("  local  = confined to a few annuli -> a ring really was changed")
    print("  broad  = spread across the field  -> the background was tilted,")
    print("           which lowers a prominence without removing anything")
    print(f"  gate: FWHM <= {LOCAL_PX:.0f} px is local.  See delta_shape().")
    print()
    print("  %-12s %10s %8s %9s %9s %8s" % ("arm", "peak DN", "at px",
                                            "FWHM px", "shape", "far DN"))
    print("  " + "-" * 62)
    for t in arms[1:]:
        if t not in prof:
            continue
        s = delta_shape(mids, prof[t][1] - prof[a.base][1])
        print("  %-12s %10.1f %8.0f %9.1f %9s %8s"
              % (t, s["dn"] * (1 if s["dir"] == "brighter" else -1),
                 s["at_px"], s["w_px"], s["shape"], s["far_dn"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
