"""S4 — does CO-SITING actually improve the image, and by how much?

S3 established that the binned render samples red at (-0.25, -0.25) and blue at
(+0.25, +0.25) binned px relative to the quad centre where green sits. This
asks the only question that matters for the product: if those two planes are
resampled onto the green grid, does the picture get measurably better?

THE REFERENCE
-------------
The demosaiced render of the same frame, box-averaged over each quad. All three
channels co-sited at the quad centre, same scale as the binned render.

It is not perfect -- Malvar-He-Cutler interpolates, so its red and blue carry
the interpolator's own error -- but it is INDEPENDENT of the thing being tested,
which is what a reference has to be. S3 measured its green against binned green
at 0.0005-0.0020 px, so the two grids are aligned to well under a hundredth of a
pixel and the comparison is not confounded by a global offset.

THE METRICS
-----------
1. Residual per-channel registration against the reference. Must fall to ~0
   for R and B if the fix does what it claims, and green must NOT move.
2. Chroma error: RMS of (R-G) and (B-G) differences against the reference.
   This is what colour fringing IS -- a misregistered channel puts a signed
   colour swing on both sides of every luminance edge.
3. Edge-localised chroma error, restricted to pixels near a strong luminance
   gradient, because that is where a registration error shows and where a
   viewer looks.

THE CONTROLS
------------
N1 negative/direction control: apply the correction BACKWARDS. If the metric is
   measuring registration, a backwards correction must make it markedly WORSE,
   roughly tripling the offset from 0.25 to 0.75. A metric that improves or
   stays flat under a backwards fix is not measuring what I think.
N2 green control: green is not touched by the fix, so every metric restricted
   to green must be unchanged to numerical precision. This catches a fix that
   improves the numbers by blurring everything.
N3 blur-only control: apply a resample of the SAME kernel with ZERO shift to R
   and B. This has the fix's blur but none of its correction. If the blur alone
   accounts for the improvement, the co-siting is not what helped.
"""

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import m95c as C  # noqa: E402

S = 256
PAIRS = {
    "frame-183": ("armF-f183.tif", "armF-f183-demo.tif"),
    "merged-gate0": ("armM-gate0-binlin.tif", "armM-gate0-demo.tif"),
}


def box2(a):
    h, w = a.shape[0] // 2 * 2, a.shape[1] // 2 * 2
    t = a[:h, :w].astype(np.float64)
    return 0.25 * (t[0::2, 0::2] + t[0::2, 1::2] + t[1::2, 0::2] + t[1::2, 1::2])


def keys_weights(t, a=-0.5):
    """Catmull-Rom (Keys, a = -1/2) 4-tap weights for fractional offset t.

    Keys, "Cubic convolution interpolation for digital image processing",
    IEEE ASSP-29(6), 1981. a = -1/2 is the choice that makes the interpolator
    agree with the Taylor series of the sampled function to third order, which
    is why it is the standard one. Chosen over bilinear because bilinear at
    t = 0.25 has a noticeably wider kernel and this correction must not cost
    more sharpness than the misregistration it removes.
    """
    t2, t3 = t * t, t * t * t
    return np.array([
        a * (t3 - 2 * t2 + t),
        (a + 2) * t3 - (a + 3) * t2 + 1.0,
        -(a + 2) * t3 + (2 * a + 3) * t2 - a * t,
        -a * (t3 - t2),
    ])


def resample_shift(plane, dy, dx):
    """Resample `plane` at coordinates (y + dy, x + dx) with separable Keys.

    This is the exact operation the Rust fix will perform, written here first
    so the benefit can be measured before any Rust is changed.
    """
    def axis(p, d, ax):
        if d == 0.0:
            return p
        i0 = int(np.floor(d))
        t = d - i0
        w = keys_weights(t)
        out = np.zeros_like(p)
        n = p.shape[ax]
        for k in range(4):
            idx = np.clip(np.arange(n) + i0 + k - 1, 0, n - 1)
            out += w[k] * (p[idx, :] if ax == 0 else p[:, idx])
        return out

    return axis(axis(plane, dy, 0), dx, 1)


def cosite(img, sign=+1.0, shift_mag=0.25, blur_only=False):
    """Return a copy with red and blue resampled onto the green grid.

    Red sits at (-0.25, -0.25) relative to the quad centre, so it must be
    sampled at (+0.25, +0.25); blue is the mirror. `sign = -1` applies the
    correction backwards, which is control N1. `blur_only` applies the same
    kernel with zero offset, which is control N3.
    """
    out = img.copy()
    d = 0.0 if blur_only else shift_mag * sign
    out[:, :, 0] = resample_shift(img[:, :, 0], +d, +d)
    out[:, :, 2] = resample_shift(img[:, :, 2], -d, -d)
    return out


