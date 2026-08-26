"""Two-sided edge profile: is the pyramid removing a veil, or adding an overshoot?

`veilpair.py` profiled only the background side of the silhouette. That cannot
tell the two hypotheses apart, because they make the SAME prediction there:

  H1 veil removal   -> background near the edge moves TOWARD far-field.
  H2 edge overshoot -> background near the edge is pushed BRIGHTER, which also
                       moves it toward (and past) far-field.

They differ on the other side. An overshoot is antisymmetric about the edge: the
dark side is pushed darker by roughly as much as the bright side is pushed
brighter. Veil removal is one-sided -- it has no reason to touch the subject
interior at all.

So: signed distance, negative inside the subject, positive outside, and report
the arm difference on both sides. Mask and distance computed ONCE from the
reference arm and applied to both, so both arms score identical pixels.
"""
import sys
import numpy as np
import tifffile
from scipy import ndimage


def luma(a):
    a = a.astype(np.float64)
    if a.ndim == 3 and a.shape[2] >= 3:
        return 0.2126 * a[:, :, 0] + 0.7152 * a[:, :, 1] + 0.0722 * a[:, :, 2]
    return a


# negative = inside subject, positive = outside
BINS = [(-128, -64), (-64, -32), (-32, -16), (-16, -8), (-8, -4), (-4, -2),
        (-2, 0), (0, 2), (2, 4), (4, 8), (8, 16), (16, 32), (32, 64), (64, 128)]


def main():
    if len(sys.argv) < 3:
        print("usage: twoside.py <ref.tiff> <arm.tiff> [--q 0.35]")
        return 2
    q = 0.35
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if "--q" in sys.argv:
        q = float(sys.argv[sys.argv.index("--q") + 1])

    ref_p, arm_p = args[0], args[1]
    A = tifffile.imread(ref_p)
    B = tifffile.imread(arm_p)
    if A.shape != B.shape:
        print(f"shape mismatch {A.shape} vs {B.shape}")
        return 1
    ya, yb = luma(A), luma(B)

    thr = float(np.quantile(ya, q))
    subj = ya < thr
    subj = ndimage.binary_opening(subj, np.ones((5, 5)))
    subj = ndimage.binary_closing(subj, np.ones((5, 5)))
    d_out = ndimage.distance_transform_edt(~subj)
    d_in = ndimage.distance_transform_edt(subj)
    sd = np.where(subj, -d_in, d_out)

    print(f"mask threshold {thr:.1f} DN, subject {100*subj.mean():.1f}% "
          f"(subject = DARKER side)")
    print()
    print(f"{'signed dist':>14} {'n':>11} {'ctrl med':>11} {'blend med':>11} "
          f"{'blend-ctrl':>12}")
    print("-" * 64)
    rows = []
    for lo, hi in BINS:
        sel = (sd >= lo) & (sd < hi)
        n = int(sel.sum())
        if n < 500:
            print(f"{f'{lo}..{hi}':>14} {n:>11,} {'--':>11} {'--':>11} {'--':>12}")
            continue
        ma, mb = float(np.median(ya[sel])), float(np.median(yb[sel]))
        rows.append((lo, hi, ma, mb))
        print(f"{f'{lo}..{hi}':>14} {n:>11,} {ma:>11.1f} {mb:>11.1f} "
              f"{mb-ma:>+12.1f}")

    ins = [r for r in rows if r[1] <= 0]
    out = [r for r in rows if r[0] >= 0]
    if ins and out:
        # nearest bins to the edge on each side
        near_in = max(ins, key=lambda r: r[0])
        near_out = min(out, key=lambda r: r[0])
        di = near_in[3] - near_in[2]
        do = near_out[3] - near_out[2]
        print()
        print(f"nearest INSIDE  bin {near_in[0]}..{near_in[1]}:  blend-ctrl {di:+.1f} DN")
        print(f"nearest OUTSIDE bin {near_out[0]}..{near_out[1]}:  blend-ctrl {do:+.1f} DN")
        print()
        if di < -100 and do > 100:
            print("VERDICT: ANTISYMMETRIC -- dark side pushed darker AND bright side")
            print("         pushed brighter. That is an EDGE OVERSHOOT, not veil")
            print("         removal. The apparent veil win is the bright lobe of a")
            print("         new artifact, and the dark lobe is what clips to zero.")
        elif do > 100 and abs(di) <= 100:
            print("VERDICT: ONE-SIDED -- background moved, subject interior did not.")
            print("         Consistent with genuine veil removal.")
        elif di < -100 and do <= 100:
            print("VERDICT: subject darkened without background change. Neither")
            print("         hypothesis as stated; investigate before concluding.")
        else:
            print("VERDICT: neither side moved by more than 100 DN at the edge.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
