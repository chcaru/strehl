"""B3b -- the coffee-bean rim, examined properly.

B3's first pass found that in linear camera-native space the rim carries an
R/G excess and NO B/G excess at all. That is a strong discriminator on its own,
because the two candidate mechanisms predict different channel signatures:

  * axial CA (SYNTHESIS fact 1413) offsets BOTH red and blue from green, and on
    `coffee-bean` specifically by dR = -0.804 and dB = -0.359 frames. Blue's
    offset is 45% of red's, so an axial-driven rim must show a blue excess
    roughly half the red one.
  * lateral CA (SYNTHESIS fact 1414) is a radial magnification error of
    eps_R = -704.5 ppm in red against eps_B = +68.4 ppm in blue -- red is
    ~10x blue. A lateral-driven rim is red with essentially no blue.

This script adds the three things the first pass lacked:
  1. the RADIAL trend of the rim excess (lateral CA scales with radius; a blur
     difference does not),
  2. the LUMINANCE profile, so a chroma rim is not confused with a halo,
  3. a SINGLE-FRAME control built with the merge's own documented composition,
     which separates "already in the optics" from "made by the merge".

It also dumps the profiles so they can be plotted and looked at (rule 7).
"""

import os
import sys

import numpy as np
import tifffile

sys.path.insert(0, os.path.dirname(__file__))
from common import OUT, frames, dump
from b3_defects import read16, silhouette_normals, normal_profiles, single_frame_binned

REND = os.path.join(OUT, "render")


def analyse(img, label, nsample=6000):
    h, w, _ = img.shape
    cx, cy = w / 2.0, h / 2.0
    ys, xs, ny, nx = silhouette_normals(img, nsample)
    d, prof = normal_profiles(img, ys, xs, ny, nx)
    R, G, B = prof
    eps = 1e-9
    rg = R / np.maximum(G, eps)
    bg = B / np.maximum(G, eps)
    lum = R + 2 * G + B
    far = d >= 18
    rg = rg / np.maximum(rg[far].mean(0, keepdims=True), eps)
    bg = bg / np.maximum(bg[far].mean(0, keepdims=True), eps)
    lum = lum / np.maximum(lum[far].mean(0, keepdims=True), eps)

    rad = np.hypot(xs - cx, ys - cy)
    # is the outward normal pointing away from, or toward, the optical centre?
    radial_dot = (nx * (xs - cx) + ny * (ys - cy)) / np.maximum(rad, eps)

    band = (d >= 1) & (d <= 8)

    def peak(sel, arr):
        if sel.sum() < 30:
            return None
        m = np.median(arr[:, sel], 1)
        return float(m[band].max() - 1.0)

    out = {"label": label, "d": d.tolist(), "n": int(ys.size),
           "rg_all": np.median(rg, 1).tolist(),
           "bg_all": np.median(bg, 1).tolist(),
           "lum_all": np.median(lum, 1).tolist(),
           "peak_rg": peak(np.ones(ys.size, bool), rg),
           "peak_bg": peak(np.ones(ys.size, bool), bg),
           "peak_lum": peak(np.ones(ys.size, bool), lum),
           "radial_dot_median": float(np.median(radial_dot))}

    # radial bins -- lateral CA grows with radius, a blur difference does not
    qs = np.quantile(rad, np.linspace(0, 1, 5))
    qs[-1] += 1
    rb = []
    for i in range(4):
        s = (rad >= qs[i]) & (rad < qs[i + 1])
        rb.append({"r_lo": float(qs[i]), "r_hi": float(qs[i + 1]),
                   "r_mid": float(np.median(rad[s])) if s.any() else None,
                   "n": int(s.sum()),
                   "rg": peak(s, rg), "bg": peak(s, bg), "lum": peak(s, lum)})
    out["radial"] = rb

    # split by whether the normal points outward or inward relative to centre
    outward = radial_dot > 0.5
    inward = radial_dot < -0.5
    out["by_normal"] = {
        "outward": {"n": int(outward.sum()), "rg": peak(outward, rg),
                    "bg": peak(outward, bg), "lum": peak(outward, lum)},
        "inward": {"n": int(inward.sum()), "rg": peak(inward, rg),
                   "bg": peak(inward, bg), "lum": peak(inward, lum)}}
    return out


def show(o):
    print(f"\n--- {o['label']}  (n={o['n']} boundary points) ---")
    print(f"   peak just outside edge:  R/G {o['peak_rg']*100:+.2f}%   "
          f"B/G {o['peak_bg']*100:+.2f}%   LUM {o['peak_lum']*100:+.2f}%")
    print("   radial bins:   r_mid      n     R/G      B/G      LUM")
    for b in o["radial"]:
        f = lambda v: "   n/a" if v is None else f"{v*100:+6.2f}%"
        print(f"                 {b['r_mid']:7.0f} {b['n']:6d}  {f(b['rg'])} "
              f"{f(b['bg'])} {f(b['lum'])}")
    bn = o["by_normal"]
    for k in ("outward", "inward"):
        v = bn[k]
        f = lambda x: "n/a" if x is None else f"{x*100:+.2f}%"
        print(f"   normal {k:8s} n={v['n']:5d}  R/G {f(v['rg'])}  "
              f"B/G {f(v['bg'])}  LUM {f(v['lum'])}")


if __name__ == "__main__":
    out = {}
    merge = os.path.join(REND, "coffee-bean-merge.tif")
    img = read16(merge)
    print(f"merge {merge}  {img.shape}  uint16-verified")
    out["merge"] = analyse(img, "coffee-bean MERGE (linear camera-native)")
    show(out["merge"])

    # single-frame control, same composition recipe, no merge
    k = int(sys.argv[1]) if len(sys.argv) > 1 else None
    if k is None:
        k = len(frames("coffee-bean")) // 2
    sf = single_frame_binned("coffee-bean", k)
    print(f"\nsingle-frame control: frame index {k}  {sf.shape}")
    out["single_frame"] = analyse(sf, f"coffee-bean SINGLE FRAME k={k}")
    out["single_frame_index"] = k
    show(out["single_frame"])

    dump("b3b_rim", out)
