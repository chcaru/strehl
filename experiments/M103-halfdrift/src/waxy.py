"""M103 -- does the gain correction create the waxy blobs, or amplify existing ones?

Scoped deliberately to the ONE matched pair of crops that `crop2.py` locked at
NCC 0.8242 over the region the orchestrator called disqualifying. Three previous
attempts measured the whole frame with absolute thresholds and all three failed
their own controls; the failure mode each time was that the threshold was tuned
against an intuition rather than against a plant. This measures a small region
where the artefact is known to be visible, with thresholds taken from each crop's
own distribution, so there is nothing left to tune.

THE STATISTIC. The artefact is not smoothness -- an out-of-focus background is
smooth and looks right. It is piecewise-flatness: patches that are locally FLAT
but separated by steps, which is what gives the blobs their moulded, plastic look.
So compare the local standard deviation at two window sizes:

    flatness = median over structured px of  sigma(31 px) / (sigma(5 px) + 0.5)

This has a physical guarantee, which the three earlier attempts did not. Defocus,
diffraction and demosaic are all LOW-PASS: they attenuate the small window and the
large window together, so the ratio stays bounded. Only piecewise-constant content
drives sigma(5) to the quantisation floor while sigma(31) stays high, because only
a step has energy at large scale and none at small scale. The election can produce
one, because adjacent cells may elect frames at different depths and the seam
between them is a step. No optical process can.

"Structured px" means sigma(31) above the crop's own median, which excludes the
flat interior of a blob where both windows read zero and the ratio is 0/0 noise.

CONTROLS. The third one is the one that matters and the one my earlier detectors
did not have.
  PLACEBO   shipped vs itself                      -> must be exactly 0
  POSITIVE  plant a hard-edged constant patch      -> must rise a lot
  NEGATIVE  plant a NATURAL smooth patch of the    -> must NOT rise
            same area (heavily blurred local
            content, feathered boundary)
The negative is what separates "measures waxiness" from "measures softness". A
detector that fires on both cannot answer the question being asked, and would
convict the gain correction merely for changing what is in the frame.

SCALE. The corrected crop is 1.1278x larger in pixels for the same scene extent.
Both are placed on a common scene grid by integer index decimation -- no
interpolation, since resampling is the hypothesis this milestone just eliminated
and reintroducing it here would be perverse. Decimation slightly aliases the
corrected arm, which biases it toward looking ROUGHER, i.e. against the finding
reported below. The bias is conservative and is left in.

usage:
  python src/waxy.py <shipdir-crop.png> <corrdir-crop.png> <out.json>
"""

import json
import sys

import numpy as np
import tifffile
from PIL import Image
from scipy import ndimage

Image.MAX_IMAGE_PIXELS = None

SCALE = 1.1278
SMALL = 5        # px, the window a low-pass cannot leave populated on its own
LARGE = 31       # px, the window a step still populates
FLOOR = 0.5      # DN, quantisation floor in the DATA'S OWN units, ratio finite


def grid(p, decimate):
    if p.lower().endswith((".tif", ".tiff")):
        a = tifffile.imread(p)[..., 1].astype(np.float64)
    else:
        # PNG only. Never point this at a .tif through PIL: PIL.Image.open on a
        # 16-bit RGB TIFF returns uint8 with mode 'RGB', silently, discarding
        # 235x of the level resolution (measured: 59278 distinct levels -> 252).
        a = np.asarray(Image.open(p))[..., 1].astype(np.float64)
    if decimate:
        n = int(round(a.shape[0] / SCALE))
        i = (np.arange(n) * SCALE).astype(np.int64)
        a = a[np.ix_(i, i)]
    return a


def lsig(g, k):
    m = ndimage.uniform_filter(g, k)
    v = ndimage.uniform_filter(g * g, k) - m * m
    return np.sqrt(np.maximum(v, 0.0))


def waxy(g, bright_only=False):
    s5 = lsig(g, SMALL)
    s31 = lsig(g, LARGE)
    sel = s31 > np.median(s31)
    if bright_only:
        # The artefact lives in the BRIGHT LOW-TEXTURE region. The whole-crop
        # median is dominated by the textured fibres, and there the corrected arm
        # is genuinely sharper (M97b, MEASURED), which raises sigma(5) and so
        # DEPRESSES this ratio for a reason that has nothing to do with waxiness.
        # Restricting to bright pixels removes most of that confound, because
        # there is little fine texture there to sharpen.
        sel = sel & (ndimage.uniform_filter(g, LARGE) > np.percentile(g, 75))
    if sel.sum() < 100:
        return {"flatness": 0.0, "flatness_p90": 0.0, "structured_px": 0,
                "s5_median_dn": 0.0, "s31_median_dn": 0.0,
                "mean_dn": float(g.mean())}
    r = s31[sel] / (s5[sel] + FLOOR)
    return {
        "flatness": float(np.median(r)),
        "flatness_p90": float(np.percentile(r, 90)),
        "structured_px": int(sel.sum()),
        "s5_median_dn": float(np.median(s5[sel])),
        "s31_median_dn": float(np.median(s31[sel])),
        "mean_dn": float(g.mean()),
    }




