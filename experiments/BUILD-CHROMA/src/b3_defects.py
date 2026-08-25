"""B3 -- do the measured per-channel focus offsets explain the two visible
defects?

Two defects, two independent tests, both run on MEASUREMENT-GRADE files:
`strehl stack --gate 4` with no other flag, which is documented as "BINNED,
LINEAR, CAMERA-NATIVE RGB: each output pixel is one real sensor quad,
R = R, G = (G1+G2)/2, B = B ... with white balance but NO colour matrix ...
It is byte-frozen." No demosaic, no colour matrix, no transfer curve, so no
cross-channel operator sits between the sensor and the number.

The gallery JPEGs are `--srgb --demosaic` and the CLI says of them "Do not
measure either file." They are used here ONLY to locate defects by eye.

RULE 1 IS ENFORCED: every TIFF is read with `tifffile` and asserted `uint16`.
`PIL.Image.open` silently narrows a 16-bit RGB TIFF to 8-bit.

Test A -- the magenta rim on `coffee-bean`.
    Sample R, G, B along the OUTWARD NORMAL of the bean silhouette at many
    boundary points, and split those points by field position. The
    discrimination is the point:
      * axial CA acts through a per-channel BLUR difference, which is
        isotropic. It predicts the same rim colour on every side of the
        subject, and no reversal anywhere.
      * lateral CA acts through a per-channel radial DISPLACEMENT. It predicts
        a rim that reverses sign across the optical centre and vanishes at it.
    A single-frame control at the same edge separates "already in the optics"
    from "made by the merge".

Test B -- the rainbow speckle on `lavendar-cpl`.
    Trace thin bright structures and measure the chroma (R/G, B/G) ALONG each
    one. The discrimination:
      * axial CA is a smooth, spatially uniform blur difference. Along a single
        hair it predicts a CONSTANT chroma offset of consistent sign.
      * the observed defect is described as alternating orange/blue/cyan
        segments, i.e. chroma that REVERSES along the structure at a short
        correlation length. That is not what a uniform blur difference makes.
    So the sign-flip rate along a hair is the discriminating statistic, and it
    is compared against the same statistic in a single-frame control.
"""

import os
import sys

import numpy as np
import tifffile
from scipy.ndimage import (binary_erosion, binary_dilation, gaussian_filter,
                           map_coordinates, uniform_filter)

sys.path.insert(0, os.path.dirname(__file__))
from common import OUT, read_cfa, planes_of, frames, dump

REND = os.path.join(OUT, "render")


def read16(path):
    """Read a 16-bit TIFF. Rule 1: never PIL, and assert the dtype."""
    a = tifffile.imread(path)
    assert a.dtype == np.uint16, f"{path} is {a.dtype}, expected uint16"
    assert a.ndim == 3 and a.shape[2] == 3, f"{path} shape {a.shape}"
    return a.astype(np.float64)


def single_frame_binned(stack, k):
    """The documented default output composition, built from one raw frame.

    R = R, G = (G1+G2)/2, B = B, one output pixel per 2x2 quad, with camera
    white balance and no colour matrix -- the same recipe the byte-frozen
    measurement render uses, applied to a single frame instead of a merge.
    This is the control that separates optics from merge.
    """
    import rawpy
    fs = frames(stack)
    with rawpy.imread(fs[k]) as r:
        wb = np.array(r.camera_whitebalance, float)
    pl = planes_of(read_cfa(fs[k]))
    g = 0.5 * (pl["G1"].astype(np.float64) + pl["G2"].astype(np.float64))
    rgb = np.stack([pl["R"].astype(np.float64) * (wb[0] / wb[1]),
                    g,
                    pl["B"].astype(np.float64) * (wb[2] / wb[1])], -1)
    return rgb


