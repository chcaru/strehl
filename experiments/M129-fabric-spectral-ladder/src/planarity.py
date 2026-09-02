"""Capture cadence, focus-peak width, and subject tilt: the three things that decide
how large an ROI may be.

Nothing here reads a cutoff frequency. It is subject and capture characterisation,
permitted before commissioning lands (PREREGISTRATION.md Amendment 1).

Three questions:

Q1. DID THE CAPTURE STEP IN DEPTH-OF-FIELD UNITS?
    The five stacks hold 210/150/109/83/71 frames over what is stated to be the same
    subject and framing. If the bracketing software sized its step from the
    depth of field then step ~ N and frame count ~ 1/N. That matters far beyond
    bookkeeping: it would mean ONE FRAME IS THE SAME AMOUNT OF DEFOCUS AT EVERY
    APERTURE, so a planarity budget quoted in frames needs no per-aperture
    correction, and the depth-of-field threat T1 is equalised across the ladder by
    construction rather than by argument. If instead the step were constant in
    microns, one frame at f/5.6 would be a far larger fraction of the depth of field
    than at f/18, and T1 would bite hardest exactly where the hypotheses separate
    least.

Q2. HOW WIDE IS THE FOCUS PEAK, IN FRAMES?
    A planarity spread of k frames only matters relative to the width of the focus
    response. Measured as the full width at half maximum of the focus score above its
    own baseline.

Q3. HOW STEEP IS THE SUBJECT TILT?
    From the best-focus index map, in focus steps per mm, which combined with Q2
    fixes the largest defensible ROI.
"""

import glob
import json
import os
import sys

import numpy as np

M5 = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))), "m5-diffraction")
sys.path.insert(0, M5)
import m5_lib as L  # noqa: E402

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(HERE, "out")

# Exact third-stop f-numbers, since the EXIF marking is rounded. 2^(k/2) per stop.
EXACT_N = {"f5.6": 2 ** 2.5, "f8": 8.0, "f11": 2 ** 3.5,
           "f14": 2 ** (23 / 6), "f18": 2 ** (25 / 6)}
COUNTS = {"f5.6": 210, "f8": 150, "f11": 109, "f14": 83, "f18": 71}


def q1_cadence(res):
    print("Q1. capture cadence: does frame count scale as 1/N?\n")
    tags = list(COUNTS)
    x = np.array([1.0 / EXACT_N[t] for t in tags])
    y = np.array([float(COUNTS[t]) for t in tags])

    # Model A: n = a/N + b   (step proportional to N, i.e. stepped in DOF units)
    A = np.vstack([x, np.ones_like(x)]).T
    (a, b), *_ = np.linalg.lstsq(A, y, rcond=None)
    predA = A @ np.array([a, b])
    rmsA = float(np.sqrt(np.mean((y - predA) ** 2)))

    # Model B: n = c (constant step in microns over a common depth range would give
    # a CONSTANT count, since the range and step would both be aperture-independent)
    predB = np.full_like(y, y.mean())
    rmsB = float(np.sqrt(np.mean((y - predB) ** 2)))

    print(f"  model A  n = {a:.1f}/N + {b:.2f}   rms residual {rmsA:.2f} frames")
    print(f"  model B  n = {y.mean():.1f} (constant)   rms residual {rmsB:.2f} frames")
    print(f"  A is better by a factor of {rmsB / rmsA:.1f} in rms\n")
    print("   aperture   exact N   frames   model A   residual")
    for t, xi, yi, pi in zip(tags, x, y, predA):
        print(f"   {t:>8}   {EXACT_N[t]:7.3f}   {int(yi):6d}   {pi:7.1f}   "
              f"{yi - pi:+7.1f}")
    ok = rmsA < 0.1 * rmsB
    print(f"\n  VERDICT: {'stepped in DOF units' if ok else 'NOT DOF-stepped'}"
          f" -- one frame is {'the same' if ok else 'NOT the same'} defocus at "
          f"every aperture.")
    print(f"  The intercept {b:+.1f} frames is the bracket's lead-in/lead-out "
          f"overhead.\n")
    res["q1"] = {"a": a, "b": b, "rms_model_a": rmsA, "rms_model_b": rmsB,
                 "dof_stepped": bool(ok),
                 "exact_N": EXACT_N, "counts": COUNTS}
    return res


