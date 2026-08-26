"""Is the winner field "blocky" in the sense that implicates the sampling grid?

The owner reads the jagged outline as a blocky winner field. "Blocky" has a
specific, falsifiable meaning: the focus measure aggregates over a SQUARE box
(WINDOW_RADIUS = 13, so 27x27), and the set of pixels whose window touches a given
feature is that feature dilated by a SQUARE. Square dilation produces straight
axis-aligned facets and square corners. If the grid is leaking, seam tangents must
pile up at 0 and 90 degrees.

On flower-bud I measured the opposite over the whole plane -- seams were ANTI-axis
-aligned -- but that test was scoped to the whole winner field, which is dominated
by interior seams. This one is scoped to the silhouette band, where a square
window's support is where it would actually show.

THE NULL THAT MATTERS. A seam that traces a real image edge inherits that edge's
orientation. Photographs of legs and hairs are full of long straight structures,
and finding straight seams on top of them proves nothing. So every seam statistic
is computed alongside the identical statistic on the MERGE'S OWN luminance edges
in the same region. The claim "the grid is leaking" requires the seams to be more
axis-aligned than the picture they sit on.

A uniform-orientation null is also printed, because if neither seams nor image
edges beat uniform then the estimator has no power here and both numbers are
noise.
"""
import pathlib

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import tifffile
from scipy import ndimage

OUT = pathlib.Path(r"C:\dev\strehl-out\BUILD-ELECT\bee")
PICS = OUT / "pics"
JUMP = 20
SMOOTH = 2.0        # px, tangent estimation scale on the plane grid


def orientations(field, mask):
    """Tangent angle to the nearest axis, in degrees, at masked pixels."""
    gy, gx = np.gradient(gaussian(field))
    # gradient direction is normal to the contour; fold to [0, 90]
    ang = np.degrees(np.arctan2(np.abs(gy), np.abs(gx)))
    a = ang[mask]
    return np.minimum(a, 90.0 - a)      # distance to the nearest axis, 0..45


def gaussian(a):
    return ndimage.gaussian_filter(a.astype(np.float64), SMOOTH, mode="nearest")


def report(name, d):
    if d.size < 200:
        print(f"  {name:<24} too few samples ({d.size})")
        return None
    near = float(np.mean(d < 10.0) * 100)
    print(f"  {name:<24} n={d.size:>8}  within 10deg of an axis {near:6.2f}%   "
          f"mean distance to axis {d.mean():5.2f}deg")
    return near


def main():
    PICS.mkdir(parents=True, exist_ok=True)
    e = tifffile.imread(str(OUT / "D-elect.tif")).astype(np.float64)
    img = tifffile.imread(str(OUT / "D-merge.tif"))
    assert img.dtype == np.uint16, img.dtype
    lum = (img.astype(np.float64) @ np.array([0.2126, 0.7152, 0.0722]))[::2, ::2]
    del img

    gy, gx = np.gradient(e)
    seam = np.hypot(gx, gy) > JUMP
    ly, lx = np.gradient(gaussian(lum))
    lmag = np.hypot(lx, ly)
    edge = lmag > np.percentile(lmag, 99.0)      # the picture's own strong edges

    # subject = dark on white paper
    thr = 0.5 * (np.percentile(lum, 5) + np.percentile(lum, 95))
    subj = lum < thr
    subj = ndimage.binary_opening(ndimage.binary_closing(subj, np.ones((9, 9))),
                                  np.ones((9, 9)))
    d_in = ndimage.distance_transform_edt(np.pad(subj, 64, mode="edge"))[64:-64, 64:-64]
    d_out = ndimage.distance_transform_edt(np.pad(~subj, 64, mode="edge"))[64:-64, 64:-64]
    band = ((subj & (d_in <= 40)) | (~subj & (d_out <= 40)))   # the silhouette band
    interior = subj & (d_in > 40)

    print(f"subject {100 * subj.mean():.2f}% of plane; silhouette band "
          f"{100 * band.mean():.2f}%; interior {100 * interior.mean():.2f}%")
    print(f"seam pixels {100 * seam.mean():.2f}% of plane\n")

    print("distance-to-nearest-axis of the tangent; a UNIFORM null gives 22.22% "
          "within 10deg, mean 22.50deg")
    print("\nSILHOUETTE BAND (within 40 plane px of the silhouette)")
    s_band = report("winner-field seams", orientations(e, seam & band))
    i_band = report("the picture's own edges", orientations(lum, edge & band))

    print("\nSUBJECT INTERIOR (more than 40 plane px in)")
    s_int = report("winner-field seams", orientations(e, seam & interior))
    i_int = report("the picture's own edges", orientations(lum, edge & interior))

    print("\nVERDICT")
    UNIFORM = 22.22
    for tag, s, i in (("silhouette band", s_band, i_band),
                      ("subject interior", s_int, i_int)):
        if s is None or i is None:
            continue
        # Two conditions, and BOTH are required. Beating the picture-edge baseline
        # alone is not enough: if the picture's edges happen to be unusually
        # non-axial, a seam distribution that is merely uniform will clear it and
        # look like grid leakage. A square window has to pile density AT the axes,
        # so the seams must also beat the uniform null.
        beats_picture = s > i + 3.0
        beats_uniform = s > UNIFORM + 3.0
        if beats_picture and beats_uniform:
            print(f"  {tag:<18} GRID SIGNATURE: seams pile at the axes "
                  f"({s:.2f}% vs picture {i:.2f}%, uniform {UNIFORM:.2f}%)")
        else:
            why = []
            if not beats_uniform:
                why.append(f"does not beat the uniform null ({s:.2f}% vs {UNIFORM:.2f}%)")
            if not beats_picture:
                why.append(f"does not beat the picture ({s:.2f}% vs {i:.2f}%)")
            print(f"  {tag:<18} NO grid signature -- " + "; ".join(why))

    fig, ax = plt.subplots(figsize=(9, 5.5))
    bins = np.linspace(0, 45, 46)
    for lab, d, c in (("seams, silhouette band", orientations(e, seam & band), "tab:red"),
                      ("picture edges, silhouette band", orientations(lum, edge & band),
                       "tab:blue"),
                      ("seams, interior", orientations(e, seam & interior), "tab:orange")):
        if d.size > 200:
            ax.hist(d, bins=bins, density=True, histtype="step", lw=2, label=lab, color=c)
    ax.axhline(1 / 45, color="k", ls="--", lw=1.4, label="uniform null")
    ax.set_xlabel("distance of tangent to the nearest axis (deg)")
    ax.set_ylabel("density")
    ax.set_title("bee-1-cpl: are winner-field seams axis-aligned?\n"
                 "a box window would pile density at 0 deg")
    ax.legend(fontsize=9); ax.grid(alpha=.3)
    fig.tight_layout()
    p = PICS / "BEE3-orientation.png"
    fig.savefig(p, dpi=115); plt.close(fig)
    print(f"\nwrote {p}")


if __name__ == "__main__":
    main()