# ------------------------------------------------------------------ A -----
def silhouette_normals(img, nsample=4000, seed=3):
    """Boundary points of the dark subject, with outward normals."""
    lum = img.sum(2)
    thr = 0.5 * (np.percentile(lum, 5) + np.percentile(lum, 95))
    dark = gaussian_filter(lum, 4) < thr
    # keep the single largest blob
    from scipy.ndimage import label, find_objects
    lab, n = label(dark)
    if n == 0:
        raise SystemExit("no subject found")
    sizes = np.bincount(lab.ravel())
    sizes[0] = 0
    dark = lab == sizes.argmax()
    edge = dark ^ binary_erosion(dark, iterations=1)
    ys, xs = np.nonzero(edge)
    rng = np.random.default_rng(seed)
    if ys.size > nsample:
        sel = rng.choice(ys.size, nsample, replace=False)
        ys, xs = ys[sel], xs[sel]
    # outward normal = gradient of a smoothed mask, pointing out of the subject
    sm = gaussian_filter(dark.astype(float), 6)
    gy, gx = np.gradient(sm)
    ny, nx = -gy[ys, xs], -gx[ys, xs]
    m = np.hypot(ny, nx)
    ok = m > 1e-3
    return ys[ok], xs[ok], ny[ok] / m[ok], nx[ok] / m[ok]


def normal_profiles(img, ys, xs, ny, nx, lo=-24, hi=24):
    """Sample each channel along the outward normal. Bilinear, but this is a
    DISPLAY-space profile, not the focus statistic -- rule 6 governs the
    registration of the focus measurement, not the reading of an edge shape."""
    d = np.arange(lo, hi + 1, 1.0)
    prof = np.empty((3, d.size, ys.size))
    for i, dd in enumerate(d):
        sy = ys + ny * dd
        sx = xs + nx * dd
        for c in range(3):
            prof[c, i] = map_coordinates(img[:, :, c], [sy, sx], order=1,
                                         mode="nearest")
    return d, prof


def rim_report(img, label, cx, cy, nsample=4000):
    ys, xs, ny, nx = silhouette_normals(img, nsample)
    d, prof = normal_profiles(img, ys, xs, ny, nx)
    R, G, B = prof
    eps = 1e-9
    # chroma relative to green, in linear camera-native space
    rg = R / np.maximum(G, eps)
    bg = B / np.maximum(G, eps)
    # normalise each point's chroma to its own far-background value so that
    # subject colour cannot masquerade as a fringe
    far = d >= 18
    rg = rg / np.maximum(rg[far].mean(0, keepdims=True), eps)
    bg = bg / np.maximum(bg[far].mean(0, keepdims=True), eps)

    # split by side of the optical centre, along the dominant field axis
    right = xs > cx
    left = ~right
    rad = np.hypot(xs - cx, ys - cy)
    inner = rad < np.median(rad)

    def curve(sel):
        return {"n": int(sel.sum()),
                "rg": np.median(rg[:, sel], 1).tolist(),
                "bg": np.median(bg[:, sel], 1).tolist()}

    out = {"label": label, "d": d.tolist(), "n_points": int(ys.size),
           "all": curve(np.ones(ys.size, bool)),
           "left": curve(left), "right": curve(right),
           "inner": curve(inner), "outer": curve(~inner)}
    # peak excess just outside the edge
    band = (d >= 1) & (d <= 8)
    out["peak_rg_excess"] = float(np.median(rg[:, :], 1)[band].max() - 1.0)
    out["peak_bg_excess"] = float(np.median(bg[:, :], 1)[band].max() - 1.0)
    out["rg_at_peak_left"] = float(np.array(out["left"]["rg"])[band].max() - 1)
    out["rg_at_peak_right"] = float(np.array(out["right"]["rg"])[band].max() - 1)
    out["bg_at_peak_left"] = float(np.array(out["left"]["bg"])[band].max() - 1)
    out["bg_at_peak_right"] = float(np.array(out["right"]["bg"])[band].max() - 1)
    return out


