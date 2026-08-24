"""M87 s31c -- what ORCH's banding actually is, against the election field.

PROVENANCE.  s31-bee3.tif was rendered by me from D:\\personal\\macro\\bee-3-cpl
at the shipped default gate with STREHL_WARPMAP pinned to my own sidecar, and
is SHA-256 IDENTICAL to ORCH's C:\\dev\\strehl-out\\ORCH-gallery3\\bee-3-cpl.tif.
So s31-index.tif and s31-neff.tif are the election and n_eff fields OF THE
FIGURE ORCH SENT, not of a similar render.  That equality is checked here.

WHAT 84 AND 86 ALREADY SETTLED.
  - one output code of ORCH's diagnostic stretch is 115.7 DN
  - far background noise sd 22.2 DN  -> code/noise 5.20x -> bands must form
  - pocket noise sd     160.1 DN     -> code/noise 0.72x -> bands cannot form
  - dithering before the cast removes far-field transitions (1.8x) and does
    nothing in the pocket (1.0x)
  - the high-pass of the 16-BIT data, at +/-480 DN and before any cast, still
    shows concentric arcs near the claw
So there are TWO different things in that figure and they are in different
places.  This script asks what the second one is.

THE PREDICTION, WITH NO FREE PARAMETER.  Pass two averages n_eff frames per
pixel.  If the noise field is nothing but un-averaged pixels, then

        noise_sd(x) * sqrt(n_eff(x))  =  constant
        d log10 noise / d log10 n_eff = -0.5   EXACTLY

That is a slope, not a correlation, and it is fixed by arithmetic rather than
fitted.  The first check of it is already on the table: 84 measured a
pocket/far noise ratio of 7.2x, which predicts an n_eff ratio of 52, and the
run printed mean n_eff 55.321 before I looked.

BARS, THREE BRANCHES EACH (discipline 676).

  B5 SQRT-N.   slope in [-0.60, -0.40] -> AVERAGING EXPLAINS THE NOISE FIELD
               slope > -0.20           -> IT DOES NOT
               otherwise               -> PARTIAL

  B6 CONTOUR.  enrichment = median |high-pass| on election boundaries divided
               by the same off boundaries, BACKGROUND PIXELS ONLY.
               >= 1.5 -> the arcs are election contours
               <= 1.1 -> they are not
               otherwise -> WEAK
               Null control: the same statistic against a 180-degree-rotated
               election map, which has identical marginal statistics and no
               registration to the render.  Must land near 1.0.

  B7 STEP SIZE. the median |high-pass| on background election boundaries, in
               DN, against the 115.7 DN quantum of ORCH's display cast.  This
               decides whether the real steps are even visible in that figure
               or whether the eye was reading posterisation the whole time.
               >= 115.7 -> visible in the figure on their own
               <= 38.6  -> at most a third of one code, invisible
               otherwise -> MARGINAL
"""
import hashlib
import json
import pathlib
import sys

import numpy as np
import tifffile
from scipy import ndimage
from PIL import Image

SCRATCH = pathlib.Path(r"C:\dev\strehl-out\M87-bee")
ORCH_TIF = pathlib.Path(r"C:\dev\strehl-out\ORCH-gallery3\bee-3-cpl.tif")
MINE = SCRATCH / "s31-bee3.tif"
IDX = SCRATCH / "s31-index.tif"
NEFF = SCRATCH / "s31-neff.tif"
DATA = pathlib.Path(__file__).resolve().parents[1] / "data"

