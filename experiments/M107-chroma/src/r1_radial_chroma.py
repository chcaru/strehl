"""M107b R-series: is ORCH's D2 edge-chroma excess RADIUS-dependent?

WHY THIS MATTERS, AND THE STRUCTURAL WORRY THAT PROMPTED IT
-----------------------------------------------------------
ORCH measured, with a single-frame LibRaw control:
    lavendar: strehl 4.22x vs control 1.36x  -> 3.1x excess
    marker:   strehl 2.65x vs control 2.23x  -> 1.19x excess
and proposes validating a chroma fix two-sided: drive lavendar toward 1.36x
while leaving marker near 2.23x.

The worry: LATERAL CA IS PRESENT IN A SINGLE FRAME AT FULL STRENGTH. It is an
optical property of the lens and it does not care that you stacked. So it is in
BOTH arms of the render/control ratio and it largely CANCELS. If that is right,
ORCH's 3.1x excess is by construction NOT the quantity M107b's lateral
correction removes, and a correct lateral fix would score badly against it --
it would push the render BELOW an uncorrected control and read as
over-correction.

The axial term (fact 1413) has the opposite property: it is created by electing
one frame on green and gathering R/B there, so it exists ONLY in the merged
render and NOT in a single frame. It survives the control by construction.

BARS, REGISTERED BEFORE THE NUMBERS ARE SEEN
--------------------------------------------
R1  Is lateral CA visible to this metric at all?
    Edge-chroma in the SINGLE-FRAME CONTROL, binned by radius, normalised to the
    innermost annulus.
      RISING  (outer/inner >= 1.50) -> lateral CA is visible in the control,
              therefore it cancels in ORCH's excess, therefore the excess does
              not measure it.
      FLAT    (outer/inner in [0.80, 1.25]) -> the metric is blind to lateral CA;
              it cannot validate M107b's fix in either direction.
      FALLING (<= 0.80) -> unexpected; report, do not explain away.

R2  Is the EXCESS radius-dependent?
    (render edge-chroma / control edge-chroma) per annulus.
      FLAT   -> the added term is radius-independent, i.e. consistent with the
                axial/election mechanism and NOT with a lateral scale error.
      RISING (outer/inner >= 1.50) -> a radius-dependent term is being ADDED by
                the pipeline; that would be new and would implicate geometry
                (warp scale) rather than election.

R3  CONTROL, and it is the one that can kill R1: per-channel colour shading
    (vignetting) also produces radial chroma, but on FLAT pixels as well as
    edges. So run the identical radial binning over the bottom-50%-gradient
    (flat) pixels.
      If flat pixels show the SAME radial trend as edges, the R1 trend is colour
      shading, NOT lateral CA, and R1 must not be read as CA.
      Lateral CA acts only where there is an edge to displace, so the CA reading
      REQUIRES edges to rise while flats stay put.

R4  SANITY: reproduce ORCH's four global D2 numbers to +/-0.05x. If this fails,
    my loader or metric differs from theirs and nothing below is comparable.

Radius is normalised to each image's own half-diagonal, so the render and the
LibRaw control are comparable even if their pixel dimensions differ.
"""
import glob
import sys

import numpy as np
import tifffile

N_ANN = 6
EDGE_PCT = 99.0
FLAT_PCT = 50.0


def load(path):
    a = tifffile.imread(path)
    if a.dtype == np.uint16:
        a = a.astype(np.float32) / 65535.0
    elif a.dtype == np.uint8:
        a = a.astype(np.float32) / 255.0
    else:
        a = a.astype(np.float32)
    if a.ndim == 2:
        a = np.stack([a] * 3, -1)
    return a[..., :3]


def luma(img):
    return 0.2126 * img[..., 0] + 0.7152 * img[..., 1] + 0.0722 * img[..., 2]


def fields(path):
    """Return (chroma, grad, rnorm) as float32, releasing the RGB image."""
    img = load(path)
    y = luma(img)
    chroma = np.maximum(np.abs(img[..., 0] - y), np.abs(img[..., 2] - y)).astype(np.float32)
    del img
    gy, gx = np.gradient(y)
    grad = np.hypot(gx, gy).astype(np.float32)
    del y, gy, gx
    h, w = grad.shape
    yy = (np.arange(h, dtype=np.float32) - (h - 1) / 2.0)[:, None]
    xx = (np.arange(w, dtype=np.float32) - (w - 1) / 2.0)[None, :]
    r = np.sqrt(yy * yy + xx * xx)
    r /= float(np.hypot((h - 1) / 2.0, (w - 1) / 2.0))
    return chroma, grad, r.astype(np.float32)