def fwhm_frames(idx, val):
    """FWHM in frames of a peak, measured above its own baseline."""
    val = np.asarray(val, float)
    idx = np.asarray(idx, float)
    base = np.median(val)
    peak = val.max()
    if peak <= base:
        return None
    half = base + 0.5 * (peak - base)
    j = int(np.argmax(val))
    lo = j
    while lo > 0 and val[lo] > half:
        lo -= 1
    hi = j
    while hi < len(val) - 1 and val[hi] > half:
        hi += 1
    # linear interpolation on each flank
    def cross(i0, i1):
        if val[i1] == val[i0]:
            return idx[i0]
        t = (half - val[i0]) / (val[i1] - val[i0])
        return idx[i0] + t * (idx[i1] - idx[i0])
    xl = cross(lo, lo + 1) if lo < j else idx[j]
    xr = cross(hi, hi - 1) if hi > j else idx[j]
    return float(xr - xl)


def q2_peak_width(res):
    print("Q2. focus peak width, in frames\n")
    got = {}
    for path in sorted(glob.glob(os.path.join(OUT, "focus-f*.json"))):
        with open(path, encoding="utf-8") as fh:
            d = json.load(fh)
        recs = d["records"]
        idx = [r["index"] for r in recs]
        for band in d["bands"]:
            w = fwhm_frames(idx, [r["bands"][band] for r in recs])
            got.setdefault(d["aperture"], {})[band] = w
        a = d["aperture"]
        print(f"  {a:>6}  " + "  ".join(
            f"{b} {got[a][b]:.1f}" if got[a][b] else f"{b} n/a"
            for b in d["bands"]))
    if not got:
        print("  (no focus-*.json surveys yet)")
    else:
        print("\n  A spread of k frames across an ROI is negligible when k is small")
        print("  compared with this width, because every part of the ROI is then")
        print("  still near the top of its own focus response.")
    print()
    res["q2"] = got
    return res


def q3_tilt(res):
    print("Q3. subject tilt, from the best-focus index map\n")
    got = {}
    for path in sorted(glob.glob(os.path.join(OUT, "focusmap-f*.json"))):
        with open(path, encoding="utf-8") as fh:
            d = json.load(fh)
        best = np.array(d["best"], float)
        con = np.array(d["contrast"], float)
        m = con > 10.0
        rcs = np.array(d["rcs"], float) * L.PITCH_UM / 1000.0   # mm
        ccs = np.array(d["ccs"], float) * L.PITCH_UM / 1000.0
        RR, CC = np.meshgrid(rcs, ccs, indexing="ij")
        A = np.vstack([RR[m], CC[m], np.ones(m.sum())]).T
        coef, *_ = np.linalg.lstsq(A, best[m], rcond=None)
        resid = best[m] - A @ coef
        gr, gc = coef[0], coef[1]
        grad = float(np.hypot(gr, gc))
        a = d["aperture"]
        got[a] = {"steps_per_mm_row": float(gr), "steps_per_mm_col": float(gc),
                  "steps_per_mm": grad,
                  "resid_rms_steps": float(np.sqrt(np.mean(resid ** 2))),
                  "range_steps": float(best[m].max() - best[m].min()),
                  "flat": d["flat"]}
        print(f"  {a:>6}  gradient {grad:6.3f} steps/mm "
              f"(row {gr:+.3f}, col {gc:+.3f})   "
              f"planar-fit residual {got[a]['resid_rms_steps']:.2f} steps   "
              f"full range {got[a]['range_steps']:.0f} steps")
    if not got:
        print("  (no focusmap-*.json yet)")
    else:
        print("\n  A plane fits the index map to within the residual quoted above.")
        print("  What is left is genuine subject relief plus estimator noise.")
        gm = np.mean([v["steps_per_mm"] for v in got.values()])
        print(f"\n  mean gradient {gm:.3f} steps/mm  ->  an ROI of side s mm spans")
        print(f"  about {gm:.3f}*s focus steps corner to corner along the slope.")
        for side_mm in (0.66, 1.31, 2.62, 5.24):
            print(f"    ROI {side_mm:5.2f} mm  (GQ {int(round(side_mm * 1000 / L.PITCH_UM / 2)):4d})"
                  f"  spans {gm * side_mm * 1.414:5.2f} steps diagonally")
    print()
    res["q3"] = got
    return res