X0, Y0, W, H = 700, 3150, 1100, 900
DN_PER_CODE = 115.7          # measured in 84-banding.py, re-derived below
B5_LO, B5_HI, B5_NONE = -0.60, -0.40, -0.20
B6_YES, B6_NO = 1.5, 1.1
B7_VISIBLE, B7_INVISIBLE = DN_PER_CODE, DN_PER_CODE / 3.0


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def main():
    out = {}
    print("=== provenance ===")
    a_mine, a_orch = sha256(MINE), sha256(ORCH_TIF)
    print(f"  mine {a_mine[:24]}\n  orch {a_orch[:24]}")
    assert a_mine == a_orch, "my render is not ORCH's figure; maps do not apply"
    print("  IDENTICAL -- the maps below are the election field OF ORCH'S FIGURE")
    out["sha_render"] = a_mine

    g = tifffile.imread(MINE)[Y0:Y0 + H, X0:X0 + W, 1].astype(np.float32)
    # plane grid is half resolution; scale by two to overlay a --demosaic render
    py0, px0, ph, pw = Y0 // 2, X0 // 2, H // 2, W // 2
    idx = tifffile.imread(IDX)[py0:py0 + ph, px0:px0 + pw].astype(np.float32)
    nef = tifffile.imread(NEFF)[py0:py0 + ph, px0:px0 + pw].astype(np.float32)
    idx = np.repeat(np.repeat(idx, 2, 0), 2, 1)
    nef = np.repeat(np.repeat(nef, 2, 0), 2, 1)
    assert idx.shape == g.shape == nef.shape, (idx.shape, g.shape, nef.shape)
    print(f"  crop {g.shape}  n_eff {nef.min():.0f}..{nef.max():.0f}"
          f" mean {nef.mean():.1f};  index {idx.min():.0f}..{idx.max():.0f}")

    lo, hi = float(np.percentile(g, 1)), float(np.percentile(g, 99))
    med = float(np.median(g))
    span = max(hi - lo, 1.0) * 0.35
    dn_code = span / 127.0
    assert abs(dn_code - DN_PER_CODE) < 0.5, dn_code
    out["dn_per_code"] = dn_code

    subj = ndimage.binary_opening(
        ndimage.binary_closing(g < med - span, np.ones((5, 5))), np.ones((3, 3)))
    bg = ~ndimage.binary_dilation(subj, np.ones((9, 9)))
    print(f"  background pixels {int(bg.sum())} ({100*bg.mean():.1f}% of crop)")
    out["bg_frac"] = float(bg.mean())

    hp = g - ndimage.median_filter(g, size=5)

    # ---------------- B5: does averaging explain the noise field? --------
    print("\n=== B5  noise_sd * sqrt(n_eff) = constant? ===")
    k = 15
    m = bg.astype(np.float32)
    cnt = ndimage.uniform_filter(m, k)
    s1 = ndimage.uniform_filter(hp * m, k)
    s2 = ndimage.uniform_filter(hp * hp * m, k)
    ok = cnt > 0.95
    var = np.where(ok, s2 / np.maximum(cnt, 1e-6) -
                   (s1 / np.maximum(cnt, 1e-6)) ** 2, np.nan)
    nz = np.sqrt(np.maximum(var, 0.0))
    ne = ndimage.uniform_filter(nef * m, k) / np.maximum(cnt, 1e-6)

    sel = ok & bg & np.isfinite(nz) & (nz > 0) & (ne >= 1.0)
    xs, ys = np.log10(ne[sel]), np.log10(nz[sel])
    print(f"  {int(sel.sum())} windows;  n_eff {10**xs.min():.1f}..{10**xs.max():.0f}")
    edges = np.percentile(xs, np.linspace(0, 100, 13))
    bx, by, bn = [], [], []
    for i in range(len(edges) - 1):
        b = (xs >= edges[i]) & (xs < edges[i + 1] if i < len(edges) - 2
                                else xs <= edges[i + 1])
        if b.sum() >= 200:
            bx.append(float(np.median(xs[b])))
            by.append(float(np.median(ys[b])))
            bn.append(int(b.sum()))
    print(f"  {'n_eff':>9} {'noise DN':>10} {'n_win':>8}")
    for X, Y, N in zip(bx, by, bn):
        print(f"  {10**X:9.1f} {10**Y:10.1f} {N:8d}")
    slope, icept = np.polyfit(bx, by, 1)
    pred = 10 ** icept
    print(f"  slope {slope:+.4f}   (predicted exactly -0.5000,"
          f" no free parameter)")
    print(f"  implied single-frame noise {pred:.1f} DN at n_eff = 1")
    b5 = ("AVERAGING EXPLAINS THE NOISE FIELD" if B5_LO <= slope <= B5_HI
          else "IT DOES NOT" if slope > B5_NONE else "PARTIAL")
    print(f"  B5: {b5}")
    out["B5"] = {"slope": float(slope), "intercept_dn": float(pred),
                 "bins": [[float(a), float(b), int(c)] for a, b, c in
                          zip(bx, by, bn)], "branch": b5}

    # ---------------- B6/B7: are the arcs election contours? -------------
    print("\n=== B6  are the real steps on election boundaries? ===")

    def enrich(field, tag):
        gy, gx = np.gradient(field)
        bnd = (np.abs(gy) + np.abs(gx)) > 0.5
        bnd = ndimage.binary_dilation(bnd, np.ones((3, 3))) & bg
        off = bg & ~ndimage.binary_dilation(bnd, np.ones((7, 7)))
        a = float(np.median(np.abs(hp[bnd]))) if bnd.sum() > 500 else np.nan
        b = float(np.median(np.abs(hp[off]))) if off.sum() > 500 else np.nan
        print(f"  {tag:18s} on {a:7.1f} DN ({int(bnd.sum()):7d} px)"
              f"   off {b:7.1f} DN ({int(off.sum()):7d} px)"
              f"   enrichment {a/b:5.2f}x")
        return a, b, a / b, int(bnd.sum())

    on_i, off_i, e_i, n_i = enrich(idx, "election index")
    on_n, off_n, e_n, _ = enrich(nef, "n_eff")
    on_r, off_r, e_r, _ = enrich(idx[::-1, ::-1].copy(), "NULL rot180 index")

    b6 = ("the arcs are election contours" if e_i >= B6_YES
          else "they are not" if e_i <= B6_NO else "WEAK")
    print(f"  B6: {b6}   (null control {e_r:.2f}x, must be near 1.0)")
    out["B6"] = {"index_on": on_i, "index_off": off_i, "index_enrich": e_i,
                 "neff_enrich": e_n, "null_enrich": e_r,
                 "boundary_px": n_i, "branch": b6}

    print("\n=== B7  are those steps visible in ORCH's own figure? ===")
    print(f"  median |step| on election boundaries {on_i:.1f} DN")
    print(f"  one output code of the diagnostic cast {dn_code:.1f} DN")
    print(f"  ratio {on_i/dn_code:.3f} codes")
    b7 = ("visible on their own" if on_i >= B7_VISIBLE
          else "invisible in that figure" if on_i <= B7_INVISIBLE
          else "MARGINAL")
    print(f"  B7: {b7}")
    out["B7"] = {"step_dn": on_i, "codes": on_i / dn_code, "branch": b7}

    # ---------------- the map (discipline 677) ---------------------------
    zy0, zy1, zx0, zx1 = 550, 900, 600, 1100
    z = g[zy0:zy1, zx0:zx1]
    zi = idx[zy0:zy1, zx0:zx1]
    zn = nef[zy0:zy1, zx0:zx1]
    zh = hp[zy0:zy1, zx0:zx1]
    sd = float(1.4826 * np.median(np.abs(zh - np.median(zh))))

    def u8(x, c, s):
        return np.clip((x - c) / s * 127.0 + 127.0, 0, 255).astype(np.uint8)

    pa = u8(z, med, span)
    pn = np.clip(np.log10(np.maximum(zn, 1)) / np.log10(299.0) * 255,
                 0, 255).astype(np.uint8)
    pi = np.clip(zi / 298.0 * 255, 0, 255).astype(np.uint8)
    ph_ = u8(zh, 0.0, 4.0 * sd)
    gy, gx = np.gradient(zi)
    bnd = ndimage.binary_dilation((np.abs(gy) + np.abs(gx)) > 0.5,
                                  np.ones((2, 2)))
    ov = np.dstack([ph_, ph_, ph_])
    ov[bnd] = (255, 40, 40)

    lab = [("A render", np.dstack([pa] * 3)),
           ("B n_eff (log)", np.dstack([pn] * 3)),
           ("C election index", np.dstack([pi] * 3)),
           (f"D high pass +/-{4*sd:.0f} DN, election boundaries in red", ov)]
    hh, ww = z.shape
    canvas = np.zeros((2 * hh + 6, 2 * ww + 6, 3), np.uint8)
    for i, (_, im_) in enumerate(lab):
        r, c = divmod(i, 2)
        canvas[r * (hh + 6):r * (hh + 6) + hh, c * (ww + 6):c * (ww + 6) + ww] = im_
    Image.fromarray(canvas).resize((canvas.shape[1] * 2, canvas.shape[0] * 2),
                                   Image.NEAREST).save(SCRATCH / "ELECTION-MAP.png")
    print(f"\n=== map, 2x nearest, zoom y {zy0}:{zy1} x {zx0}:{zx1} ===")
    for t, _ in lab:
        print(f"  {t}")
    print(f"  wrote {SCRATCH / 'ELECTION-MAP.png'}")

    DATA.mkdir(exist_ok=True)
    (DATA / "87-election.json").write_text(
        json.dumps(out, indent=1, default=float), encoding="utf-8")
    print(f"wrote {DATA / '87-election.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
