"""M87 step 60 -- two populations of island, and the instrument in a white field.

ANSWERS TWO THINGS.

(A) ARE THE ISLANDS REACHABLE? ORCH's reading was that they sit "in places the
    background cannot physically reach". 58 found all 3 decidable islands at
    SUBJECT depth, which rules out the election importing a distant background,
    and it also showed the largest island is a real hole through the plant with
    filaments crossing it. So the question becomes geometric: how far is each
    island from the background it supposedly cannot come from?
      d2bg  Euclidean distance from the island to the nearest pixel of the
            border-connected background component.
    A severed veil is a contiguous bright band cut by a thin dark filament, so
    it will sit a FEW pixels from the background. A genuine gap through the
    plant is background seen through a hole and can be arbitrarily deep.
    BRIDGING confirms the first case causally rather than by distance alone:
    close the bright mask by rho, which fills dark gaps narrower than 2*rho,
    and see how much island area is absorbed into the background component.

    REGISTERED, before running:
      B1  The island population is BIMODAL in d2bg, not unimodal.
      B2  Most island COUNT is absorbed into the background by a closing of
          rho <= 8 binned px, i.e. severed by thin structure.
      B3  BROKEN ARM, registered as such. Discs of matched area dropped at
          deep-subject sites must NOT be absorbed at rho <= 8. If they are,
          the closing is absorbing everything and B2 means nothing.

(B) ORCH's CAUTION 4: does my fidelity instrument misbehave against a large
    near-clipping white field? Two ways it could:
      - clipping flattens the background, so a fine-band energy goes to zero
        and any normalised contrast ratio becomes 0/0;
      - the background dominates the frame by area and swamps the subject.
    Measured on the EXPOSED tif, because gallery.py writes the judged
    -100pct.png from `out`, the exposure-boosted array, NOT from -srgb.tif.
    My first pass in 57 read -srgb.tif and reported 0.000% near-clipping; that
    answered the question against an image nobody judged, which is the exact
    failure ORCH recorded as fact 1324. The exposed arm is boosted until it
    hits CLIP_BUDGET = 0.5%, so it is clipped BY CONSTRUCTION.
"""

import json
import pathlib

import numpy as np
import tifffile
from scipy import ndimage as ndi

CACHE = pathlib.Path(__file__).resolve().parents[1] / "cache"
DATA = pathlib.Path(__file__).resolve().parents[1] / "data"
GAL = pathlib.Path(r"C:\dev\strehl-out\ORCH-gallery")

RHOS = [1, 2, 3, 4, 6, 8, 12, 20, 40]
DEEP = 30
FINE = (1.0, 3.0)
COARSE = (8.0, 32.0)
RNG = np.random.default_rng(6001)


def otsu(v):
    h, e = np.histogram(v.ravel(), 512)
    h = h.astype(np.float64)
    c, m = h.cumsum(), (h * ((e[:-1] + e[1:]) / 2)).cumsum()
    tot, mt = c[-1], m[-1]
    with np.errstate(invalid="ignore", divide="ignore"):
        sb = (mt * c / tot - m) ** 2 / (c * (tot - c))
    return float(e[1:][np.nanargmax(sb)])


def decompose(lum):
    tau = otsu(lum)
    bright = lum > tau
    lab, _ = ndi.label(bright)
    b = set(np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]])))
    b.discard(0)
    bg = np.isin(lab, list(b))
    return tau, bright, bg, bright & ~bg


def dog(x, lo, hi):
    return ndi.gaussian_filter(x, lo) - ndi.gaussian_filter(x, hi)


def close_disc(mask, r):
    """Binary closing by a disc, via the EDT identity (fast at large r)."""
    dil = ndi.distance_transform_edt(~mask) <= r
    return ndi.distance_transform_edt(dil) > r


def absorbed(bright, bg, island, ilab, ni, rho):
    """Island area and count that joins the border component after closing."""
    cl = close_disc(bright, rho)
    lab, _ = ndi.label(cl)
    b = set(np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]])))
    b.discard(0)
    newbg = np.isin(lab, list(b))
    hit = ndi.maximum(newbg.astype(np.uint8), ilab, range(1, ni + 1))
    ar = ndi.sum(island, ilab, range(1, ni + 1))
    joined = np.asarray(hit) > 0
    ar = np.asarray(ar)
    return float(joined.mean()), float(ar[joined].sum() / max(ar.sum(), 1e-9))


