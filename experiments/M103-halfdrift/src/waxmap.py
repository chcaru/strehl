"""M103 -- what makes the waxy blobs? A whole-frame detector, with plants.

`blobs.py` killed the viewer hypothesis: the artefact is in the raw pixels at 1:1
with no resampling. The remaining candidates, from the orchestrator:

  H1 election mottle -- in a region with no focus signal the box-mean gradient
     response is noise (fact 73), so adjacent cells elect frames at very
     different depths. Predicts: patches of smooth (defocused) content separated
     by HARD boundaries, and -- crucially -- the effect is a property of the
     ELECTION, not of the gain, so it must be present in BOTH arms, differing in
     where and how much.

  H2 coverage -- warping further shrinks the commonly-covered region, so
     `fit_to_cover` crops harder and upsamples more. Predicts: a GLOBAL softening
     that is worst at the periphery, because coverage is an intersection of
     warped rectangles and fails at the edges first. Does not predict localised
     patches with hard interior boundaries.

The two make opposite predictions about *locality* and about *which arm*, so one
whole-frame measurement separates them.

The detector wants the conjunction that distinguishes a merge artefact from
honest defocus. Honest out-of-focus background is smooth and bright too -- but it
has no hard boundary inside it. So a pixel is "waxy" when it is

    bright, AND has near-zero local texture, AND belongs to a low-texture region
    whose BOUNDARY carries a strong gradient

Controls:
  PLACEBO     the same detector on the shipped render. M97b says that arm has no
              blobs; if the detector fires equally there it is not measuring the
              artefact.
  POSITIVE    plant a synthetic waxy blob (smooth fill, hard edge) of known area
              and location into a copy of a real render; the detector must find
              it, at that location, with roughly that area.
  SPECIFICITY plant a large Gaussian-blurred patch -- smooth and bright, but with
              NO hard boundary, i.e. honest defocus. The detector must NOT fire.
              This is the discriminating control: without it, "waxy" is just
              "smooth" and the whole measurement is circular.

usage:
  python src/waxmap.py <shipped.tif> <corrected.tif> <outdir>
"""

import json
import os
import sys

import numpy as np
from PIL import Image, ImageFilter

Image.MAX_IMAGE_PIXELS = None

SIG = 1.5     # DN: local sigma below this is "no texture"
BRIGHT = 110  # DN: the artefact is reported in the BRIGHT low-texture regions
EDGE = 12.0   # DN: gradient magnitude that counts as a hard boundary
K = 9         # local-sigma window
BLOCK = 16    # map cell


def local_sigma(g, k=K):
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
    out = np.zeros_like(g)
    out[k // 2:k // 2 + h - k, k // 2:k // 2 + w - k] = np.sqrt(
        np.maximum(B / n - (A / n) ** 2, 0.0))
    return out


