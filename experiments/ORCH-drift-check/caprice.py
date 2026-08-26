"""Price the lateral-CA correction: does the R/B resample cost resolution?

Control built in: lateral CA correction is a radial resample of R and B only.
Green is not touched.  So sigma_HF(G) must be IDENTICAL between arms.  If green
moves, the correction is doing something other than what it says, and every
other number here is uninterpretable.  That control is checked first and the
script refuses to report if it fails.

Usage:
    python caprice.py <arm_off.tif> <arm_on.tif>
"""

import sys
import numpy as np
import tifffile


def hf(ch):
    """Laplacian-ish high-frequency response, robust sigma."""
    v = np.zeros_like(ch)
    v[1:-1, 1:-1] = (4.0 * ch[1:-1, 1:-1]
                     - ch[:-2, 1:-1] - ch[2:, 1:-1]
                     - ch[1:-1, :-2] - ch[1:-1, 2:])
    return v


def rsig(v):
    med = np.median(v)
    return float(1.4826 * np.median(np.abs(v - med)))


def main():
    p_off, p_on = sys.argv[1], sys.argv[2]
    off = tifffile.imread(p_off).astype(np.float32) / 65535.0
    on = tifffile.imread(p_on).astype(np.float32) / 65535.0
    print(f"shape {off.shape}")

    gmean = 0.5 * (off[:, :, 1] + on[:, :, 1])
    gx = np.zeros_like(gmean); gy = np.zeros_like(gmean)
    gx[:, 1:-1] = gmean[:, 2:] - gmean[:, :-2]
    gy[1:-1, :] = gmean[2:, :] - gmean[:-2, :]
    grad = np.hypot(gx, gy)
    thr = float(np.quantile(grad, 0.99))
    edge = grad >= thr
    print(f"edge set = top 1% gradient on arm-mean, n={int(edge.sum()):,}\n")

    names = ("R", "G", "B")
    res = {}
    for c in range(3):
        a = rsig(hf(off[:, :, c])[edge])
        b = rsig(hf(on[:, :, c])[edge])
        res[names[c]] = (a, b)

    print(f"{'ch':<3} {'sigma_HF off':>13} {'sigma_HF on':>13} {'ON/OFF':>8}")
    for n in names:
        a, b = res[n]
        print(f"{n:<3} {a:>13.6f} {b:>13.6f} {b/a:>8.4f}")

    ga, gb = res["G"]
    gratio = gb / ga
    print()
    print("CONTROL  green must be untouched by a lateral R/B resample.")
    if abs(gratio - 1.0) > 0.002:
        print(f"  *** CONTROL FAILED: green HF moved {100*(gratio-1):+.3f}% "
              f"-- the correction is not a pure R/B warp. Numbers above are not")
        print( "      interpretable as a CA-correction price. STOP.")
        return 1
    print(f"  OK: green HF moved {100*(gratio-1):+.4f}%  (tolerance 0.2%)")
    print()
    for n in ("R", "B"):
        a, b = res[n]
        d = 100.0 * (b / a - 1.0)
        verdict = "COSTS sharpness" if d < -1.0 else ("GAINS" if d > 1.0 else "no material change")
        print(f"  {n}: {d:+.2f}% HF vs its own arm-off  -> {verdict}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
