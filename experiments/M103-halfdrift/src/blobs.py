"""M103 -- are M97b's waxy blobs in the RENDER, or in M97b's VIEWER?

M97b Section 8 reported "waxy, smeared blobs in the bright low-texture region"
on the gain-corrected render of `dry-erase-marker-head-cpl`, cause unknown. The
orchestrator opened the side-by-side and judged them disqualifying as shipped.

M97b's viewer takes a 474 px crop from the corrected render for every 420 px crop
from the shipped one and Lanczos-downsamples it, deliberately, as a handicap. A
Lanczos kernel has negative lobes; on a smooth bright region with a slight
overshoot it can ring, and ringing on smooth content reads as waxy banding. So
the artefact might be M97b's viewer rather than the render.

That is a discriminating test, not a judgement call:

    take ONE region of the corrected render and produce two pictures of it
      A. cropped 1:1, no resampling of any kind
      B. cropped at 474 and Lanczos-resampled to 420, exactly as M97b does

    blobs in both  -> the render is at fault, the viewer is exonerated
    blobs in B only -> the viewer is at fault
    blobs in A only -> impossible; would indict this script

Nothing here resamples the 1:1 arm. 16-bit is mapped to 8-bit by a plain right
shift of 8: no gamma, no stretch, no clipping, no tone curve. The TIFs are
already sRGB-encoded by `--srgb`, so a shift is the identity on appearance and
cannot manufacture a smooth region.

Controls:
  PLACEBO   the shipped render gets the identical treatment at the matched scene
            location. It is the arm M97b says does NOT have blobs, so it is the
            negative case: if my crop pipeline manufactures blobs, they appear
            here too.
  POSITIVE  a synthetic patch of known smooth gradient plus fine noise is passed
            through the same 474->420 Lanczos. If Lanczos banding is capable of
            producing this artefact at all, it shows here, on content whose
            true smoothness is known.
  SELF      the 1:1 arm is checked to be byte-identical to the source pixels it
            claims to show (no accidental resize by the PNG writer).

usage:
  python src/blobs.py <shipped.tif> <corrected.tif> <outdir>
"""

import json
import os
import sys

import numpy as np
from PIL import Image

Image.MAX_IMAGE_PIXELS = None

# M97b's viewer geometry, from experiments/M97b-align-visible/src/owner_sbs.py
PANEL = 420
SCALE = 1.1278  # MEASURED by M97b: corrected subject is 1.1278x the shipped one
BIG = int(round(PANEL * SCALE))  # 474
PANELS = {"upper-left": (0.34, 0.30), "centre": (0.50, 0.52), "lower-right": (0.66, 0.72)}


def to8(a):
    """-> uint8 with no tone change. The renders `--srgb` writes are already
    8-bit sRGB; a 16-bit source is mapped by a plain right shift. No gamma, no
    stretch, no clip. (An earlier version shifted unconditionally, which zeroes
    a uint8 source; caught by this script's own smoothness readout coming back
    at 1.0000 smooth / 0.0000 bright on all three panels, i.e. a black frame.)"""
    if a.dtype == np.uint8:
        return a
    return (a >> 8).astype(np.uint8)


def load(p):
    im = Image.open(p)
    a = np.asarray(im)
    print("  %-44s %s %s" % (os.path.basename(p), a.shape, a.dtype))
    return a


def b_coords(ay, ax, ha, wa, hb, wb):
    """Same scene point in the corrected render, measured from each image's own
    centre and scaled -- M97b's mapping, reproduced."""
    dy = ay + PANEL / 2 - (ha - 1) / 2
    dx = ax + PANEL / 2 - (wa - 1) / 2
    by = int((hb - 1) / 2 + dy * SCALE - BIG / 2)
    bx = int((wb - 1) / 2 + dx * SCALE - BIG / 2)
    return max(0, min(by, hb - BIG)), max(0, min(bx, wb - BIG))


def lanczos(patch, out=PANEL):
    return np.asarray(Image.fromarray(patch).resize((out, out), Image.LANCZOS))


def texture(gray, k=9):
    """Local standard deviation via integral images -- the smoothness measure."""
    g = gray.astype(np.float64)
    s = np.cumsum(np.cumsum(g, 0), 1)
    s2 = np.cumsum(np.cumsum(g * g, 0), 1)
    s = np.pad(s, ((1, 0), (1, 0)))
    s2 = np.pad(s2, ((1, 0), (1, 0)))
    h, w = g.shape
    y0, y1 = np.arange(h - k), np.arange(k, h)
    x0, x1 = np.arange(w - k), np.arange(k, w)
    A = s[np.ix_(y1, x1)] - s[np.ix_(y0, x1)] - s[np.ix_(y1, x0)] + s[np.ix_(y0, x0)]
    B = s2[np.ix_(y1, x1)] - s2[np.ix_(y0, x1)] - s2[np.ix_(y1, x0)] + s2[np.ix_(y0, x0)]
    n = k * k
    return np.sqrt(np.maximum(B / n - (A / n) ** 2, 0.0))