# ------------------------------------------------------------------ B -----
def hair_chroma(img, label, min_len=40, nmax=400, seed=5):
    """Chroma along thin bright structures, and how often its sign flips.

    Ridges are found on GREEN alone (so the selection cannot be biased by the
    chroma being measured), as pixels that are locally much brighter than a
    background estimate and are thin.

    The float64 cast on entry is load-bearing, not cosmetic. `uniform_filter`
    preserves its input dtype, so on a uint16 image the background estimate is
    truncated to uint16 and `G - bg` then WRAPS AROUND wherever the pixel is
    darker than its neighbourhood -- turning every negative into a value near
    65535. The ridge threshold is derived from that array's own standard
    deviation, so the failure is silent and self-consistent: it reports zero
    ridge pixels rather than raising. This is rule 1's hazard in a different
    costume (a dtype quietly degrading a measurement), and it cost a run here.
    """
    img = np.asarray(img, dtype=np.float64)
    G = img[:, :, 1]
    bg = uniform_filter(G, 25)
    hp = G - bg
    s = hp[hp > 0].std()
    ridge = hp > 3.0 * s
    # thin: survives no erosion, i.e. remove blobs
    thin = ridge & ~binary_erosion(ridge, iterations=2)
    ys, xs = np.nonzero(thin)
    if ys.size < 200:
        return {"label": label, "n": int(ys.size), "verdict": "too few ridge px"}

    eps = 1e-9
    rg = img[:, :, 0] / np.maximum(G, eps)
    bgc = img[:, :, 2] / np.maximum(G, eps)
    # local background chroma, so subject colour is removed and only the
    # edge-scale departure survives (the same high-pass logic M107 section 6 used)
    rg_hp = rg - uniform_filter(rg, 25)
    bg_hp = bgc - uniform_filter(bgc, 25)

    v_rg = rg_hp[ys, xs]
    v_bg = bg_hp[ys, xs]

    # trace short runs of connected ridge pixels and count sign flips along them
    from scipy.ndimage import label as cclabel
    lab, n = cclabel(thin)
    rng = np.random.default_rng(seed)
    flips, lens, consistency = [], [], []
    order = rng.permutation(np.arange(1, n + 1))
    for li in order:
        m = lab == li
        c = int(m.sum())
        if c < min_len:
            continue
        yy, xx = np.nonzero(m)
        # order along the structure's principal axis
        p = np.stack([yy - yy.mean(), xx - xx.mean()], 1)
        u, s_, vt = np.linalg.svd(p, full_matrices=False)
        t = p @ vt[0]
        o = np.argsort(t)
        vv = rg_hp[yy[o], xx[o]]
        sg = np.sign(vv)
        sg = sg[sg != 0]
        if sg.size < 8:
            continue
        flips.append(float((np.diff(sg) != 0).mean()))
        lens.append(int(c))
        consistency.append(float(max((sg > 0).mean(), (sg < 0).mean())))
        if len(flips) >= nmax:
            break

    return {"label": label, "n_ridge_px": int(ys.size),
            "n_structures": int(len(flips)),
            "median_run_len": float(np.median(lens)) if lens else None,
            "rg_hp_sd": float(v_rg.std()), "bg_hp_sd": float(v_bg.std()),
            "rg_hp_p05": float(np.percentile(v_rg, 5)),
            "rg_hp_p95": float(np.percentile(v_rg, 95)),
            "frac_rg_positive": float((v_rg > 0).mean()),
            "frac_bg_positive": float((v_bg > 0).mean()),
            "median_sign_flip_rate": float(np.median(flips)) if flips else None,
            "median_sign_consistency": float(np.median(consistency)) if consistency else None}


if __name__ == "__main__":
    what = sys.argv[1] if len(sys.argv) > 1 else "all"
    out = {}

    if what in ("all", "rim"):
        p = os.path.join(REND, "coffee-bean-merge.tif")
        img = read16(p)
        h, w, _ = img.shape
        print(f"-- rim: {p} {img.shape} uint16-verified")
        out["rim_merge"] = rim_report(img, "coffee-bean merge", w / 2, h / 2)
        r = out["rim_merge"]
        print(f"   merged: peak R/G excess {r['peak_rg_excess']*100:+.2f}%  "
              f"B/G excess {r['peak_bg_excess']*100:+.2f}%")
        print(f"   left  R/G {r['rg_at_peak_left']*100:+.2f}%  "
              f"B/G {r['bg_at_peak_left']*100:+.2f}%")
        print(f"   right R/G {r['rg_at_peak_right']*100:+.2f}%  "
              f"B/G {r['bg_at_peak_right']*100:+.2f}%")

    if what in ("all", "hair"):
        p = os.path.join(REND, "lavendar-cpl-merge.tif")
        if os.path.exists(p):
            img = read16(p)
            print(f"-- hair: {p} {img.shape} uint16-verified")
            out["hair_merge"] = hair_chroma(img, "lavendar merge")
            print("   ", out["hair_merge"])

    dump("b3_defects", out)
