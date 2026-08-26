"""Discriminate ALIGNED-to-green from BLURRED for the lateral-CA correction.

The problem this exists to solve: at an edge carrying lateral CA, the R channel's
high-frequency energy INCLUDES the fringe.  Removing the fringe therefore lowers
sigma_HF(R) -- and so does blurring R.  An amplitude number cannot tell the two
apart (SS33: "a noise figure alone cannot tell a well-averaged region from a
destroyed one").

The discriminator is not amplitude but REGISTRATION:

    correction works  ->  R's edges move ONTO G's edges  ->  corr(HF_R, HF_G) UP
    correction blurs  ->  R's edges smear across G's     ->  corr(HF_R, HF_G) DOWN

Both hypotheses predict the amplitude falls.  Only one predicts correlation rises.

Controls:
  * corr(HF_G, HF_G) across arms must be ~1 (green is untouched).
  * A synthetic BLUR arm is built from the ca-OFF image by blurring R and B with
    a kernel calibrated to reproduce the SAME amplitude loss the real correction
    produced.  That is the potency control: it proves this instrument can see a
    blur of exactly the size in question, so a null on the real arm is a real null.

Usage:
    python caalign.py <arm_off.tif> <arm_on.tif>
"""

import sys
import numpy as np
import tifffile


def hf(ch):
    v = np.zeros_like(ch)
    v[1:-1, 1:-1] = (4.0 * ch[1:-1, 1:-1]
                     - ch[:-2, 1:-1] - ch[2:, 1:-1]
                     - ch[1:-1, :-2] - ch[1:-1, 2:])
    return v


def rsig(v):
    med = np.median(v)
    return float(1.4826 * np.median(np.abs(v - med)))


def corr(a, b):
    a = a - a.mean()
    b = b - b.mean()
    d = np.sqrt((a * a).sum() * (b * b).sum())
    return float((a * b).sum() / d) if d else float("nan")


def blur3(ch, w):
    """Separable [w, 1-2w, w] blur -- one knob, monotone in strength."""
    o = ch.copy()
    o[:, 1:-1] = w * ch[:, :-2] + (1 - 2 * w) * ch[:, 1:-1] + w * ch[:, 2:]
    p = o.copy()
    p[1:-1, :] = w * o[:-2, :] + (1 - 2 * w) * o[1:-1, :] + w * o[2:, :]
    return p


def main():
    off = tifffile.imread(sys.argv[1]).astype(np.float32) / 65535.0
    on = tifffile.imread(sys.argv[2]).astype(np.float32) / 65535.0
    print(f"shape {off.shape}")

    gmean = 0.5 * (off[:, :, 1] + on[:, :, 1])
    gx = np.zeros_like(gmean); gy = np.zeros_like(gmean)
    gx[:, 1:-1] = gmean[:, 2:] - gmean[:, :-2]
    gy[1:-1, :] = gmean[2:, :] - gmean[:-2, :]
    edge = np.hypot(gx, gy) >= float(np.quantile(np.hypot(gx, gy), 0.99))
    n = int(edge.sum())
    print(f"edge set = top 1% gradient on arm-mean, n={n:,}\n")

    hfo = [hf(off[:, :, c])[edge] for c in range(3)]
    hfn = [hf(on[:, :, c])[edge] for c in range(3)]

    # CONTROL 1 tests a stronger claim than this analysis needs: that the
    # correction is a pure R/B warp leaving green bit-identical.  On this
    # pipeline it FAILS, and the failure is already explained -- CA correction
    # runs pre-demosaic, so moving R and B changes green's interpolation
    # (V-CHROMA: cross-channel demosaic coupling, not an election shift).
    #
    # It is reported, not deleted, and it forces the comparison below to be
    # WITHIN-arm: each arm's R is compared against ITS OWN green.  A within-arm
    # comparison does not assume green is fixed across arms.
    print("CONTROL 1  is green invariant across arms? (tests 'pure R/B warp')")
    cg = corr(hfo[1], hfn[1])
    sg = rsig(hfn[1]) / rsig(hfo[1])
    print(f"  corr(HF_G off, HF_G on) = {cg:.6f}    amplitude ratio = {sg:.6f}")
    if cg < 0.995:
        print(f"  RESULT: FAILED -- green's PATTERN moved ({100*(1-cg):.1f}% decorrelated)")
        print(f"          while its AMPLITUDE did not ({100*(sg-1):+.2f}%).")
        print( "          Expected: correction is pre-demosaic, so R/B moves recolour G.")
        print( "          Consequence: green is not a fixed cross-arm reference.")
        print( "          All comparisons below are therefore WITHIN-arm only.")
    else:
        print("  RESULT: passed -- green is invariant across arms.")

    # Guard the within-arm comparison: it is only meaningful if green's own
    # sharpness is comparable in the two arms, else corr(R,G) could move
    # because G changed rather than because R did.
    if abs(sg - 1.0) > 0.02:
        print(f"  *** green sharpness moved {100*(sg-1):+.1f}% -- within-arm corr(R,G)")
        print( "      is confounded by the reference itself. STOP.")
        return 1

    # Potency control: synthesise a blur arm matched to the measured amplitude loss.
    print("\nCONTROL 2  potency -- can this instrument see a blur of the size in question?")
    targets = {}
    for c, nm in ((0, "R"), (2, "B")):
        want = rsig(hfn[c]) / rsig(hfo[c])
        best, bw = None, None
        for w in np.arange(0.01, 0.35, 0.005):
            r = rsig(hf(blur3(off[:, :, c], float(w)))[edge]) / rsig(hfo[c])
            if best is None or abs(r - want) < abs(best - want):
                best, bw = r, float(w)
        targets[nm] = (bw, best, want)
        print(f"  {nm}: real arm amplitude ratio {want:.4f}; "
              f"synthetic blur w={bw:.3f} reproduces {best:.4f}")

    print(f"\n{'pair (WITHIN-arm)':<24} {'OFF':>9} {'ON':>9} {'BLUR-ctl':>9}  verdict")
    ok = True
    for c, nm in ((0, "R"), (2, "B")):
        w = targets[nm][0]
        hb = hf(blur3(off[:, :, c], w))[edge]
        c_off = corr(hfo[c], hfo[1])
        c_on = corr(hfn[c], hfn[1])
        c_blur = corr(hb, hfo[1])
        if c_blur >= c_off:
            print(f"  potency FAILED for {nm}: synthetic blur did not lower corr "
                  f"({c_off:.4f} -> {c_blur:.4f}). Instrument cannot see a blur.")
            ok = False
            continue
        verdict = "ALIGNED (corr up)" if c_on > c_off else "BLURRED (corr down)"
        print(f"corr(HF_{nm}, HF_G){'':<9} {c_off:>9.5f} {c_on:>9.5f} {c_blur:>9.5f}  {verdict}")
    if not ok:
        return 1

    print("\n  amplitude alone would have called both arms a loss;")
    print("  the blur control shows what a real loss of that size looks like.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