def main():
    ship_p, corr_p, outdir = sys.argv[1], sys.argv[2], sys.argv[3]
    os.makedirs(outdir, exist_ok=True)
    print("loading (188 MB each, ~30 s)")
    A = load(ship_p)
    B = load(corr_p)
    ha, wa = A.shape[:2]
    hb, wb = B.shape[:2]
    res = {"shipped_shape": list(A.shape), "corrected_shape": list(B.shape),
           "panel": PANEL, "big": BIG, "scale": SCALE, "panels": {}}

    for name, (fy, fx) in PANELS.items():
        ay, ax = int(ha * fy), int(wa * fx)
        by, bx = b_coords(ay, ax, ha, wa, hb, wb)
        raw = B[by:by + BIG, bx:bx + BIG]
        shipraw = A[ay:ay + PANEL, ax:ax + PANEL]

        # ARM A -- 1:1, no resampling whatsoever
        a1 = to8(raw)
        Image.fromarray(a1).save(os.path.join(outdir, "%s_CORR_1to1_%dpx.png" % (name, BIG)))
        # ARM B -- M97b's exact handicap
        a2 = lanczos(a1)
        Image.fromarray(a2).save(os.path.join(outdir, "%s_CORR_lanczos%d.png" % (name, PANEL)))
        # PLACEBO -- the shipped arm, same pipeline, no Lanczos (it is already 420)
        Image.fromarray(to8(shipraw)).save(
            os.path.join(outdir, "%s_SHIP_1to1_%dpx.png" % (name, PANEL)))

        # SELF control: the saved 1:1 PNG must be the source pixels, unresized
        chk = np.asarray(Image.open(os.path.join(outdir, "%s_CORR_1to1_%dpx.png" % (name, BIG))))
        same = chk.shape == a1.shape and bool((chk == a1).all())

        g = a1[..., 1].astype(np.float64)
        t = texture(g)
        smooth_frac = float((t < 2.0).mean())
        bright_smooth = float(((t < 2.0) & (g[4:-5, 4:-5] > 140)).mean())
        res["panels"][name] = {
            "shipped_yx": [ay, ax], "corrected_yx": [by, bx],
            "self_control_byte_identical": same,
            "corr_smooth_frac": smooth_frac,
            "corr_bright_smooth_frac": bright_smooth,
            "corr_mean": float(g.mean()),
        }
        gs = to8(shipraw)[..., 1].astype(np.float64)
        ts = texture(gs)
        res["panels"][name]["ship_smooth_frac"] = float((ts < 2.0).mean())
        res["panels"][name]["ship_bright_smooth_frac"] = float(
            ((ts < 2.0) & (gs[4:-5, 4:-5] > 140)).mean())
        res["panels"][name]["ship_mean"] = float(gs.mean())
        print("  %-12s ship(%d,%d) corr(%d,%d)  self-control %s" %
              (name, ay, ax, by, bx, "PASS" if same else "FAIL"))

    # POSITIVE control: can Lanczos 474->420 band a known-smooth patch at all?
    yy, xx = np.mgrid[0:BIG, 0:BIG]
    ramp = (120 + 60.0 * xx / BIG)
    rng = np.random.default_rng(7)
    synth = np.clip(ramp + rng.normal(0, 1.2, ramp.shape), 0, 255).astype(np.uint8)
    synth3 = np.dstack([synth] * 3)
    lz = lanczos(synth3)[..., 1].astype(np.float64)
    # banding would show as periodic structure across the ramp; measure the
    # residual after removing the known linear ramp
    fit = np.polyfit(np.arange(PANEL), lz.mean(0), 1)
    resid = lz.mean(0) - np.polyval(fit, np.arange(PANEL))
    res["positive_lanczos_band_amplitude_dn"] = float(resid.max() - resid.min())
    print("\nPOSITIVE  Lanczos %d->%d on a KNOWN smooth ramp + noise:" % (BIG, PANEL))
    print("          residual banding amplitude %.3f DN (of 255)"
          % res["positive_lanczos_band_amplitude_dn"])

    print("\nSmoothness of the region M97b called blobby (fraction of pixels with")
    print("local sigma < 2 DN, 9x9 window; and the same restricted to bright pixels):")
    print("  %-12s %10s %10s | %10s %10s" %
          ("panel", "ship smth", "corr smth", "ship brt", "corr brt"))
    for name in PANELS:
        p = res["panels"][name]
        print("  %-12s %10.4f %10.4f | %10.4f %10.4f" %
              (name, p["ship_smooth_frac"], p["corr_smooth_frac"],
               p["ship_bright_smooth_frac"], p["corr_bright_smooth_frac"]))

    with open(os.path.join(outdir, "blobs.json"), "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=1, sort_keys=True)
    print("\nwrote %s" % os.path.join(outdir, "blobs.json"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
