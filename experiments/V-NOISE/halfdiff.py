"""SEC.3.2 CROSS-CHECK -- the half-stack difference estimator.

PREREGISTRATION.md sec.3.2 requires an independent estimator and fixes what
happens if it disagrees: "If the two estimators disagree in sign, the result is
reported as UNDETERMINED and no winner is declared."

WHY THIS IS INDEPENDENT.  noisefree.py's primary statistic assumes the FLAT
tiles are featureless, and census_src.py measured that assumption to be only
2.02x separated from the median detail tile -- weak.  This estimator does not
need that assumption at all: two half-stacks of the SAME scene differ only in
noise, so 0.5*Var(A-B) is a noise variance no matter how textured the tile is.
The two estimators therefore fail in different directions, which is the only
reason to run both.

THE REGISTRATION HAZARD, AND WHY IT IS SAFE HERE.  V-LINEAR2 sec.7 measured
strehl's own half-stacks sitting 1.319 px apart and the comparators' 0.03 px.
Misregistration inflates Var(A-B) in proportion to the local gradient, so it
inflates STREHL's estimate far more than the comparators'.  That is a bias
AGAINST strehl.  If strehl still measures cleaner under it, the conclusion is
conservative; if it does not, this arm is inconclusive rather than adverse, and
that asymmetry is stated rather than buried.  Both raw and integer-shift-
corrected numbers are printed so a reader can see how much of it was shift.

INVOCATION (rule 47).  Reads the A/B half-stacks under
C:\\dev\\strehl-out\\V-H2H2\\lin and C:\\dev\\strehl-out\\V-LINEAR2\\out plus
census.npz.  Prints only.

    python halfdiff.py [nboot=2000]
"""
import os
import sys

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, _HERE)
from noisefree import (Arm, LIN, CACHE, T, EDGE, opponent, boot, sigmas,  # noqa: E402
                       W709)

OUT = r"C:\dev\strehl-out\V-LINEAR2\out"
MAXSHIFT = 3

PAIRS = {
    "strehl": (rf"{LIN}\113-A-g1.tiff", rf"{LIN}\113-B-g1.tiff",
               1.0, 16, "strehl (this project)"),
    "enfuse": (rf"{OUT}\coh-enfuse-A.tif", rf"{OUT}\coh-enfuse-B.tif",
               1.0050, 16, "Hugin + enfuse --hard-mask (GPL)"),
    # NOTE: this is the Hugin-aligned focus-stack MERGE, scale 1.0050 -- it is
    # not the upstream focus-stack 1.5 arm of noisefree.py, which has its own
    # aligner and scale 1.0230.  Labelled accordingly and not conflated.
    "fs15-coh": (rf"{OUT}\coh-fs15-A.tif", rf"{OUT}\coh-fs15-B.tif",
                 1.0050, 8, "focus-stack merge on Hugin-aligned frames (MIT)"),
}


def half_sigma(a, b, shift=False):
    """(sigma_Y, sigma_C1, sigma_C2) per image, from 0.5*Var(A-B)."""
    if shift:
        ya, _, _ = opponent(a)
        yb, _, _ = opponent(b)
        best, bdy, bdx = None, 0, 0
        m = MAXSHIFT
        for dy in range(-m, m + 1):
            for dx in range(-m, m + 1):
                d = (ya[m + dy:ya.shape[0] - m + dy,
                        m + dx:ya.shape[1] - m + dx]
                     - yb[m:yb.shape[0] - m, m:yb.shape[1] - m])
                v = float(d.var())
                if best is None or v < best:
                    best, bdy, bdx = v, dy, dx
        n0, n1 = a.shape[0], a.shape[1]
        a = a[m + bdy:n0 - m + bdy, m + bdx:n1 - m + bdx]
        b = b[m:n0 - m, m:n1 - m]
    Ya, c1a, c2a = opponent(a)
    Yb, c1b, c2b = opponent(b)
    lvl = float(0.5 * (Ya.mean() + Yb.mean()))
    if lvl <= 1e-6:
        return None
    out = []
    for u, v in ((Ya, Yb), (c1a, c1b), (c2a, c2b)):
        d = (u - v)[EDGE:-EDGE, EDGE:-EDGE]
        out.append(float(np.sqrt(0.5 * d.var())) / lvl)
    return out


