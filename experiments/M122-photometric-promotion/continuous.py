"""M122 AMENDMENT 1 -- the blur control as a continuous covariate, not a bin.

PREREGISTRATION AMENDMENT 1 sections 1d/1e. Retires the smooth/textured split,
which ranks windows by coarse subsampled `std` -- i.e. by CONTRAST, not by
pixel-level texture -- and therefore puts smooth windows and mixed
subject/background windows into the "textured" bin. Discipline 837.

For every window of a stack, with NO brightness gate and NO ranking, record
hf(A0) and hf(A1). Then:

    hf1n = hf1 / (level ratio)          level-normalised (report M20: hf is
                                        absolute and scales with level)
    k    = Theil-Sen slope of hf1n on hf0, over the UPPER HALF of hf0
    c    = the Theil-Sen intercept

    a BLUR multiplies real structure by a constant fraction wherever it is:
        k < 1, ratio below 1 at every hf0.
    a BACKGROUND LEVEL FIX removes an additive excess that only exists where
    the background is smooth:
        k ~ 1, ratio departs from 1 only at low hf0 and returns to 1.

Gate: a stack FAILS the blur control if k < 0.97.

Power (rule 20 -- the input that must make the gate fail): the same k is
computed for a sigma=0.5 gaussian blur of A0 scored as the test arm. If that
does not come out well below 0.97, the gate cannot fire and no pass from it
means anything.

Reads C:\\dev\\strehl-out\\M122\\measure. Writes C:\\dev\\strehl-out\\M122.
Never touches D:\\.
"""

import json
import os

import numpy as np
import tifffile
from scipy.ndimage import gaussian_filter
from scipy.stats import theilslopes

MEAS = r"C:\dev\strehl-out\M122\measure"
OUT = r"C:\dev\strehl-out\M122"
S, BORDER, STRIDE = 256, 400, 128
GATE = 0.97


def load(p):
    a = tifffile.imread(p)
    assert a.dtype == np.uint16, "%s read as %s, expected uint16" % (p, a.dtype)
    return a[..., :3].astype(np.float64).mean(axis=2) if a.ndim == 3 else a.astype(np.float64)


def hf(w):
    lap = -4 * w[1:-1, 1:-1] + w[:-2, 1:-1] + w[2:, 1:-1] + w[1:-1, :-2] + w[1:-1, 2:]
    return float(np.sqrt((lap ** 2).mean()))


def scan(A0, A1):
    """Every window. No gate, no ranking."""
    H, W = A0.shape
    out = []
    for y in range(BORDER, H - S - BORDER, STRIDE):
        for x in range(BORDER, W - S - BORDER, STRIDE):
            w0 = A0[y:y + S, x:x + S]
            w1 = A1[y:y + S, x:x + S]
            m0, m1 = float(w0.mean()), float(w1.mean())
            out.append((hf(w0), hf(w1), m0, m1, x, y))
    return out


def slope(rec):
    """Theil-Sen slope of level-normalised hf1 on hf0, upper half of hf0."""
    h0 = np.array([r[0] for r in rec])
    h1 = np.array([r[1] for r in rec])
    lr = np.array([r[3] / max(r[2], 1e-9) for r in rec])
    h1n = h1 / np.where(lr > 0, lr, 1.0)
    cut = float(np.median(h0))
    m = h0 >= cut
    if m.sum() < 8:
        return None
    k, c, lo, hi = theilslopes(h1n[m], h0[m], 0.95)
    return dict(k=float(k), c=float(c), k_lo=float(lo), k_hi=float(hi),
                n_upper=int(m.sum()), hf0_cut=cut)


def profile(rec):
    """Median level-normalised ratio in deciles of hf0 -- aggregate last."""
    h0 = np.array([r[0] for r in rec])
    h1 = np.array([r[1] for r in rec])
    lr = np.array([r[3] / max(r[2], 1e-9) for r in rec])
    h1n = h1 / np.where(lr > 0, lr, 1.0)
    ratio = h1n / np.maximum(h0, 1e-9)
    edges = np.percentile(h0, np.arange(0, 101, 10))
    rows = []
    for i in range(10):
        m = (h0 >= edges[i]) & (h0 <= edges[i + 1] if i == 9 else h0 < edges[i + 1])
        if m.sum():
            rows.append(dict(decile=i + 1, hf0_med=float(np.median(h0[m])),
                             ratio_med=float(np.median(ratio[m])), n=int(m.sum())))
    return rows


def main():
    subs = sorted({f.split("__")[0] for f in os.listdir(MEAS) if f.endswith("__A0.tif")})
    out = []
    print("%-38s %7s %7s %8s %9s %8s %9s" %
          ("stack", "k", "k_lo", "k_hi", "intercept", "k_blur", "gate"))
    for s in subs:
        p0 = os.path.join(MEAS, "%s__A0.tif" % s)
        p1 = os.path.join(MEAS, "%s__A1.tif" % s)
        if not os.path.exists(p1):
            continue
        A0, A1 = load(p0), load(p1)
        if A0.shape != A1.shape:
            continue
        rec = scan(A0, A1)
        sl = slope(rec)
        blur = slope(scan(A0, gaussian_filter(A0, sigma=0.5, mode="nearest")))
        if sl is None or blur is None:
            continue
        gate = "PASS" if sl["k"] >= GATE else "**FAIL**"
        print("%-38s %7.4f %7.4f %8.4f %9.2f %8.4f %9s" %
              (s, sl["k"], sl["k_lo"], sl["k_hi"], sl["c"], blur["k"], gate))
        out.append(dict(stack=s, k=sl["k"], k_lo=sl["k_lo"], k_hi=sl["k_hi"],
                        intercept=sl["c"], n_upper=sl["n_upper"], hf0_cut=sl["hf0_cut"],
                        k_blur=blur["k"], blur_intercept=blur["c"],
                        gate="PASS" if sl["k"] >= GATE else "FAIL",
                        n_windows=len(rec), profile=profile(rec)))

    kb = [r["k_blur"] for r in out]
    print("\nPOWER (rule 20): sigma=0.5 blur of A0 scored as the test arm.")
    print("  The gate is commissioned PER STACK, not corpus-wide: a stack whose own")
    print("  blur plant does not come out below %.2f cannot have its k read at all." % GATE)
    dead = [r["stack"] for r in out if r["k_blur"] >= GATE]
    live = [r for r in out if r["k_blur"] < GATE]
    print("  k_blur over commissioned stacks: median %.4f  worst %.4f  n=%d"
          % (float(np.median([r["k_blur"] for r in live])),
             float(max(r["k_blur"] for r in live)), len(live)))
    print("  gate NOT commissioned on: %s" % (dead or "none"))
    print("  (a stack whose windows span too narrow an hf0 range cannot support a"
          " slope estimate; that is a property of the stack, not of --photometric)")
    fails = [r["stack"] for r in live if r["gate"] == "FAIL"]
    print("\nstacks where --photometric FAILS the amended blur gate (k < %.2f) AND the"
          " gate is commissioned:\n  %s" % (GATE, fails or "none"))
    uninterp = [r["stack"] for r in out if r["k_blur"] >= GATE and r["gate"] == "FAIL"]
    print("stacks reading k < %.2f but with an uncommissioned gate (NOT interpretable): %s"
          % (GATE, uninterp or "none"))
    for r in out:
        r["gate_commissioned"] = bool(r["k_blur"] < GATE)
    json.dump(out, open(os.path.join(OUT, "continuous.json"), "w"), indent=1)
    print("wrote %s" % os.path.join(OUT, "continuous.json"))


if __name__ == "__main__":
    main()