def main():
    res = {}
    sel = np.load(CACHE / "25-flower-alone-sel.npy").astype(np.float32)
    tau, bright, bg, island = decompose(sel)
    ilab, ni = ndi.label(island)
    areas = np.asarray(ndi.sum(island, ilab, range(1, ni + 1)))
    d2bg = ndi.distance_transform_edt(~bg)
    dmin = np.asarray(ndi.minimum(d2bg, ilab, range(1, ni + 1)))
    print(f"binned {sel.shape}  {ni} islands  total area {int(areas.sum())} px")

    print("\n=== B1: is d2bg bimodal? ===")
    edges = [0, 2, 4, 8, 16, 30, 60, 120, 250, 1e9]
    for i in range(len(edges) - 1):
        m = (dmin >= edges[i]) & (dmin < edges[i + 1])
        if m.sum():
            print(f"  d2bg {edges[i]:>5.0f}-{edges[i + 1]:>5.0f} px : "
                  f"{m.sum():>4} islands, {int(areas[m].sum()):>7} px "
                  f"({100 * areas[m].sum() / areas.sum():5.1f}% of island area)")
    shallow, deep = dmin < DEEP, dmin >= DEEP
    print(f"\n  SHALLOW (<{DEEP} px): {shallow.sum():>4} islands, "
          f"{100 * areas[shallow].sum() / areas.sum():5.1f}% of island area")
    print(f"  DEEP    (>={DEEP} px): {deep.sum():>4} islands, "
          f"{100 * areas[deep].sum() / areas.sum():5.1f}% of island area")
    gap = (dmin >= 8) & (dmin < 30)
    b1 = gap.sum() < 0.15 * ni and deep.sum() > 0 and shallow.sum() > 0
    print(f"  8-30 px trough holds {gap.sum()} islands ({100 * gap.sum() / ni:.1f}%)"
          f"   B1 bimodal: {'PASS' if b1 else 'FAIL'}")
    res["B1_bimodal"] = bool(b1)
    res["n_islands"] = int(ni)
    res["shallow"] = {"n": int(shallow.sum()),
                      "area_frac": float(areas[shallow].sum() / areas.sum())}
    res["deep"] = {"n": int(deep.sum()),
                   "area_frac": float(areas[deep].sum() / areas.sum())}

    print("\n=== B2/B3: bridging by a closing of radius rho ===")
    dbr = ndi.distance_transform_edt(~bright)
    ctrl = np.zeros_like(island)
    ys, xs = np.where(~bright & (dbr > 60))
    for _ in range(min(60, len(ys))):
        j = RNG.integers(len(ys))
        a = float(RNG.choice(areas))
        r = max(int(round(np.sqrt(a / np.pi))), 3)
        cy, cx = int(ys[j]), int(xs[j])
        y0, y1 = max(cy - r, 0), min(cy + r + 1, sel.shape[0])
        x0, x1 = max(cx - r, 0), min(cx + r + 1, sel.shape[1])
        gy, gx = np.ogrid[y0:y1, x0:x1]
        ctrl[y0:y1, x0:x1] |= ((gy - cy) ** 2 + (gx - cx) ** 2) <= r * r
    clab, cn = ndi.label(ctrl)
    print(f"  broken arm: {cn} matched discs planted in deep subject (>60 px)")
    print(f"  {'rho':>4} {'islands joined':>15} {'island area':>12}"
          f" {'CTRL joined':>12}")
    rows = []
    for rho in RHOS:
        jc, ja = absorbed(bright, bg, island, ilab, ni, rho)
        cc, _ = absorbed(bright | ctrl, bg, ctrl, clab, cn, rho)
        rows.append({"rho": rho, "count": jc, "area": ja, "ctrl": cc})
        print(f"  {rho:>4} {100 * jc:>14.1f}% {100 * ja:>11.1f}%"
              f" {100 * cc:>11.1f}%")
    res["bridging"] = rows
    at8 = [r for r in rows if r["rho"] == 8][0]
    b2 = at8["count"] >= 0.5
    b3 = at8["ctrl"] < 0.2
    print(f"  B2 majority of islands bridged by rho<=8: "
          f"{100 * at8['count']:.1f}%  {'PASS' if b2 else 'FAIL'}")
    print(f"  B3 broken arm stays unbridged at rho=8:   "
          f"{100 * at8['ctrl']:.1f}%  {'PASS' if b3 else 'FAIL'}")
    res["B2_pass"], res["B3_pass"] = bool(b2), bool(b3)

    print("\n=== (B) ORCH caution 4: the instrument in a white field ===")
    for name in ("srgb", "exposed"):
        img = tifffile.imread(GAL / f"flower-bud-alone-cpl-{name}.tif")
        a = img.astype(np.float32) / 65535.0
        lum = 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]
        # gallery.py budgets clipping on the PER-CHANNEL max, not on luma, so a
        # luma test understates it: a pixel can peg one channel and still read
        # a luma well below 1.
        chmax = a.max(axis=2)
        del img, a
        hard = float((chmax >= 1.0 - 1e-6).mean())
        near = float((chmax >= 0.99).mean())
        t2, br2, bg2, is2 = decompose(lum)
        f = dog(lum, *FINE)
        c = dog(lum, *COARSE)
        fb = float(np.sqrt((f[bg2] ** 2).mean()))
        fs = float(np.sqrt((f[~br2] ** 2).mean()))
        cb = float(np.sqrt((c[bg2] ** 2).mean()))
        cs = float(np.sqrt((c[~br2] ** 2).mean()))
        print(f"  {name:<8} clipped {100 * hard:7.4f}%  >=0.99 {100 * near:7.4f}%"
              f"  tau {t2:.4f}  bright {100 * br2.mean():5.2f}%"
              f"  islands {100 * is2.mean():.3f}%")
        print(f"           FINE rms  bg {fb:.6f}  subj {fs:.6f}   "
              f"COARSE rms  bg {cb:.6f}  subj {cs:.6f}")
        res[name] = {"clipped": hard, "near99": near, "tau": t2,
                     "bright_frac": float(br2.mean()),
                     "island_frac": float(is2.mean()),
                     "fine_bg": fb, "fine_subj": fs,
                     "coarse_bg": cb, "coarse_subj": cs}
    degen = res["exposed"]["fine_bg"] < 1e-4
    print(f"\n  background FINE-band energy degenerate (<1e-4): "
          f"{'YES -- ratio unusable' if degen else 'NO -- instrument reads it'}")
    res["fine_band_degenerate"] = bool(degen)

    json.dump(res, open(DATA / "60-islands-2pop.json", "w"), indent=1)
    print(f"\nwrote {DATA / '60-islands-2pop.json'}")


if __name__ == "__main__":
    main()
