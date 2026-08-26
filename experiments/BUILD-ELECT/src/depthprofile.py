"""The mechanism's spatial fingerprint: elected index vs depth inside the silhouette.

Everything so far rests on four hand-picked ROIs and two crops. If the cause is a
veiling ramp cast by the defocused silhouette, then it makes a prediction over the
*whole* subject that four ROIs cannot fake:

    the elected frame index must be high close to the silhouette and fall as you
    move inward, with a characteristic reach set by the blur of the far frames.

If instead the patches were a coverage gap (H4), a tile grid (H3) or a box-window
artifact (H1), the elected index would have no reason to organise itself by
distance from the silhouette at all.

CONTROL. The same profile is computed for the *backdrop* side. Out there the far
frames genuinely are in focus, so the profile should be high and should NOT decay
inward -- a decay on both sides would mean the statistic is measuring the distance
transform rather than the picture.

TRAP. scipy's distance_transform_edt treats the array border as object, so
distances blow up at the frame edge. The subject touches the frame here, so the
mask is padded by replication before the transform and cropped after: the frame
edge must not act as a silhouette.
"""
import pathlib

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import tifffile
from scipy import ndimage

OUT = pathlib.Path(r"C:\dev\strehl-out\BUILD-ELECT")
PICS = OUT / "pics"
PAD = 64
BINS = np.arange(0, 420, 20)      # plane px inward from the silhouette


def edt_replicated(mask):
    """Distance to ~mask, with the frame border replicated so it is not an edge."""
    p = np.pad(mask, PAD, mode="edge")
    d = ndimage.distance_transform_edt(p)
    return d[PAD:-PAD, PAD:-PAD]


def main():
    img = tifffile.imread(str(OUT / "B-noalign-merge.tif"))
    assert img.dtype == np.uint16, img.dtype
    lum = img.astype(np.float64) @ np.array([0.2126, 0.7152, 0.0722])
    del img
    thr = 0.5 * (np.percentile(lum, 5) + np.percentile(lum, 95))
    subj = lum < thr
    subj = ndimage.binary_opening(ndimage.binary_closing(subj, np.ones((15, 15))),
                                  np.ones((15, 15)))
    lab, nl = ndimage.label(subj)
    subj = lab == (1 + int(np.argmax(ndimage.sum(subj, lab, range(1, nl + 1)))))
    psubj = subj[::2, ::2]

    d_in = edt_replicated(psubj)        # depth inside the subject
    d_out = edt_replicated(~psubj)      # depth into the backdrop
    print(f"subject {100 * psubj.mean():.2f}% of plane; "
          f"max inward depth {d_in.max():.0f} px, outward {d_out.max():.0f} px")

    e = tifffile.imread(str(OUT / "B-noalign-elect.tif"))
    assert e.dtype == np.uint16, e.dtype
    e = e.astype(np.float64)

    fig, ax = plt.subplots(figsize=(9.5, 6))
    print(f"\n{'depth px':>9} | {'SUBJECT elected':>28} | {'BACKDROP elected':>28}")
    print(f"{'':>9} | {'median':>8}{'p90':>8}{'n':>12} | {'median':>8}{'p90':>8}{'n':>12}")
    print("-" * 74)
    rows = {}
    for name, d, m, c in (("subject", d_in, psubj, "tab:red"),
                          ("backdrop", d_out, ~psubj, "tab:blue")):
        xs, med, p90 = [], [], []
        for lo, hi in zip(BINS[:-1], BINS[1:]):
            sel = m & (d >= lo) & (d < hi)
            if sel.sum() < 500:
                continue
            v = e[sel]
            xs.append(0.5 * (lo + hi)); med.append(np.median(v))
            p90.append(np.percentile(v, 90))
        rows[name] = (xs, med, p90)
        ax.plot(xs, med, c, lw=2.2, marker="o", ms=4, label=f"{name} median")
        ax.fill_between(xs, med, p90, color=c, alpha=.15)
    for i in range(max(len(rows["subject"][0]), len(rows["backdrop"][0]))):
        def cell(n):
            xs, med, p90 = rows[n]
            return (f"{med[i]:8.0f}{p90[i]:8.0f}{'':12}" if i < len(xs)
                    else f"{'-':>8}{'-':>8}{'':12}")
        x = rows["subject"][0][i] if i < len(rows["subject"][0]) else rows["backdrop"][0][i]
        print(f"{x:9.0f} | {cell('subject')} | {cell('backdrop')}")

    ax.set_xlabel("distance from the silhouette (plane px)")
    ax.set_ylabel("elected frame index")
    ax.set_title("Elected frame index vs depth from the silhouette\n"
                 "shaded band = median to p90; subject should decay, backdrop should not")
    ax.grid(alpha=.3); ax.legend()
    fig.tight_layout()
    p = PICS / "DEPTH-profile.png"
    fig.savefig(p, dpi=115); plt.close(fig)
    print(f"\nwrote {p}")


if __name__ == "__main__":
    main()
