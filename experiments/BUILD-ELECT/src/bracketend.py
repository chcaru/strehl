"""The bracket-boundary signature: how much of the subject elects the last frames?

The H2 control picture showed the winner field ramping monotonically from the
silhouette inward until it pins at ~204 -- the final frame of a 205-frame bracket
-- over the whole pale wash. That is a checkable signature and a much cheaper one
than any of the measurements so far, because a genuine focus peak is *interior*.
A focus measure whose argmax runs to the end of the bracket and stops there is not
finding a peak; it is climbing a monotone function and hitting the wall.

`merge.rs` already has `Estimator::at_bracket_boundary` (line 1922), so the crate
can measure this on itself.

Reported for the shipped arm, the edge-aware-off arm, and -- as the control that
gives the number meaning -- for the backdrop, where electing a far frame is the
correct answer and the same statistic should be large for honest reasons.
"""
import pathlib

import numpy as np
import tifffile
from scipy import ndimage

OUT = pathlib.Path(r"C:\dev\strehl-out\BUILD-ELECT")
NFRAMES = 205
EDGE = 8          # "at the bracket boundary" = within this many frames of either end


def subject_mask(merge_path):
    """Backdrop is bright; subject is the largest dark connected component."""
    img = tifffile.imread(str(merge_path))
    assert img.dtype == np.uint16, img.dtype
    lum = img.astype(np.float64) @ np.array([0.2126, 0.7152, 0.0722])
    del img
    thr = 0.5 * (np.percentile(lum, 5) + np.percentile(lum, 95))
    subj = lum < thr
    subj = ndimage.binary_closing(subj, np.ones((15, 15)))
    subj = ndimage.binary_opening(subj, np.ones((15, 15)))
    lab, nl = ndimage.label(subj)
    subj = lab == (1 + int(np.argmax(ndimage.sum(subj, lab, range(1, nl + 1)))))
    return subj[::2, ::2], thr, lum.size


def main():
    psubj, thr, n = subject_mask(OUT / "B-noalign-merge.tif")
    print(f"subject mask: threshold {thr:.0f} DN, {100 * psubj.mean():.2f}% of frame")

    # erode so the statistic is about the subject INTERIOR, not the silhouette band
    interior = ndimage.binary_erosion(psubj, np.ones((41, 41)))
    print(f"interior (eroded 41 px on the plane grid): {100 * interior.mean():.2f}%\n")

    print(f"{'arm':<28} {'region':<10} {'at end':>8} {'>=190':>8} {'median':>8} {'p90':>7}")
    print("-" * 74)
    for label, f in (("edge-aware ON (shipped)", "B-noalign-elect.tif"),
                     ("edge-aware OFF (box)", "C-noea-elect.tif")):
        e = tifffile.imread(str(OUT / f))
        assert e.dtype == np.uint16, e.dtype
        e = e.astype(np.int32)
        for region, m in (("subject", interior), ("backdrop", ~psubj)):
            v = e[m]
            at_end = np.mean((v >= NFRAMES - 1 - EDGE) | (v <= EDGE)) * 100
            hi = np.mean(v >= 190) * 100
            print(f"{label:<28} {region:<10} {at_end:7.2f}% {hi:7.2f}% "
                  f"{np.median(v):8.0f} {np.percentile(v, 90):7.0f}")
        del e
    print("\nThe backdrop row is the control: out there a far frame IS the right\n"
          "answer, so a large number is honest. The subject-interior row is the\n"
          "defect -- there the surface is in focus somewhere in the middle of the\n"
          "bracket, and electing the final frames cannot be right.")


if __name__ == "__main__":
    main()
