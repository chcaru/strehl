"""Is the outer-annulus 'sharpness gain' real detail, or the black fill's edge?

warp_frame_in_place writes the black level wherever the gather leaves the source
frame. Where the merge then averages those, the render can carry dark wedges whose
BOUNDARY is a very strong gradient -- which a Tenengrad statistic would happily
report as 'sharpness'. That would be an artefact of my own fill, not a measurement
of the subject, and it would invalidate the radial result.

This checks it directly: what fraction of each annulus is near-black, before and
after? If the aligned image has dark pixels the unaligned one does not, the gain
is suspect and must be re-measured on the covered region only.
"""

import sys
import numpy as np
import tifffile

N_ANN = 8


def main(p_before, p_after):
    b = tifffile.imread(p_before)[:, :, 1].astype(np.float64)
    a = tifffile.imread(p_after)[:, :, 1].astype(np.float64)
    h, w = b.shape
    yy, xx = np.mgrid[0:h, 0:w]
    cy, cx = (h - 1) / 2.0, (w - 1) / 2.0
    r = np.sqrt(((yy - cy) / cy) ** 2 + ((xx - cx) / cx) ** 2) / np.sqrt(2.0)

    # "Near black" relative to each image's own distribution, so a global
    # brightness difference cannot masquerade as coverage loss.
    thr_b = np.percentile(b, 0.5)
    thr_a = np.percentile(a, 0.5)
    print(f"  0.5th percentile: before {thr_b:.1f}, after {thr_a:.1f}")
    # A fixed absolute floor is the honest test for a black fill.
    floor = 64.0
    print(f"  absolute floor used: {floor}")
    print()
    print("  annulus         frac<floor before   frac<floor after     delta")
    edges = np.linspace(0.0, r.max(), N_ANN + 1)
    for i in range(N_ANN):
        lo, hi = edges[i], edges[i + 1]
        sel = (r >= lo) & (r < hi)
        if sel.sum() < 1000:
            continue
        fb = (b[sel] < floor).mean()
        fa = (a[sel] < floor).mean()
        print(f"  {lo:5.3f}-{hi:5.3f}      {fb:16.6f}   {fa:16.6f}   {fa-fb:+9.6f}")

    print()
    print(f"  WHOLE  before {(b < floor).mean():.6f}   after {(a < floor).mean():.6f}")

    # Where exactly does the aligned image go dark?
    dark = a < floor
    if dark.any():
        ys, xs = np.nonzero(dark)
        print()
        print(f"  aligned dark pixels: {dark.sum()} "
              f"({100.0*dark.mean():.3f}% of frame)")
        print(f"    x range {xs.min()}..{xs.max()}  (w={w})")
        print(f"    y range {ys.min()}..{ys.max()}  (h={h})")
    else:
        print("\n  aligned image has NO pixels below the floor.")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
