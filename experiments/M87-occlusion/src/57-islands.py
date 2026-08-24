"""M87 step 57 -- are the detached white islands the same defect as the veil?

ORCH's question, and it matters before any fix is scored: a veil is a two-layer
composite at an occluding boundary; hard-edged islands tens of pixels across
INSIDE the subject look more like an election pathology in a texture-free cell.
If they are two mechanisms, a correction tuned on the veil will not touch the
islands, and a metric that averages both will hide that.

I opened `flower-bud-alone-cpl-100pct.png` myself first. Confirmed by eye: a
thick white veil wrapping the silhouette, a clearly LOBED boundary, and several
hard-edged white blobs well inside the green bud, many of them sitting beside
the thin brown filaments.

TWO ARMS, DELIBERATELY, because they answer different questions:
  APPEARANCE  measured on the GALLERY TIFF -- the image actually judged. ORCH
              nearly shipped a fix that never reached the judged image
              (fact 1324), so geometry is measured on that render, not on a
              convenient cache.
  MECHANISM   measured on my cached full-frame `argbest`, the elected frame
              index per pixel, which the gallery render does not carry. The
              cross-check is that the island geometry must agree between arms.

REGION DEFINITIONS, needing no ground truth:
  BG_FAR  bright, connected to the image border, >200 px from the subject
  VEIL    bright, connected to the border, within 40 px of the subject
  ISLAND  bright, NOT connected to the border -- fully enclosed by subject
  SUBJ    not bright, >60 px from any bright pixel
"Connected to the border" is what makes ISLAND well posed without truth.

REGISTERED PREDICTIONS, written before the script was run:
  P-A  If islands are a background-frame election, their elected index will sit
       with BG_FAR's and far from SUBJ's: |median(ISLAND) - median(BG_FAR)|
       will be small next to |median(SUBJ) - median(BG_FAR)|.
  P-B  If instead islands are noise-driven election in texture-free cells, the
       elected index inside an island will be INCOHERENT -- a high local spread
       -- whereas a genuine background election is coherent, like BG_FAR's.
  P-C  The scallop lobe scale will land on a pipeline lengthscale, not on an
       arbitrary one. Candidates: regulariser radius 8 (dia 17), focus window
       radius 13 (dia 27), their sum 21 (dia 43).
  These can disagree, and P-A and P-B can BOTH fail, which is what makes it a
  test rather than a demonstration.

16-bit TIFF is read with tifffile, never PIL (fact P40).
"""

import json
import pathlib

import numpy as np
import tifffile
from scipy import ndimage as ndi

GAL = pathlib.Path(r"C:\dev\strehl-out\ORCH-gallery")
OUTDIR = pathlib.Path(r"C:\dev\strehl-out\M87-islands")
CACHE = pathlib.Path(__file__).resolve().parents[1] / "cache"
DATA = pathlib.Path(__file__).resolve().parents[1] / "data"

NEAR_VEIL = 40
FAR_BG = 200
DEEP_SUBJ = 60
RADII = [2, 4, 6, 8, 10, 13, 16, 21, 27, 34, 43, 55]


def luma(a):
    a = a.astype(np.float32)
    if a.ndim == 3:
        a = 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]
    return a


def otsu(v):
    h, e = np.histogram(v.ravel(), 512)
    h = h.astype(np.float64)
    c = h.cumsum()
    m = (h * ((e[:-1] + e[1:]) / 2)).cumsum()
    tot, mt = c[-1], m[-1]
    with np.errstate(invalid="ignore", divide="ignore"):
        sb = (mt * c / tot - m) ** 2 / (c * (tot - c))
    return float(e[1:][np.nanargmax(sb)])


def regions(lum, tau=None):
    """Bright/subject decomposition that needs no ground truth."""
    tau = otsu(lum) if tau is None else tau
    bright = lum > tau
    lab, n = ndi.label(bright)
    border = set(np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]])))
    border.discard(0)
    bg = np.isin(lab, list(border))
    island = bright & ~bg
    subject = ~bright
    d_sub = ndi.distance_transform_edt(~subject)
    d_bright = ndi.distance_transform_edt(~bright)
    return {"tau": tau, "bright": bright, "bg": bg, "island": island,
            "veil": bg & (d_sub <= NEAR_VEIL),
            "bg_far": bg & (d_sub > FAR_BG),
            "subj": subject & (d_bright > DEEP_SUBJ)}


