"""geomcrop.py -- joint scale+offset geometry, for subjects whose comparator
raster was cropped by align_image_stack -C.

WHY THIS EXISTS.  geom2.py uses V-HEADTOHEAD2/geom.py AS-IS, and geom.fit
correlates tiles taken at IDENTICAL GRID COORDINATES in the two rasters:

    peak(S[y:y+tile, x:x+tile], Cz[y:y+tile, x:x+tile])

That is correct only while the two images share an origin.  On `113MSDCF` and
`119MSDCF` they do -- MEASURED, the comparator raster is (4688, 7032), byte
for byte the same shape as strehl's -- and geom2.py fitted them cleanly, score
0.7686 at scale 1.004.

On `bee-1-cpl` align_image_stack -C cropped the aligned set to (4127, 6201)
against strehl's (4688, 7032).  The comparator is now a SUB-WINDOW of the
scene, so tile (y, x) in one raster is not tile (y, x) in the other, and the
fit collapsed: median tile peak 0.046-0.057 against 119's 0.77, with the sweep
rising monotonically to the edge of its range and no interior maximum.

THE FAILURE IS NOT A SCALE FAILURE.  `zoom(C, s)` scales about the ORIGIN, so
raising s translates content by up to s*width -- at s=1.03 that is 186 px on
bee, the same order as the ~415 px crop offset.  The sweep was therefore
buying offset compensation with scale and reporting the result as a
magnification.  An edge-running sweep is exactly what that aliasing looks
like, which is why geom2.py's "no interior maximum -> FAILED FIT" rule fired
correctly and must not be relaxed: the honest fix is to give the model the
freedom it was missing, not to widen the range until the alias peaks.

WHAT THIS DOES INSTEAD.  Scale and translation are estimated JOINTLY, and
translation is estimated by phase correlation, which is translation-invariant
by construction and so cannot be traded against scale:

    for each candidate scale s:
        zoom the comparator by s
        embed both images in one common canvas
        take ONE global phase correlation -> (dy, dx) and a peak height
    the fitted scale is the s whose peak height is greatest

The interior-maximum rule is retained unchanged.  The reported offset is a
MEASUREMENT, not a fitted nuisance parameter: it is read off the correlation
peak, never assumed to be the centred crop that the raster sizes imply.

COMMISSIONED, and against a planted transform rather than against agreement
with geom2.py -- agreeing with an instrument that failed proves nothing.  Arm
PLANT takes strehl's own image, applies a KNOWN scale and a KNOWN offset, and
requires this code to recover both.  Arm NULL feeds the image against itself
and requires scale 1.000 and offset (0, 0): a fitter that always returns the
centre of its sweep would pass PLANT-with-scale-1 trivially, so the planted
scale is deliberately not 1.

Usage:
    python geomcrop.py commission          # both arms, no subject needed
    python geomcrop.py <key> [<key> ...]   # fit and REWRITE <key>/geom.json
"""
import json
import os
import sys

import numpy as np
from scipy import ndimage

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, "..", "V-HEADTOHEAD2"))
import geom                                                       # noqa: E402

ROOT = r"C:\dev\strehl-out\V-NOISE2"
D = 8                       # analysis decimation, matching geom.fit's default
COARSE = np.arange(0.94, 1.0601, 0.005)
COMPARATORS = {
    "enfuse": ("coh-enfuse-A.tif",
               "Hugin align_image_stack + enfuse --hard-mask (GPL)"),
    "fs15-coh": ("coh-fs15-A.tif",
                 "focus-stack merge on Hugin-aligned frames (MIT)"),
}


