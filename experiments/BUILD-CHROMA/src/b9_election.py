"""
b9_election.py -- if axial CA does not make the speckle, does the ELECTION?

b5 excluded axial CA as the cause of the rainbow speckle on two grounds: the
measured dose is roughly an order of magnitude too small, and -- more damning --
the correlation length is wrong. The observed chroma reverses sign between
adjacent ridge pixels at very nearly the rate a random ordering would give
(0.417 observed against 2q(1-q) = 0.404 predicted). A blur difference is a
low-pass operation and cannot produce a pixel-scale process.

Something else must be producing it, and there is an obvious suspect that the
stacker can be asked about directly. The merge elects ONE frame per pixel. If
neighbouring pixels along a hair elect frames that are far apart in the
bracket, the merge is stitched from samples taken at different focus depths --
and since each frame has its own noise realisation and its own defocus, that
stitching is a genuinely pixel-scale process with no smoothness constraint at
all. That is the right shape to make confetti.

`strehl stack --index-map` writes the elected 0-based frame index per plane
pixel, so the hypothesis is directly testable rather than merely plausible.

The measurement compares, on the SAME ridge pixels b5 used:

  ON-HAIR      election roughness along thin bright structures
  OFF-HAIR     election roughness on the local background beside them

and reports the roughness in FRAMES. The comparison matters because a large
absolute roughness would be uninformative on its own -- the whole point of a
focus stack is that the elected index varies across the field. What would
implicate the election is roughness at the PIXEL scale, on the hairs, well
above what the surrounding background shows.

The link to the chroma is then made explicitly: if election jitter drives the
speckle, then ridge pixels whose local election is rough should carry more
chroma than ridge pixels whose local election is smooth. That is a
dose-response within the observed data, and it is the claim being tested.
"""
import os

import numpy as np
from scipy.ndimage import uniform_filter, binary_erosion

from common import OUT, dump
import b3_defects as b3

REND = os.path.join(OUT, "render")


def ridge_mask(img):
    """Same construction b5/b3 used: thin, locally bright, found on GREEN."""
    G = np.asarray(img, dtype=np.float64)[:, :, 1]
    hp = G - uniform_filter(G, 25)
    s = hp[hp > 0].std()
    r = hp > 3.0 * s
    return r & ~binary_erosion(r, iterations=2)


def roughness(idx):
    """Local pixel-scale roughness of the election field, in frames.

    Mean absolute difference to the 4-neighbours. This is deliberately a
    first-difference statistic rather than a local standard deviation: the
    elected index has a real, wanted large-scale gradient across a tilted
    subject, and a variance over any window wide enough to be stable would
    read that gradient as roughness. A 1-px difference does not.
    """
    d = np.zeros_like(idx, dtype=np.float64)
    d[1:, :] += np.abs(idx[1:, :] - idx[:-1, :])
    d[:-1, :] += np.abs(idx[1:, :] - idx[:-1, :])
    d[:, 1:] += np.abs(idx[:, 1:] - idx[:, :-1])
    d[:, :-1] += np.abs(idx[:, 1:] - idx[:, :-1])
    return d / 4.0