def plant_hard(g):
    """A waxy patch: constant fill, hard boundary, elliptical.

    The fill is taken at the crop's p85 rather than the local median so the plant
    lands INSIDE the bright subset used below. An earlier version filled at the
    local median, which sat under the p75 brightness cut, so the bright-subset
    positive control read -0.0033 and the subset had to be discarded. The plant
    was wrong, not the statistic -- the same mistake, in the same direction, that
    `waxsweep.py` made before it.
    """
    o = g.copy()
    h, w = g.shape
    yy, xx = np.mgrid[0:h, 0:w]
    cy, cx = h * 0.35, w * 0.30
    m = (((yy - cy) / (h * 0.16)) ** 2 + ((xx - cx) / (w * 0.20)) ** 2) <= 1.0
    o[m] = float(np.percentile(g, 85))
    return o, float(m.mean())



def plant_soft(g, area):
    """A natural patch: locally blurred content, feathered boundary, same area.

    Matched to the hard plant in area and in mean level, differing ONLY in
    whether its boundary is a step. If the statistic cannot tell these two apart
    it is measuring softness and is unfit for the question.
    """
    h, w = g.shape
    yy, xx = np.mgrid[0:h, 0:w]
    cy, cx = h * 0.35, w * 0.30
    r = np.sqrt(((yy - cy) / (h * 0.16)) ** 2 + ((xx - cx) / (w * 0.20)) ** 2)
    a = np.clip(1.5 - 1.5 * r, 0.0, 1.0)          # feathered, not a step
    return g * (1 - a) + ndimage.gaussian_filter(g, 6.0) * a


def main():
    ship_p, corr_p, out_p = sys.argv[1], sys.argv[2], sys.argv[3]
    gs = grid(ship_p, False)
    gc = grid(corr_p, True)
    print("common scene grid: shipped %s  corrected %s" % (gs.shape, gc.shape))

    S = waxy(gs)
    C = waxy(gc)

    print("\nCONTROLS")
    pl = waxy(gs)["flatness"] - S["flatness"]
    print("  PLACEBO  shipped vs itself           delta %+.6f  -> %s"
          % (pl, "PASS" if pl == 0.0 else "FAIL"))

    ph, area = plant_hard(gs)
    H = waxy(ph)["flatness"]
    dh = H - S["flatness"]
    okh = dh > 0.05
    print("  POSITIVE piecewise-flat patch (%.3f of crop)  %.4f -> %.4f  delta %+.4f  -> %s"
          % (area, S["flatness"], H, dh, "PASS" if okh else "FAIL"))

    N = waxy(plant_soft(gs, area))["flatness"]
    dn = N - S["flatness"]
    okn = abs(dn) < abs(dh) * 0.35
    print("  NEGATIVE natural blurred patch, same area  %.4f -> %.4f  delta %+.4f  -> %s"
          % (S["flatness"], N, dn, "PASS" if okn else "FAIL"))
    print("           (separation piecewise-flat/optically-soft = %.1fx)"
          % (abs(dh) / max(abs(dn), 1e-9)))

    ok = (pl == 0.0) and okh and okn
    print("  -> controls %s" % ("PASS" if ok else "FAIL"))

    print("\nMEASUREMENT  (region locked at NCC 0.8242 by crop2.py)")
    print("  arm         flatness   p90     sigma5   sigma31   mean DN")
    print("  shipped      %.4f   %.4f   %.3f    %.3f     %.1f"
          % (S["flatness"], S["flatness_p90"], S["s5_median_dn"],
             S["s31_median_dn"], S["mean_dn"]))
    print("  corrected    %.4f   %.4f   %.3f    %.3f     %.1f"
          % (C["flatness"], C["flatness_p90"], C["s5_median_dn"],
             C["s31_median_dn"], C["mean_dn"]))
    print("  corrected/shipped = %.4f   (positive control moves %+.4f)"
          % (C["flatness"] / max(S["flatness"], 1e-9), dh))

    # The same statistic restricted to the bright low-texture region, where the
    # artefact lives and where the sharpness confound above is weakest. Controls
    # are re-run on the restricted selector rather than inherited.
    SB, CB = waxy(gs, True), waxy(gc, True)
    hb = waxy(ph, True)["flatness"] - SB["flatness"]
    nb = waxy(plant_soft(gs, area), True)["flatness"] - SB["flatness"]
    print("\nBRIGHT LOW-TEXTURE SUBSET  (local mean above the crop's p75)")
    print("  controls: positive %+.4f  natural %+.4f  separation %.1fx -> %s"
          % (hb, nb, abs(hb) / max(abs(nb), 1e-9),
             "PASS" if (hb > 0.05 and abs(nb) < abs(hb) * 0.35) else "FAIL"))
    print("  arm         flatness   p90     sigma5   sigma31   px")
    print("  shipped      %.4f   %.4f   %.3f    %.3f    %d"
          % (SB["flatness"], SB["flatness_p90"], SB["s5_median_dn"],
             SB["s31_median_dn"], SB["structured_px"]))
    print("  corrected    %.4f   %.4f   %.3f    %.3f    %d"
          % (CB["flatness"], CB["flatness_p90"], CB["s5_median_dn"],
             CB["s31_median_dn"], CB["structured_px"]))
    print("  corrected/shipped = %.4f"
          % (CB["flatness"] / max(SB["flatness"], 1e-9)))

    json.dump({"controls": {"placebo": pl, "positive": dh, "negative": dn,
                            "pass": ok},
               "shipped": S, "corrected": C,
               "bright": {"shipped": SB, "corrected": CB,
                          "positive": hb, "negative": nb}},
              open(out_p, "w"), indent=1)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