def granulometry(mask):
    """Pattern spectrum of the mask's protrusions.

    A disc opening deletes every protrusion narrower than 2r while leaving the
    body untouched, so the AREA REMOVED as a function of r isolates the lobes:
    the body contributes nothing to the derivative. The peak of dA/dr is the
    characteristic protrusion width.

    Computed through the distance transform rather than by convolving discs --
    binary_opening with an r=55 disc is ~1e4 ops per pixel over 33 Mpx and will
    not finish. open(M, disc_r) == dilate(erode(M, disc_r), disc_r), and both
    are EDT thresholds: erode == {d_in >= r}, dilate == {d_out <= r}.
    """
    base = float(mask.sum())
    d_in = ndi.distance_transform_edt(mask)
    out = []
    prev = 1.0
    for r in RADII:
        # STRICT >. A closed disc of radius r centred at c lies inside the mask
        # only when the nearest background is STRICTLY further than r; using
        # >= admits centres whose nearest background sits at exactly r, and on
        # an integer grid exact ties are common, so the dilation then leaks
        # background pixels back in and the opening reports kept > 100%, which
        # is impossible. Caught by that impossible value, not by inspection.
        er = d_in > r
        op = ndi.distance_transform_edt(~er) <= r if er.any() else er
        kept = op.sum() / max(base, 1.0)
        out.append({"r": r, "kept": float(kept),
                    "removed_rate": float((prev - kept) / r)})
        prev = kept
    return out