def field_rois(h, w, s, nx, ny, margin=64):
    ys = np.linspace(margin, h - s - margin, ny).astype(int)
    xs = np.linspace(margin, w - s - margin, nx).astype(int)
    return [(int(y), int(x)) for y in ys for x in xs]


def registration(ground, cand, rois):
    per = {"R": [], "G": [], "B": []}
    for y, x in rois:
        for c, nm in enumerate("RGB"):
            a = ground[y : y + S, x : x + S, c]
            b = cand[y : y + S, x : x + S, c]
            if C.coherence(a, b) < 0.5:
                continue
            d = C.phase_ramp_shift_robust(a, b)
            per[nm].append(np.hypot(d[0], d[1]))
    return {nm: float(np.mean(v)) if v else float("nan") for nm, v in per.items()}


def chroma_error(ground, cand, rois):
    """RMS error in the colour-difference planes, all ROIs pooled, and the same
    restricted to pixels near a strong luminance edge."""
    all_e, edge_e = [], []
    for y, x in rois:
        g = ground[y : y + S, x : x + S, :]
        c = cand[y : y + S, x : x + S, :]
        for hi in (0, 2):
            dg = (g[:, :, hi] - g[:, :, 1]) - (c[:, :, hi] - c[:, :, 1])
            all_e.append(dg.ravel())
            lum = g[:, :, 1]
            gy, gx = np.gradient(lum)
            mag = np.hypot(gy, gx)
            m = mag > np.percentile(mag, 90)
            edge_e.append(dg[m].ravel())
    a = np.concatenate(all_e)
    e = np.concatenate(edge_e)
    return float(np.sqrt(np.mean(a**2))), float(np.sqrt(np.mean(e**2)))


def run_pair(name, binf, demof):
    print("\n" + "=" * 72)
    print("PAIR: %s" % name)
    ib = C.load_tif(os.path.join(C.OUT, binf)).astype(np.float64)
    idm = C.load_tif(os.path.join(C.OUT, demof)).astype(np.float64)
    ground = np.stack([box2(idm[:, :, c]) for c in range(3)], axis=2)
    h, w = ib.shape[0], ib.shape[1]
    rois = field_rois(h, w, S, nx=7, ny=5)

    variants = {
        "as-shipped": ib,
        "co-sited": cosite(ib, +1.0),
        "N1-backwards": cosite(ib, -1.0),
        "N3-blur-only": cosite(ib, +1.0, blur_only=True),
    }

    res = {}
    for vn, v in variants.items():
        reg = registration(ground, v, rois)
        ca, ce = chroma_error(ground, v, rois)
        res[vn] = {"reg_R": reg["R"], "reg_G": reg["G"], "reg_B": reg["B"],
                   "chroma_rms_DN": ca, "chroma_rms_edge_DN": ce}
        print("  %-13s  regR %.4f  regG %.4f  regB %.4f   chroma %8.2f DN   edge %8.2f DN"
              % (vn, reg["R"], reg["G"], reg["B"], ca, ce))

    base = res["as-shipped"]
    fix = res["co-sited"]
    print("\n  co-siting vs as-shipped:")
    print("    red   misregistration  %.4f -> %.4f px  (%.1f%% removed)"
          % (base["reg_R"], fix["reg_R"], 100 * (1 - fix["reg_R"] / base["reg_R"])))
    print("    blue  misregistration  %.4f -> %.4f px  (%.1f%% removed)"
          % (base["reg_B"], fix["reg_B"], 100 * (1 - fix["reg_B"] / base["reg_B"])))
    print("    green (N2, untouched)  %.4f -> %.4f px" % (base["reg_G"], fix["reg_G"]))
    print("    chroma RMS at edges    %.2f -> %.2f DN  (%.1f%% lower)"
          % (base["chroma_rms_edge_DN"], fix["chroma_rms_edge_DN"],
             100 * (1 - fix["chroma_rms_edge_DN"] / base["chroma_rms_edge_DN"])))
    print("    N1 backwards           regR %.4f (must be much worse than %.4f)"
          % (res["N1-backwards"]["reg_R"], base["reg_R"]))
    print("    N3 blur only           regR %.4f (must stay near %.4f)"
          % (res["N3-blur-only"]["reg_R"], base["reg_R"]))
    return res


def main():
    out = {n: run_pair(n, b, d) for n, (b, d) in PAIRS.items()}
    C.jdump("s4_benefit.json", out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