def global_peak(S, C):
    """One phase correlation over a common canvas -> (peak, dy, dx) in /D px.

    Both images are embedded top-left in a canvas big enough for either, so
    the comparator's smaller raster is handled without resampling it.  The
    Hanning window is applied to the canvas, not to the payload, so the zero
    padding does not manufacture an edge that correlates with itself.
    """
    h = max(S.shape[0], C.shape[0])
    w = max(S.shape[1], C.shape[1])
    a = np.zeros((h, w), np.float64)
    b = np.zeros((h, w), np.float64)
    a[:S.shape[0], :S.shape[1]] = S - S.mean()
    b[:C.shape[0], :C.shape[1]] = C - C.mean()
    win = np.hanning(h)[:, None] * np.hanning(w)[None, :]
    A = np.fft.fft2(a * win)
    B = np.fft.fft2(b * win)
    R = A * np.conj(B)
    R /= np.abs(R) + 1e-30
    c = np.real(np.fft.ifft2(R))
    i = np.unravel_index(np.argmax(c), c.shape)
    dy = i[0] - (h if i[0] > h // 2 else 0)
    dx = i[1] - (w if i[1] > w // 2 else 0)
    return float(c[i]), int(dy), int(dx)


def fit_joint(S, C, scales, verbose=True):
    """(best_scale, score, interior, dy, dx, sweep) -- all offsets in SOURCE px."""
    sweep = []
    for s in scales:
        Cz = ndimage.zoom(C, s, order=3) if abs(s - 1.0) > 1e-9 else C
        p, dy, dx = global_peak(S, Cz)
        sweep.append((float(s), p, dy, dx))
        if verbose:
            print(f"    scale {s:.4f}: global peak {p:.5f}  "
                  f"offset dy {dy * D:+5d} dx {dx * D:+5d} px")
    best = max(sweep, key=lambda t: t[1])
    interior = sweep[0][1] < best[1] and sweep[-1][1] < best[1]
    return best[0], best[1], interior, best[2] * D, best[3] * D, sweep


def fit_tiles(S, C, scales, oy, ox, tile=128, ntile=6, verbose=True):
    """Median-over-tiles fit at a KNOWN coarse offset -- the robust estimator.

    The global correlation above is a single number over the whole frame, so
    every region where the two merges genuinely differ (and on a 299-frame
    deep stack they differ a great deal) enters the same statistic and buries
    the geometry.  MEASURED on bee: global peaks of 0.014-0.026 against this
    same code's 0.685 on a planted transform, a sweep that is not unimodal,
    and -- decisively -- scale 1.0250 for enfuse against 1.0150 for
    focus-stack, when BOTH are fused from ONE aligned set and therefore share
    a raster and a scale by construction.  Two different answers for one
    quantity is a failing instrument, not a measurement.

    So: correlate TILE BY TILE and take the MEDIAN peak, which is geom.fit's
    own robustness and is what scored 0.7686 on 119.  The crop is handled by
    taking the strehl tile at (y+oy, x+ox) against the comparator tile at
    (y, x); per-tile phase correlation is translation-invariant and absorbs
    the residual, which is then reported as the check.
    """
    sweep = []
    for s in scales:
        Cz = ndimage.zoom(C, s, order=3) if abs(s - 1.0) > 1e-9 else C
        ys = np.linspace(tile, Cz.shape[0] - 2 * tile, ntile).astype(int)
        xs = np.linspace(tile, Cz.shape[1] - 2 * tile, ntile).astype(int)
        pk, offs = [], []
        for y in ys:
            for x in xs:
                sy, sx = y + oy, x + ox
                if (y + tile > Cz.shape[0] or x + tile > Cz.shape[1] or
                        sy < 0 or sx < 0 or
                        sy + tile > S.shape[0] or sx + tile > S.shape[1]):
                    continue
                p, dy, dx = geom.peak(S[sy:sy + tile, sx:sx + tile],
                                      Cz[y:y + tile, x:x + tile])
                pk.append(p)
                offs.append((dy, dx))
        if not pk:
            sweep.append((float(s), 0.0, 0, 0))
            continue
        offs = np.array(offs)
        sweep.append((float(s), float(np.median(pk)),
                      int(np.median(offs[:, 0])), int(np.median(offs[:, 1]))))
        if verbose:
            print(f"    scale {s:.4f}: median tile peak {sweep[-1][1]:.4f} "
                  f"over {len(pk)} tiles  residual dy {sweep[-1][2] * D:+4d} "
                  f"dx {sweep[-1][3] * D:+4d} px")
    best = max(sweep, key=lambda t: t[1])
    interior = sweep[0][1] < best[1] and sweep[-1][1] < best[1]
    return best[0], best[1], interior, best[2] * D, best[3] * D, sweep


def commission():
    """NULL, PLANT and BADOFF, on strehl's own image so no comparator is needed."""
    src = None
    for k in ("bee", "119", "113"):
        p = os.path.join(ROOT, k, "arms", "strehl-A.tiff")
        if os.path.exists(p):
            src = p
            break
    if src is None:
        raise SystemExit("no strehl-A.tiff available to commission against")
    print("=" * 92)
    print(f"geomcrop COMMISSIONING -- source {src}")
    print("=" * 92)
    S = geom.block_mean(geom.load_grey(src), D)

    ok = True
    # ---- NULL: the image against itself.  scale 1.000, no offset.
    print("\n  NULL  (image against itself; true scale 1.0000)")
    s, sc, inter, dy, dx, _ = fit_tiles(S, S, COARSE, 0, 0, verbose=False)
    hit = abs(s - 1.0) < 1e-9 and dy == 0 and dx == 0
    ok &= hit
    print(f"    scale {s:.4f}  median tile peak {sc:.4f}  residual dy {dy:+d} "
          f"dx {dx:+d}  -> {'PASS' if hit else 'FAIL'}")

    # ---- PLANT: a KNOWN scale and a KNOWN centred crop, fitted through
    # EXACTLY the rule fit_subject uses -- coarse offset inferred from the two
    # raster shapes, residual absorbed per tile.  The scale is deliberately not
    # 1.0, so a fitter stuck at the centre of its sweep cannot pass.
    TS, MY, MX = 1.020, 35, 52            # true scale; crop margin in /D px
    Z = ndimage.zoom(S, 1.0 / TS, order=3)
    C = Z[MY:Z.shape[0] - MY, MX:Z.shape[1] - MX]
    oy = (S.shape[0] - C.shape[0]) // 2
    ox = (S.shape[1] - C.shape[1]) // 2
    print(f"\n  PLANT (true scale {TS:.4f}; comparator is a centred crop, "
          f"{C.shape[1] * D}x{C.shape[0] * D} from {S.shape[1] * D}x{S.shape[0] * D})")
    s, sc, inter, dy, dx, _ = fit_tiles(S, C, COARSE, oy, ox, verbose=False)
    ds = abs(s - TS)
    hit = ds <= 0.005 and inter
    ok &= hit
    print(f"    scale {s:.4f} (err {ds:.4f})  median tile peak {sc:.4f}  "
          f"interior={inter}  residual dy {dy:+d} dx {dx:+d}")
    print(f"    -> {'PASS' if hit else 'FAIL'}  (tolerance: one sweep step 0.005)")
    plant_peak = sc

    # ---- BADOFF: the SAME planted pair with a deliberately wrong coarse
    # offset.  Without this arm the fit could be offset-blind -- succeeding on
    # PLANT for reasons having nothing to do with the crop handling that is the
    # whole point of this file -- and an offset-blind fitter is precisely what
    # geom2.py already was.  The score must COLLAPSE.
    print(f"\n  BADOFF (same planted pair, coarse offset wrong by "
          f"{40 * D} px in each axis)")
    s3, sc3, _, _, _, _ = fit_tiles(S, C, COARSE, oy + 40, ox + 40, verbose=False)
    collapsed = sc3 < 0.5 * plant_peak
    ok &= collapsed
    print(f"    scale {s3:.4f}  median tile peak {sc3:.4f} against PLANT's "
          f"{plant_peak:.4f}  -> {'PASS (collapsed)' if collapsed else 'FAIL (offset-blind)'}")

    print(f"\n  COMMISSIONING {'PASSED' if ok else 'FAILED'}")
    return 0 if ok else 1


def fit_subject(key):
    arm = os.path.join(ROOT, key, "arms")
    sp = os.path.join(arm, "strehl-A.tiff")
    if not os.path.exists(sp):
        print(f"{key}: NO strehl-A.tiff -- subject not built")
        return None
    S = geom.block_mean(geom.load_grey(sp), D)
    out = {}
    for k, (fn, label) in COMPARATORS.items():
        cp = os.path.join(arm, fn)
        print(f"\n=== {key} / {k}: strehl vs {label} ===")
        if not os.path.exists(cp):
            print(f"  NOT PRESENT: {cp} -- FAILED (missing output)")
            out[k] = {"ok": False, "why": "missing output"}
            continue
        C = geom.block_mean(geom.load_grey(cp), D)
        cropped = C.shape != S.shape
        print(f"  strehl     {S.shape[1] * D} x {S.shape[0] * D}")
        print(f"  comparator {C.shape[1] * D} x {C.shape[0] * D}"
              f"{'   (raster differs)' if cropped else '   (same raster)'}")

        # --------------------------------- CROP or UNIFORM RESAMPLE?  MEASURED.
        # align_image_stack -m optimises field of view, so its output is not
        # guaranteed to be the input raster minus a crop: with a large focus
        # sweep it renormalises the FOV and the whole frame comes back
        # RESAMPLED.  The two cases need opposite treatment -- a crop needs a
        # large offset and scale ~1, a resample needs offset ~0 and a scale far
        # from 1 -- so assuming the wrong one makes the sweep run to its edge,
        # which is what happened on `bee-1-cpl` (peak 0.10, scale pinned at the
        # top of a +-6% range, and two different answers for two arms that
        # share a raster).
        #
        # The discriminator is free and it is in the raster shapes: a uniform
        # resample preserves the aspect ratio, a crop has no reason to.
        ry = S.shape[0] / C.shape[0]
        rx = S.shape[1] / C.shape[1]
        aspect_err = abs(ry - rx) / rx
        resampled = cropped and aspect_err < 0.01
        print(f"  raster ratios y {ry:.4f} x {rx:.4f} (agree to "
              f"{aspect_err * 100:.2f}%) -> "
              f"{'UNIFORM RESAMPLE' if resampled else ('CROP' if cropped else 'IDENTITY')}")
        if resampled:
            oy = ox = 0
            lo, hi = min(ry, rx) - 0.06, max(ry, rx) + 0.06
            coarse = np.arange(lo, hi + 1e-9, 0.005)
            print(f"  offset held at 0; scale swept {lo:.3f}-{hi:.3f} "
                  f"around the raster ratio")
        else:
            oy = (S.shape[0] - C.shape[0]) // 2
            ox = (S.shape[1] - C.shape[1]) // 2
            coarse = COARSE
            print(f"  coarse offset from centred crop: dy {oy * D:+d} "
                  f"dx {ox * D:+d} px")
        s, sc, inter, dy, dx, sweep = fit_tiles(S, C, coarse, oy, ox)
        if not inter:
            print("  NO INTERIOR MAXIMUM -- FAILED FIT, refusing to refine.")
            out[k] = {"ok": False, "why": "no interior maximum (tile fit)"}
            continue
        fine = np.arange(s - 0.006, s + 0.0061, 0.001)
        s2, sc2, inter2, dy2, dx2, _ = fit_tiles(S, C, fine, oy, ox, verbose=False)
        print(f"  REFINED scale {s2:.4f} median tile peak {sc2:.4f} "
              f"{'(interior)' if inter2 else '(EDGE -- treat with suspicion)'}")
        print(f"  residual offset: dy {dy2:+d} dx {dx2:+d} px")
        out[k] = {"ok": True, "scale": round(float(s2), 4),
                  "score": round(float(sc2), 4), "interior": bool(inter2),
                  "off_dy": int(oy * D + dy2), "off_dx": int(ox * D + dx2),
                  "resampled": bool(resampled), "joint": True, "label": label}

    # ------------------------------------------------- ARM-CONSISTENCY CHECK
    # Both comparators are fused from ONE align_image_stack output, so they
    # share a raster and therefore a scale BY CONSTRUCTION.  Two different
    # fitted scales is an internal contradiction and condemns the fit rather
    # than the data.  This is free, it needs no ground truth, and it is what
    # caught the global-correlation version of this file returning 1.0250 and
    # 1.0150 for two images that are the same size.
    good = {k: v for k, v in out.items() if v.get("ok")}
    if len(good) == 2:
        ks = list(good)
        d = abs(good[ks[0]]["scale"] - good[ks[1]]["scale"])
        agree = d <= 0.0015          # one fine step, the fit's own resolution
        print(f"\n  ARM CONSISTENCY: {ks[0]} {good[ks[0]]['scale']:.4f} vs "
              f"{ks[1]} {good[ks[1]]['scale']:.4f}  (differ by {d:.4f})  -> "
              f"{'CONSISTENT' if agree else 'CONTRADICTION'}")
        if not agree:
            print("  Both arms are fused from one aligned set and must share a\n"
                  "  scale.  Two answers for one quantity is a failing fit, so\n"
                  "  BOTH arms are marked failed for this subject.")
            for k in ks:
                out[k] = {"ok": False,
                          "why": f"arm-consistency contradiction "
                                 f"({good[ks[0]]['scale']:.4f} vs "
                                 f"{good[ks[1]]['scale']:.4f})"}

    p = os.path.join(ROOT, key, "geom.json")
    with open(p, "w", encoding="utf-8") as fh:
        json.dump(out, fh, indent=2)
    print(f"\n  written {p}")
    return out


def main():
    args = sys.argv[1:]
    if not args:
        raise SystemExit(__doc__)
    if args[0] == "commission":
        return commission()
    for k in args:
        fit_subject(k)
    return 0


if __name__ == "__main__":
    sys.exit(main())
