"""Measure the silhouette veil as a function of the gate.

CONTEXT. Facts 1371-1372 recorded a bright veil hugging the whole subject
silhouette, 20-40 px into the defocused background. Fact 1375 measured it
INVARIANT across all three resampler kernels, which cleanly excluded resampling
as the cause. The G4 montage suggests it is NOT invariant across the gate.

That is an eye judgement on four panels and it is not evidence. This measures it.

METHOD. The subject is dark, the background bright. Build a subject mask by
threshold, take the exact Euclidean distance transform outward from it, and
profile the background level against distance-from-subject in rings. A veil
appears as EXCESS brightness in the near rings relative to the far background.
Because every arm is byte-identical except the gate, and all four are pinned to
--exposure=1.54, ring profiles are directly comparable between arms.

CONTROL (this is the part that can kill the result). A gate change alters the
background NOISE enormously in flat regions (measured: 33.5x from gate 4 to
gate 0). Noise is symmetric and must not shift a MEDIAN, so the profile uses
per-ring medians rather than means. If the veil amplitude tracked the noise
instead of the gate, the effect would be an artifact of the statistic.
Reported alongside: per-ring MAD, so any reader can see the noise moving and
confirm the median is not following it.
"""
import os

import numpy as np
import tifffile
from scipy import ndimage

OUT = r"C:\dev\strehl-out\ORCH-gate"
GATES = ["4.00", "2.00", "0.7078", "0.00"]
Y, X, S = 3150, 700, 900          # the region facts 1371-1372 were measured on


def load(g):
    return tifffile.imread(os.path.join(OUT, f"pin-bee-3-cpl-gate-{g}.tif"))[Y:Y + S, X:X + S]


def main():
    ref = load("4.00").astype(np.float32).mean(axis=2)
    thr = np.percentile(ref, 45)
    subject = ref < thr
    subject = ndimage.binary_closing(subject, np.ones((5, 5)))
    subject = ndimage.binary_opening(subject, np.ones((3, 3)))
    dist = ndimage.distance_transform_edt(~subject)
    print(f"crop {S}x{S} at ({X},{Y})  threshold {thr:.0f} DN  subject {100*subject.mean():.1f}% of crop")

    edges = [(1, 5), (5, 10), (10, 20), (20, 30), (30, 45), (45, 60), (60, 90), (90, 130), (130, 200)]
    far = (dist >= 130) & (dist < 200)

    prof = {}
    for g in GATES:
        img = load(g).astype(np.float32).mean(axis=2)
        base = float(np.median(img[far]))
        rows = []
        for lo, hi in edges:
            m = (dist >= lo) & (dist < hi)
            if m.sum() < 200:
                rows.append((np.nan, np.nan, 0))
                continue
            v = img[m]
            med = float(np.median(v))
            mad = float(np.median(np.abs(v - med)) * 1.4826)
            rows.append((med - base, mad, int(m.sum())))
        prof[g] = (base, rows)

    print(f"\nVEIL PROFILE -- median background level MINUS the far-field base ({edges[-1][0]}-{edges[-1][1]} px), in DN")
    print(f"{'ring px':>10} " + " ".join(f"{'gate '+g:>12}" for g in GATES) + f" {'n px':>9}")
    for i, (lo, hi) in enumerate(edges):
        cells = " ".join(f"{prof[g][1][i][0]:>12.1f}" for g in GATES)
        print(f"{f'{lo}-{hi}':>10} {cells} {prof[GATES[0]][1][i][2]:>9d}")

    print(f"\nPER-RING NOISE (MAD*1.4826) -- the control: this must move a lot while the medians above do not")
    for i, (lo, hi) in enumerate(edges):
        cells = " ".join(f"{prof[g][1][i][1]:>12.1f}" for g in GATES)
        print(f"{f'{lo}-{hi}':>10} {cells}")

    print(f"\n{'gate':>8} {'far base':>10} {'veil peak':>11} {'ring':>9} {'veil @1-5':>11} {'veil @20-30':>12}")
    peaks = {}
    for g in GATES:
        base, rows = prof[g]
        vals = [r[0] for r in rows[:6]]
        k = int(np.nanargmax(vals))
        peaks[g] = vals[k]
        print(f"{g:>8} {base:>10.1f} {vals[k]:>11.1f} {f'{edges[k][0]}-{edges[k][1]}':>9}"
              f" {rows[0][0]:>11.1f} {rows[3][0]:>12.1f}")

    p4, p0 = peaks["4.00"], peaks["0.00"]
    print(f"\nveil peak, gate 4.00 -> 0.00 : {p4:.1f} -> {p0:.1f} DN"
          f"   ({100*(p0-p4)/p4:+.1f}%)")
    mono = all(peaks[GATES[i]] >= peaks[GATES[i + 1]] for i in range(len(GATES) - 1))
    print("monotone decreasing with the gate:", mono)


if __name__ == "__main__":
    main()