def main():
    OUTDIR.mkdir(parents=True, exist_ok=True)
    res = {}

    # ---------------- ARM 1: APPEARANCE, on the judged render ----------------
    tif = GAL / "flower-bud-alone-cpl-srgb.tif"
    img = tifffile.imread(tif)
    lum = luma(img)
    print(f"gallery render {img.shape} {img.dtype}")
    clip = float((lum >= 0.999 * float(lum.max())).mean())
    print(f"  near-clipping fraction: {100 * clip:.3f}%  (ORCH's caution 4)")
    R = regions(lum)
    n_lab, n_iso = ndi.label(R["island"])
    sizes = ndi.sum(R["island"], n_lab, range(1, n_iso + 1))
    big = sizes[sizes >= 100]
    print(f"  otsu tau {R['tau']:.1f}")
    for k in ("bright", "bg", "island", "veil", "bg_far", "subj"):
        print(f"  {k:<8} {100 * R[k].mean():7.3f}% of frame")
    print(f"  islands: {n_iso} components, {len(big)} with area >= 100 px, "
          f"median area {np.median(big) if len(big) else 0:.0f} px, "
          f"max {sizes.max() if n_iso else 0:.0f} px")
    res["appearance"] = {
        "shape": list(img.shape), "tau": R["tau"], "clip_frac": clip,
        "fracs": {k: float(R[k].mean()) for k in
                  ("bright", "bg", "island", "veil", "bg_far", "subj")},
        "n_islands": int(n_iso), "n_islands_ge100": int(len(big)),
        "median_island_area": float(np.median(big)) if len(big) else 0.0,
        "max_island_area": float(sizes.max()) if n_iso else 0.0}

    print("\n--- P-C: lobe scale of the veil boundary (granulometry) ---")
    # Restrict to the subject's bounding box: the veil is local, and a whole-frame
    # EDT ladder over 33 Mpx buys nothing but runtime.
    ys, xs = np.where(~R["bright"])
    y0, y1 = max(int(ys.min()) - 300, 0), min(int(ys.max()) + 300, lum.shape[0])
    x0, x1 = max(int(xs.min()) - 300, 0), min(int(xs.max()) + 300, lum.shape[1])
    print(f"  subject bbox y{y0}..{y1} x{x0}..{x1}")
    g = granulometry(R["veil"][y0:y1, x0:x1])
    res["granulometry_veil"] = g
    res["bbox"] = [y0, y1, x0, x1]
    for row in g:
        print(f"  r={row['r']:>3}  kept {100 * row['kept']:6.2f}%"
              f"  removed/px {100 * row['removed_rate']:6.3f}")
    peak = max(g, key=lambda z: z["removed_rate"])
    res["veil_lobe_peak_r"] = peak["r"]
    halves = [row["r"] for row in g if row["kept"] < 0.5]
    res["veil_half_radius"] = halves[0] if halves else None
    print(f"  peak removal rate at r={peak['r']} (width {2 * peak['r']} px);"
          f" half-loss radius {res['veil_half_radius']}")

    # ---------------- ARM 2: MECHANISM, on the cached argbest ----------------
    print("\n=== MECHANISM: elected frame index per region ===")
    sel = np.load(CACHE / "25-flower-alone-sel.npy")
    arg = np.load(CACHE / "25-flower-alone-argbest.npy").astype(np.int32)
    print(f"cached merge {sel.shape}, argbest range {arg.min()}..{arg.max()}")
    Rc = regions(sel.astype(np.float32))
    for k in ("island", "veil", "bg_far", "subj"):
        print(f"  {k:<8} {100 * Rc[k].mean():7.3f}% of cached frame")

    # local incoherence of the elected index: sd within a 9x9 window
    a = arg.astype(np.float32)
    m1 = ndi.uniform_filter(a, 9)
    m2 = ndi.uniform_filter(a * a, 9)
    inc = np.sqrt(np.maximum(m2 - m1 * m1, 0.0))

    stats = {}
    for k in ("island", "veil", "bg_far", "subj"):
        m = Rc[k]
        if m.sum() < 50:
            print(f"  {k}: too few pixels ({m.sum()})")
            continue
        stats[k] = {"n": int(m.sum()), "median_idx": float(np.median(arg[m])),
                    "p10_idx": float(np.percentile(arg[m], 10)),
                    "p90_idx": float(np.percentile(arg[m], 90)),
                    "median_incoherence": float(np.median(inc[m]))}
        s = stats[k]
        print(f"  {k:<8} n={s['n']:>9}  elected idx median {s['median_idx']:6.1f}"
              f"  p10-p90 {s['p10_idx']:.0f}-{s['p90_idx']:.0f}"
              f"  local sd {s['median_incoherence']:6.2f}")
    res["mechanism"] = stats

    if {"island", "bg_far", "subj"} <= stats.keys():
        d_ib = abs(stats["island"]["median_idx"] - stats["bg_far"]["median_idx"])
        d_sb = abs(stats["subj"]["median_idx"] - stats["bg_far"]["median_idx"])
        pa = d_ib < 0.5 * d_sb
        pb = stats["island"]["median_incoherence"] > \
            2.0 * stats["bg_far"]["median_incoherence"]
        res["P_A_island_elects_like_background"] = bool(pa)
        res["P_B_island_election_incoherent"] = bool(pb)
        res["d_island_bg"] = d_ib
        res["d_subj_bg"] = d_sb
        print(f"\nP-A  islands elect like the background : "
              f"{'YES' if pa else 'NO'}  (|isl-bg| {d_ib:.1f} vs |subj-bg| {d_sb:.1f})")
        print(f"P-B  island election is incoherent     : "
              f"{'YES' if pb else 'NO'}  (local sd {stats['island']['median_incoherence']:.2f}"
              f" vs bg {stats['bg_far']['median_incoherence']:.2f})")
        print("\n  !! P-A is scored against GLOBAL medians and the elected index")
        print("     is a function of depth, hence of position. A global median is")
        print("     the wrong reference. Superseded by the per-island local test")
        print("     in 58-island-depth.py; do not read P-A's verdict as evidence.")
        res["P_A_SUPERSEDED"] = "global reference invalid; see 58-island-depth.py"

    # also measure the lobe scale on the BINNED grid, where the pipeline's own
    # lengthscales (WINDOW_RADIUS 13, REGULARISER_RADIUS 8) natively live --
    # the render is ~2x that grid, so a radius read there is not comparable.
    ys, xs = np.where(~Rc["bright"])
    cy0, cy1 = max(int(ys.min()) - 150, 0), min(int(ys.max()) + 150, sel.shape[0])
    cx0, cx1 = max(int(xs.min()) - 150, 0), min(int(xs.max()) + 150, sel.shape[1])
    gb = granulometry(Rc["veil"][cy0:cy1, cx0:cx1])
    res["granulometry_veil_binned"] = gb
    print("\n--- P-C on the BINNED grid (native pipeline units) ---")
    for row in gb:
        print(f"  r={row['r']:>3}  kept {100 * row['kept']:6.2f}%"
              f"  removed/px {100 * row['removed_rate']:6.3f}")
    pkb = max(gb, key=lambda z: z["removed_rate"])
    hb = [row["r"] for row in gb if row["kept"] < 0.5]
    res["veil_lobe_peak_r_binned"] = pkb["r"]
    res["veil_half_radius_binned"] = hb[0] if hb else None
    print(f"  peak removal at r={pkb['r']} binned px; half-loss r={res['veil_half_radius_binned']}")

    json.dump(res, open(DATA / "57-islands.json", "w"), indent=1)
    print(f"\nwrote {DATA / '57-islands.json'}")


if __name__ == "__main__":
    main()