def q4_scaling(res):
    """A free positive control, using only data already in hand.

    The subject was not touched between apertures, so its tilt and its relief are
    FIXED PHYSICAL DEPTHS in micrometres. The focus index measures depth in units of
    the bracket's step, and Q1 found the step to be proportional to N. Therefore
    every geometric quantity read off the index map -- the tilt gradient, the
    planar-fit residual, the full range -- must scale as 1/N.

    That prediction is not fitted to anything here and it can fail. If it holds it
    certifies three separate things at once:
      * the cadence model of Q1, from wholly independent data (image content rather
        than file counts);
      * that the index map measures real subject geometry rather than estimator
        noise, since noise would be constant in frames, not proportional to 1/N;
      * that the subject and camera did not move between the five stacks, since any
        re-setup would break the common physical tilt.
    """
    print("Q4. do the map's geometric quantities scale as 1/N? (free control)\n")
    t = res.get("q3", {})
    if len(t) < 3:
        print("  (need at least three apertures)\n")
        return res
    tags = [k for k in EXACT_N if k in t]
    N = np.array([EXACT_N[k] for k in tags])
    rows = []
    for name, key in (("tilt gradient (steps/mm)", "steps_per_mm"),
                      ("planar residual (steps)", "resid_rms_steps"),
                      ("full range (steps)", "range_steps")):
        y = np.array([t[k][key] for k in tags], float)
        prod = y * N
        cv_scaled = float(np.std(prod) / np.mean(prod))     # model: y ~ 1/N
        cv_const = float(np.std(y) / np.mean(y))            # model: y ~ const
        rows.append((name, key, y, prod, cv_scaled, cv_const))
        print(f"  {name}")
        print("      " + "  ".join(f"{k}={v:7.3f}" for k, v in zip(tags, y)))
        print(f"      y*N : " + "  ".join(f"{v:7.3f}" for v in prod))
        print(f"      spread of y*N  {cv_scaled * 100:5.1f}%   "
              f"spread of y alone {cv_const * 100:5.1f}%   "
              f"-> {'1/N CONFIRMED' if cv_scaled < 0.5 * cv_const else 'NOT 1/N'}")
        print()

    # The y*N column is not flat: it drifts downward with N. Rather than let the
    # word CONFIRMED cover that up, fit the exponent and quote it.
    print("  the residual drift, quantified: fit y ~ N^-gamma")
    gam = {}
    for name, key, y, prod, cv, cvc in rows:
        g, c = np.polyfit(np.log(N), np.log(y), 1)
        pred = np.exp(c) * N ** g
        rms = float(np.sqrt(np.mean((np.log(y) - np.log(pred)) ** 2)))
        gam[key] = {"gamma": float(-g), "log_rms": rms}
        print(f"    {name:<26} gamma = {-g:5.3f}   log-residual rms {rms:.4f}")
    gmean = float(np.mean([v["gamma"] for v in gam.values()]))
    print(f"    mean gamma {gmean:.3f}, against 1.000 for a step exactly "
          f"proportional to N.")
    print("    So the bracket's step grows slightly FASTER than N. One frame is a")
    print("    little more defocus at f/18 than at f/5.6, by a factor of")
    print(f"    {(EXACT_N['f18'] / EXACT_N['f5.6']) ** (gmean - 1):.2f}x over the")
    print("    full range. This is a property of the camera's bracketing, it is")
    print("    recorded rather than explained, and it does not enter the primary")
    print("    measurement: the reduction selects the best-focus frame per ROI by")
    print("    search, and never converts a frame index into micrometres.")
    print()
    res["q4_gamma"] = gam
    res["q4"] = {key: {"y": y.tolist(), "yN": prod.tolist(),
                       "cv_scaled": cv, "cv_const": cvc, "tags": tags}
                 for name, key, y, prod, cv, cvc in rows}

    print("  CONSEQUENCE FOR THREAT T1, which changes its registered direction.")
    print("  T1 was registered on the premise that depth of field grows 3.2x from")
    print("  f/5.6 to f/18, so more of an ROI is in focus at f/18. That premise")
    print("  assumed a fixed focus setting. This capture is a focus STACK stepped in")
    print("  depth-of-field units, and the reduction picks the best-focus frame PER")
    print("  ROI, so the residual defocus across an ROI is its physical relief")
    print("  divided by the depth of field -- which shrinks as 1/N, not grows.")
    print("  The sign of the registered direction is unchanged (less defocus")
    print("  penalty at f/18) but the mechanism and the magnitude are different,")
    print("  and the magnitude is now measurable rather than assumed.")
    print()
    print("  It also makes T1 SELF-DIAGNOSING. Defocus blur scales as relief/N_eff")
    print("  and diffraction blur as lambda*N_eff, so the ratio of the two goes as")
    print("  1/N^2. T1 therefore imprints a TREND of B against N, whereas a wrong")
    print("  value of B is a constant offset. The registered constancy test A3 is")
    print("  thus a T1 detector, not merely a consistency check.")
    print()
    return res


def main():
    res = {}
    q1_cadence(res)
    q2_peak_width(res)
    q3_tilt(res)
    q4_scaling(res)
    with open(os.path.join(OUT, "planarity.json"), "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=2)
    print(f"wrote {os.path.join(OUT, 'planarity.json')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