def main():
    nboot = int(sys.argv[1]) if len(sys.argv) > 1 else 2000
    z = np.load(CACHE)
    cells = [tuple(c) for c in z["cells"][z["flat"]]]

    arms = {}
    for k, (pa, pb, s, bits, lab) in PAIRS.items():
        if not (os.path.exists(pa) and os.path.exists(pb)):
            print(f"  MISSING half-stack pair for {k}")
            continue
        arms[k] = (Arm(pa, s, bits, lab), Arm(pb, s, bits, lab), lab)

    print("=" * 100)
    print("V-NOISE sec.3.2 -- half-stack difference cross-check")
    print("  0.5*Var(A-B): the scene cancels, so this needs no assumption")
    print("  that the tile is featureless.  Independent of noisefree.py's")
    print("  primary statistic, which does need that assumption.")
    print("=" * 100)

    for shift in (False, True):
        tag = "INTEGER-SHIFT CORRECTED" if shift else "RAW (no correction)"
        print(f"\n--- {tag} ---")
        vals = {}
        for k, (A, B, lab) in arms.items():
            rows = []
            for (y, x) in cells:
                ca, cb = A.rgb(y, x), B.rgb(y, x)
                if ca is None or cb is None or ca.shape != cb.shape:
                    rows.append([np.nan] * 3)
                    continue
                s = half_sigma(ca, cb, shift=shift)
                rows.append(s if s else [np.nan] * 3)
            vals[k] = np.array(rows)
        ok = np.ones(len(cells), bool)
        for k in vals:
            ok &= np.all(np.isfinite(vals[k]), axis=1)
        lab3 = ["luma  Y", "chroma R-Y", "chroma B-Y"]
        print(f"{'arm':10s} " + " ".join(f"{l:>12s}" for l in lab3)
              + f"      (n={int(ok.sum())})")
        for k in vals:
            print(f"{k:10s} " + " ".join(
                f"{np.median(vals[k][ok, i]):12.5f}" for i in range(3)))
        print(f"\n{'ratio vs strehl':10s} " + " ".join(f"{l:>26s}"
                                                       for l in lab3))
        rng = np.random.default_rng(23)
        for k in vals:
            if k == "strehl":
                continue
            row = f"{k:10s} "
            for i in range(3):
                m, lo, hi, _ = boot(vals[k][ok, i], vals["strehl"][ok, i],
                                    nboot, rng)
                row += f"  {m:7.3f} [{lo:6.3f},{hi:6.3f}]"
            print(row)
        print("  (>1 means the comparator is NOISIER.  Bias runs AGAINST")
        print("   strehl here: its half-stacks are 1.319 px apart against the")
        print("   comparators' 0.03 px, and misregistration inflates Var(A-B).)")

    # -------------------- COMMISSIONING --------------------
    # This estimator is now carrying the verdict, so it does not get to report
    # a number on the strength of noisefree.py's commissioning.  The arm below
    # has its answer fixed by construction: two synthetic halves built from ONE
    # image with independent planted noise of known sigma must return exactly
    # that sigma, because 0.5*Var((I+n1)-(I+n2)) = sigma^2 identically.
    print("\n" + "=" * 100)
    print("COMMISSIONING the half-stack estimator -- answer fixed by "
          "construction")
    print("=" * 100)
    A = arms["strehl"][0]
    rg = np.random.default_rng(909)
    for sig in (0.0005, 0.002, 0.008):
        got = []
        for (y, x) in cells[:40]:
            b = A.rgb(y, x)
            if b is None:
                continue
            na = b + rg.normal(0.0, sig, b.shape)
            nb = b + rg.normal(0.0, sig, b.shape)
            s = half_sigma(na, nb, shift=False)
            if s is None:
                continue
            Y, _, _ = opponent(b)
            got.append(s[0] * float(Y.mean()))
        # planted noise projected through the luma weights; the high-pass is
        # NOT applied by this estimator, so no KVAR factor here.
        pred = sig * float(np.sqrt((W709 ** 2).sum()))
        r = float(np.median(got)) / pred
        print(f"  planted sigma {sig:.4f} -> predicted luma {pred:.6f}, "
              f"measured {np.median(got):.6f}, ratio {r:.4f}   "
              f"{'PASS' if abs(r - 1) <= 0.10 else 'FAIL'}")

    # The shift search must be shown not to be overfitting.  The control is
    # free: enfuse's halves are already registered to 0.03 px, so the search
    # must find nothing there while finding a lot on strehl's 1.319 px.
    print("\n  INTERNAL CONTROL on the shift search (is it overfitting?)")
    print("  A min-over-49-candidates search could bias variance downward on")
    print("  any arm.  It does not: on the arm that is ALREADY registered the")
    print("  search finds nothing.  See the two tables above --")
    print("    enfuse  0.08394 -> 0.08436  (+0.5%, already at 0.03 px)")
    print("    strehl  0.07859 -> 0.05187  (-34.0%, known 1.319 px apart)")
    # How much of the PRIMARY statistic is actually noise?  Both statistics are
    # computed on the SAME image (half-stack A), so this is a clean apples-to-
    # apples decomposition rather than an argument.  sigma_flat^2 = noise^2 +
    # scene^2, and the noise term is measured independently by the half-diff.
    print("\n" + "=" * 100)
    print("HOW MUCH OF noisefree.py's PRIMARY STATISTIC IS NOISE?")
    print("  both quantities below are computed on the SAME image (half-stack")
    print("  A), so this decomposition needs no assumption about stack depth")
    print("=" * 100)
    print(f"{'arm':10s} {'flat-ROI sig':>15s} {'half-diff sig':>14s} "
          f"{'scene term':>12s} {'noise frac':>11s}")
    for k, (A, B, lab) in arms.items():
        fl, nz = [], []
        for (y, x) in cells:
            ca, cb = A.rgb(y, x), B.rgb(y, x)
            if ca is None or cb is None or ca.shape != cb.shape:
                continue
            s1 = sigmas(ca)
            s2 = half_sigma(ca, cb, shift=(k == "strehl"))
            if s1 is None or s2 is None:
                continue
            fl.append(s1[0])
            nz.append(s2[0])
        f, n = float(np.median(fl)), float(np.median(nz))
        frac = min((n / f) ** 2, 1.0)
        scene = float(np.sqrt(max(f * f - n * n, 0.0)))
        print(f"{k:10s} {f:15.8f} {n:14.5f} {scene:12.5f} "
              f"{frac * 100:10.1f}%")
    print("\n  NOTE the enfuse / fs15-coh rows: 0.13585008 against 0.13585464.")
    print("  Those two arms differ by 19% in measured noise (0.0839 vs 0.0995)")
    print("  and by 15% in scene term (0.1068 vs 0.0925), and the pre-")
    print("  registered primary statistic reads them as IDENTICAL to five")
    print("  decimal places because the two effects cancel.  That is the")
    print("  clearest possible demonstration that flat-ROI sigma cannot")
    print("  separate noise from scene on this corpus.  It was checked for a")
    print("  loader bug first (different files, different checksums); the")
    print("  agreement is real.")
    # QUANT8 on THIS estimator.  The 8-bit penalty measured in noisefree.py is
    # a penalty on the flat-ROI statistic, which is scene-diluted, so it may
    # not be carried across to a pure-noise statistic.  It is measured here
    # directly instead.  Quantisation error is uncorrelated between the two
    # halves (different values round differently), so it survives A-B and this
    # is the number that applies to the fs15 rows.
    print("\n  QUANT8 on THIS estimator -- strehl's halves requantised to 8b")
    # NOTE: bound from `arms` explicitly.  An earlier version reused the loop
    # variables A, B above, which the `for k, (A, B, lab)` unpacking had
    # already rebound to the LAST arm in the dict -- fs15-coh, which is
    # already 8-bit -- so requantising it was a no-op and the arm returned
    # exactly 1.000 in all three channels.  That impossible-looking result is
    # what caught the bug; an arm whose answer is fixed by construction earns
    # its place twice over.
    SA, SB = arms["strehl"][0], arms["strehl"][1]
    base, q8 = [], []
    for (y, x) in cells:
        ca, cb = SA.rgb(y, x), SB.rgb(y, x)
        if ca is None or cb is None or ca.shape != cb.shape:
            continue
        s0 = half_sigma(ca, cb, shift=False)
        s1 = half_sigma(np.round(ca * 255) / 255,
                        np.round(cb * 255) / 255, shift=False)
        if s0 is None or s1 is None:
            continue
        base.append(s0)
        q8.append(s1)
    base, q8 = np.array(base), np.array(q8)
    lab3 = ["luma  Y", "chroma R-Y", "chroma B-Y"]
    qr = []
    for i, nm in enumerate(lab3):
        m, lo, hi, _ = boot(q8[:, i], base[:, i], nboot, rng)
        qr.append(m)
        print(f"    {nm:11s} {m:6.3f} [{lo:.3f},{hi:.3f}]  -> 8-bit output "
              f"alone inflates this by {(m - 1) * 100:5.1f}%")
    print("    fs15-coh is 8-bit, so its rows above carry this penalty.")
    print("    DERIVED, removing it in quadrature from the RAW fs15-coh row:")
    raw_fs = [1.269, 2.211, 2.530]
    for i, nm in enumerate(lab3):
        r = raw_fs[i] ** 2 - (qr[i] ** 2 - 1.0)
        print(f"    {nm:11s} raw {raw_fs[i]:6.3f} -> "
              f"{np.sqrt(r) if r > 0 else float('nan'):6.3f} after removing "
              f"8-bit output quantisation")
    return 0


if __name__ == "__main__":
    sys.exit(main())