def run(stack="lavendar-cpl"):
    ip = os.path.join(REND, "lavendar-index.tif")
    mp = os.path.join(REND, f"{stack}-merge.tif")
    import tifffile
    idx = tifffile.imread(ip).astype(np.float64)
    if idx.ndim == 3:
        idx = idx[:, :, 0]
    merge = b3.read16(mp)
    print(f"-- index map {idx.shape} range {idx.min():.0f}..{idx.max():.0f} frames")
    print(f"-- merge     {merge.shape}")

    # the index map is on the PLANE grid (half resolution); the merge output
    # here is binned to the same grid, so they should already correspond
    mh, mw = merge.shape[:2]
    ih, iw = idx.shape
    if (ih, iw) != (mh, mw):
        n = min(ih, mh), min(iw, mw)
        print(f"   grids differ; cropping both to {n}")
        idx = idx[:n[0], :n[1]]
        merge = merge[:n[0], :n[1]]

    rough = roughness(idx)
    ridge = ridge_mask(merge)
    # background comparison: near the hairs but not on them
    from scipy.ndimage import binary_dilation
    near = binary_dilation(ridge, iterations=6) & ~binary_dilation(ridge, iterations=2)

    res = {
        "stack": stack,
        "index_range_frames": [float(idx.min()), float(idx.max())],
        "n_ridge_px": int(ridge.sum()),
        "n_near_px": int(near.sum()),
        "roughness_on_hair_median": float(np.median(rough[ridge])),
        "roughness_on_hair_p90": float(np.percentile(rough[ridge], 90)),
        "roughness_off_hair_median": float(np.median(rough[near])),
        "roughness_off_hair_p90": float(np.percentile(rough[near], 90)),
        "roughness_whole_field_median": float(np.median(rough)),
    }
    print(f"   election roughness (frames per 1-px step):")
    print(f"     on  hair  median {res['roughness_on_hair_median']:7.3f}"
          f"   p90 {res['roughness_on_hair_p90']:7.3f}  (n={res['n_ridge_px']})")
    print(f"     off hair  median {res['roughness_off_hair_median']:7.3f}"
          f"   p90 {res['roughness_off_hair_p90']:7.3f}  (n={res['n_near_px']})")
    print(f"     whole field median {res['roughness_whole_field_median']:7.3f}")

    # ---- dose-response: does rough election carry more chroma? -----------
    m = np.asarray(merge, dtype=np.float64)
    eps = 1e-9
    rg = m[:, :, 0] / np.maximum(m[:, :, 1], eps)
    rg_hp = rg - uniform_filter(rg, 25)
    v = np.abs(rg_hp[ridge])
    r = rough[ridge]
    qs = [0, 25, 50, 75, 90, 100]
    edges = np.percentile(r, qs)
    print(f"   chroma |R/G high-pass| by election-roughness quartile:")
    bins = []
    for i in range(len(edges) - 1):
        sel = (r >= edges[i]) & (r <= edges[i + 1] if i == len(edges) - 2
                                 else r < edges[i + 1])
        if sel.sum() < 50:
            continue
        b = {"q_lo": qs[i], "q_hi": qs[i + 1],
             "rough_lo": float(edges[i]), "rough_hi": float(edges[i + 1]),
             "n": int(sel.sum()), "median_abs_chroma": float(np.median(v[sel]))}
        bins.append(b)
        print(f"     rough {b['rough_lo']:6.2f}-{b['rough_hi']:6.2f} frames  "
              f"n {b['n']:7d}   |chroma| {b['median_abs_chroma']:.4f}")
    res["chroma_by_roughness"] = bins
    if len(bins) >= 2:
        lo, hi = bins[0]["median_abs_chroma"], bins[-1]["median_abs_chroma"]
        res["chroma_ratio_roughest_over_smoothest"] = float(hi / max(lo, 1e-9))
        print(f"   roughest / smoothest chroma ratio: "
              f"{res['chroma_ratio_roughest_over_smoothest']:.2f}x")

    # ---- the remaining suspect: CFA co-siting on sub-Nyquist detail ------
    # With election jitter and axial CA both excluded, the candidate left is
    # the sampling lattice itself. In this byte-frozen binned output each pixel
    # is one 2x2 sensor quad, and R, G and B are NOT co-sited inside it: R sits
    # at (0,0) and B at (1,1), a full sensel apart on the diagonal. For a hair
    # one or two sensels wide, the R site and the B site are therefore looking
    # at DIFFERENT PARTS OF THE STRUCTURE, and binning asserts they are the
    # same point. That is a per-pixel, uncorrelated colour error on exactly the
    # structures where the speckle is seen -- the right magnitude, the right
    # correlation length, present before any stacking, and untouched by
    # defocus dose. It is ordinary Bayer aliasing on detail above Nyquist.
    #
    # It makes a sharp prediction that nothing else here makes: the chroma must
    # scale INVERSELY with structure width, and must approach zero for
    # structures several sensels wide, because a wide structure looks the same
    # from both sites. Axial CA predicts the opposite dependence (a blur
    # difference bites hardest on the sharpest EDGES, which wide bright bars
    # also have) and election jitter predicts no width dependence at all.
    from scipy.ndimage import distance_transform_edt
    G = m[:, :, 1]
    hp_g = G - uniform_filter(G, 25)
    s_g = hp_g[hp_g > 0].std()
    bright = hp_g > 3.0 * s_g
    # local half-width of the bright structure at each ridge pixel, in px
    width = 2.0 * distance_transform_edt(bright)
    w = width[ridge]
    print(f"   chroma by structure width (CFA co-siting predicts 1/width):")
    wb = []
    for lo_w, hi_w in ((0, 2), (2, 3), (3, 4), (4, 6), (6, 1e9)):
        sel = (w >= lo_w) & (w < hi_w)
        if sel.sum() < 50:
            continue
        e = {"width_lo": lo_w, "width_hi": (None if hi_w > 1e8 else hi_w),
             "n": int(sel.sum()), "median_abs_chroma": float(np.median(v[sel]))}
        wb.append(e)
        hw = "inf" if hi_w > 1e8 else f"{hi_w}"
        print(f"     width {lo_w}-{hw:>3} px   n {e['n']:7d}   "
              f"|chroma| {e['median_abs_chroma']:.4f}")
    res["chroma_by_width"] = wb
    if len(wb) >= 2:
        res["chroma_ratio_thinnest_over_widest"] = float(
            wb[0]["median_abs_chroma"] / max(wb[-1]["median_abs_chroma"], 1e-9))
        print(f"   thinnest / widest chroma ratio: "
              f"{res['chroma_ratio_thinnest_over_widest']:.2f}x")
    return res


if __name__ == "__main__":
    o = run()
    dump("b9_election", o)