def d2_global(chroma, grad):
    edge = grad >= np.percentile(grad, EDGE_PCT)
    flat = grad <= np.percentile(grad, FLAT_PCT)
    ce, cf = chroma[edge].mean(), chroma[flat].mean()
    return float(ce / max(cf, 1e-9)), float(ce), float(cf)


def radial(chroma, grad, r, which):
    """Mean chroma over `which` ('edge'|'flat') pixels, per radial annulus.

    The edge/flat thresholds are GLOBAL, not per-annulus, so that an annulus
    with few strong edges is reported as sparse rather than having its own
    weaker edges promoted to 'edge' by a local percentile.
    """
    if which == "edge":
        sel = grad >= np.percentile(grad, EDGE_PCT)
    else:
        sel = grad <= np.percentile(grad, FLAT_PCT)
    edges = np.linspace(0.0, 1.0, N_ANN + 1)
    out = []
    for i in range(N_ANN):
        m = sel & (r >= edges[i]) & (r < edges[i + 1])
        n = int(m.sum())
        out.append((n, float(chroma[m].mean()) if n >= 500 else float("nan")))
    return out


def trend(vals):
    v = [x for x in vals if np.isfinite(x)]
    if len(v) < 3 or v[0] <= 0:
        return float("nan")
    return v[-1] / v[0]


def verdict(ratio):
    if not np.isfinite(ratio):
        return "INDETERMINATE (too few pixels)"
    if ratio >= 1.50:
        return "RISING"
    if ratio <= 0.80:
        return "FALLING"
    if ratio <= 1.25:
        return "FLAT"
    return "INTERMEDIATE (1.25-1.50, not resolved)"


def main():
    tn = r"C:\dev\strehl-out\ORCH-thennow"
    scenes = {
        "lavendar": (rf"{tn}\lavendar-HEAD-8f46f04.tif",
                     rf"{tn}\CONTROL-singleframe-lavendar-cpl.tif"),
        "marker": (rf"{tn}\marker-HEAD-8f46f04.tif",
                   glob.glob(rf"{tn}\CONTROL-singleframe-dry-erase-marker*.tif")[0]),
    }
    expect = {"lavendar": (4.22, 1.36), "marker": (2.65, 2.23)}

    for name, (rp, cp) in scenes.items():
        print("=" * 72)
        print(f"SCENE {name}")
        print(f"  render  {rp}")
        print(f"  control {cp}")
        res = {}
        for tag, path in (("render", rp), ("control", cp)):
            ch, gr, r = fields(path)
            g, ce, cf = d2_global(ch, gr)
            e = radial(ch, gr, r, "edge")
            f = radial(ch, gr, r, "flat")
            res[tag] = (g, e, f)
            del ch, gr, r
            print(f"  [{tag:7s}] D2 global {g:.2f}x  (edge {ce:.5f} flat {cf:.5f})")

        # R4 sanity
        er, ec = expect[name]
        d_r, d_c = abs(res["render"][0] - er), abs(res["control"][0] - ec)
        ok = d_r <= 0.05 and d_c <= 0.05
        print(f"  R4 sanity vs ORCH ({er}x / {ec}x): "
              f"delta {d_r:.3f} / {d_c:.3f}  -> {'PASS' if ok else 'FAIL'}")

        print(f"  {'annulus':>12s} {'n_edge':>9s} {'edge chroma':>12s} "
              f"{'n_flat':>10s} {'flat chroma':>12s}   (control)")
        for i in range(N_ANN):
            ne, ve = res["control"][1][i]
            nf, vf = res["control"][2][i]
            lo, hi = i / N_ANN, (i + 1) / N_ANN
            print(f"  {lo:.2f}-{hi:.2f}r {ne:9d} {ve:12.6f} {nf:10d} {vf:12.6f}")

        c_edge = trend([v for _, v in res["control"][1]])
        c_flat = trend([v for _, v in res["control"][2]])
        print(f"  R1 control EDGE outer/inner = {c_edge:.3f}  -> {verdict(c_edge)}")
        print(f"  R3 control FLAT outer/inner = {c_flat:.3f}  -> {verdict(c_flat)}")
        if np.isfinite(c_edge) and np.isfinite(c_flat) and c_flat > 0:
            print(f"     edge-over-flat trend ratio = {c_edge / c_flat:.3f} "
                  f"(>1 means edges rise faster than shading alone)")

        exc = []
        for i in range(N_ANN):
            _, vr = res["render"][1][i]
            _, vc = res["control"][1][i]
            exc.append(vr / vc if (np.isfinite(vr) and np.isfinite(vc) and vc > 0)
                       else float("nan"))
        print("  R2 excess (render/control) per annulus: "
              + ", ".join("nan" if not np.isfinite(x) else f"{x:.2f}" for x in exc))
        t = trend(exc)
        print(f"  R2 outer/inner = {t:.3f}  -> {verdict(t)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