def wax_mask(g):
    """A flat, bright REGION whose BOUNDARY carries a hard edge.

    The criterion is region-based, not cell-based. An earlier version required
    every cell to sit near a hard edge, which fires only on a blob's perimeter
    ring and excludes its interior -- the positive control caught it, returning
    10 of 352 planted cells. A blob is a *bounded region*, so the test is: label
    the connected flat-and-bright regions, and accept a whole region when a
    sufficient share of its boundary is a hard edge. That also keeps the
    specificity control meaningful: honest defocus is flat and bright but its
    boundary fades, so its regions are rejected entire.
    """
    from scipy import ndimage

    sig = local_sigma(g)
    flat = (sig < SIG) & (g > BRIGHT)
    gy, gx = np.gradient(g)
    grad = np.hypot(gy, gx)

    fi = Image.fromarray((flat * 255).astype(np.uint8)).resize(
        (g.shape[1] // BLOCK, g.shape[0] // BLOCK), Image.BOX)
    flat_frac = np.asarray(fi).astype(np.float64) / 255.0
    fmask = flat_frac > 0.75

    # Block-MAX, not block-mean. A hard edge is a local maximum: averaging a
    # 140 DN step over the 16 px it occupies in a 256 px cell yields ~8.75 DN,
    # below EDGE, so a mean-pooled gradient map reports no hard edges anywhere.
    # That zeroed both controls before it was caught.
    bh, bw = g.shape[0] // BLOCK, g.shape[1] // BLOCK
    gblk = grad[:bh * BLOCK, :bw * BLOCK].reshape(bh, BLOCK, bw, BLOCK).max(axis=(1, 3))

    lab, n = ndimage.label(fmask)
    out = np.zeros_like(fmask)
    if n:
        for sl, i in zip(ndimage.find_objects(lab), range(1, n + 1)):
            if sl is None:
                continue
            pad = tuple(slice(max(0, s.start - 3), min(d, s.stop + 3))
                        for s, d in zip(sl, fmask.shape))
            sub = lab[pad] == i
            if int(sub.sum()) < 4:  # a handful of cells is noise, not a blob
                continue
            ring = ndimage.binary_dilation(sub, iterations=2) & ~ndimage.binary_erosion(
                sub, iterations=2)
            if ring.sum() == 0:
                continue
            if float((gblk[pad][ring] > EDGE).mean()) > 0.30:
                out[pad] |= sub
    return flat_frac, gblk > EDGE, out


def summarise(name, g):
    ff, hn, wax = wax_mask(g)
    h, w = wax.shape
    yy, xx = np.mgrid[0:h, 0:w]
    cy, cx = (h - 1) / 2.0, (w - 1) / 2.0
    r = np.hypot((yy - cy) / cy, (xx - cx) / cx)
    tot = float(wax.mean())
    inner = float(wax[r < 0.5].mean())
    outer = float(wax[r > 0.8].mean())
    return {"wax_frac": tot, "wax_frac_inner_r<0.5": inner, "wax_frac_outer_r>0.8": outer,
            "flat_frac": float((ff > 0.75).mean())}, wax


def load_green(p):
    a = np.asarray(Image.open(p))
    return a[..., 1].astype(np.float64), a


def main():
    ship_p, corr_p, outdir = sys.argv[1], sys.argv[2], sys.argv[3]
    os.makedirs(outdir, exist_ok=True)
    print("loading")
    gs, As = load_green(ship_p)
    gc, Ac = load_green(corr_p)
    print("  shipped %s  corrected %s" % (As.shape, Ac.shape))

    # ---------------- CONTROLS ----------------
    print("\nCONTROLS")
    base, _ = summarise("ship", gs)

    # POSITIVE: a smooth fill with a hard edge, known area. The fill must be
    # BRIGHT, because the artefact being detected is bright-and-smooth and the
    # detector requires it. (A first version filled with the local median + 40,
    # which in this dark region never crossed BRIGHT, and the control correctly
    # failed at 3% of the planted area. The plant was wrong, not the detector.)
    plant = gs.copy()
    ph, pw = 300, 300
    py, px = 1200, 2400
    plant[py:py + ph, px:px + pw] = 175.0
    ppos, wpos = summarise("plant", plant)
    want = (ph * pw) / float(gs.size)
    got = ppos["wax_frac"] - base["wax_frac"]
    ok1 = got > 0.4 * want
    print("  POSITIVE planted smooth blob, hard edge, area %.5f of frame:" % want)
    print("           detector rises %.5f -> %.5f (delta %.5f) -> %s"
          % (base["wax_frac"], ppos["wax_frac"], got, "PASS" if ok1 else "FAIL"))

    # SPECIFICITY: honest defocus -- smooth and bright, NO hard boundary
    soft = gs.copy()
    sy, sx = 2600, 4200
    patch = Image.fromarray(soft[sy:sy + 600, sx:sx + 600].astype(np.uint8))
    blur = np.asarray(patch.filter(ImageFilter.GaussianBlur(14))).astype(np.float64)
    # feather the seam so the patch introduces no hard edge of its own
    ramp = np.minimum(np.minimum(np.arange(600), np.arange(600)[::-1])[:, None],
                      np.minimum(np.arange(600), np.arange(600)[::-1])[None, :])
    a = np.clip(ramp / 60.0, 0, 1)
    soft[sy:sy + 600, sx:sx + 600] = a * blur + (1 - a) * soft[sy:sy + 600, sx:sx + 600]
    psoft, _ = summarise("soft", soft)
    dsoft = psoft["wax_frac"] - base["wax_frac"]
    ok2 = dsoft < 0.25 * got
    print("  SPECIFICITY planted honest defocus (Gaussian sigma 14, feathered, 4x the area):")
    print("           detector moves %+.5f, against %+.5f for the hard-edged blob -> %s"
          % (dsoft, got, "PASS" if ok2 else "FAIL"))
    print("           (so it is measuring a BOUNDED region, not just smoothness)")

    ok = ok1 and ok2
    print("  -> controls %s\n" % ("PASS" if ok else "FAIL"))
    if not ok:
        return 1

    # ---------------- the two arms ----------------
    sship, wship = summarise("ship", gs)
    scorr, wcorr = summarise("corr", gc)
    print("Whole-frame waxy fraction (bright, textureless, hard-bounded):")
    print("  %-12s %10s %10s %10s" % ("arm", "whole", "inner r<0.5", "outer r>0.8"))
    for n, s in (("shipped", sship), ("corrected", scorr)):
        print("  %-12s %10.5f %10.5f %10.5f"
              % (n, s["wax_frac"], s["wax_frac_inner_r<0.5"], s["wax_frac_outer_r>0.8"]))
    print()
    print("H1 (election) predicts the artefact in BOTH arms, localised, interior.")
    print("H2 (coverage) predicts a GLOBAL effect, worst at the periphery.")
    ratio_in_out_c = (scorr["wax_frac_outer_r>0.8"] /
                      max(scorr["wax_frac_inner_r<0.5"], 1e-9))
    print("  corrected outer/inner = %.2f  (H2 needs this >> 1)" % ratio_in_out_c)
    print("  corrected/shipped whole = %.2f  (H1 needs both arms non-zero)"
          % (scorr["wax_frac"] / max(sship["wax_frac"], 1e-9)))

    for n, w in (("shipped", wship), ("corrected", wcorr)):
        Image.fromarray((w * 255).astype(np.uint8)).save(
            os.path.join(outdir, "waxmap-%s.png" % n))

    res = {"shipped": sship, "corrected": scorr,
           "controls": {"positive_delta": got, "positive_expected_area": want,
                        "specificity_delta": dsoft, "pass": bool(ok)}}
    with open(os.path.join(outdir, "waxmap.json"), "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=1, sort_keys=True)
    print("\nwrote %s" % os.path.join(outdir, "waxmap.json"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
