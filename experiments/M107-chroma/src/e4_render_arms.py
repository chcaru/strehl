"""E4 -- Instrument A on the three RENDER arms, holding the solve, the reference,
the election and the binary fixed.

  linear   default no-flag byte-frozen path: binned, camera-native LINEAR RGB.
           No demosaic, no colour matrix, no sRGB curve, no COSITE_SHIFT.
  binned   --srgb --binned: adds matrix + curve + M95's COSITE_SHIFT.
  demosaic --srgb (the shipped default): Malvar-He-Cutler at full sensor res.

Lattice convention per arm, in SOURCE SENSEL, stated because it is the whole
point of the comparison:

  linear        : one output px = one 2x2 quad. R sits at the quad's (0,0)
                  corner, G is the two-green mean at the centre (0.25,0.25),
                  B at (0.5,0.5) output px. This is M95's geometry, uncorrected.
  binned        : SAME construction, but `develop_binned` (image_out.rs:302-304)
                  resamples red by +COSITE_SHIFT and blue by -COSITE_SHIFT with
                  COSITE_SHIFT = 0.25 binned px, so R and B are carried ONTO the
                  quad centre.  All three channels are therefore CO-SITED on
                  this arm and its offsets are equal.
                  This correction was found by initially giving `binned` the
                  uncorrected offsets, which manufactured an R-B error of
                  exactly 0.5 output px = 1.0 source sensel -- the full size of
                  the correction, double-counted.  The wrong version is kept
                  reachable as OFFSETS_UNCORRECTED so the size of the mistake
                  can be reproduced rather than merely asserted.
  demosaic      : every channel is estimated at every site, so all three are
                  co-sited by construction -- offsets equal.

A displacement of D output px is D * cov source sensel on the demosaic arm and
2 * D * cov source sensel on the binned arms, where cov is the coverage rescale
the render log printed.
"""

import sys, os, json
import numpy as np
import tifffile

sys.path.insert(0, os.path.dirname(__file__))
from common import fit_plane_esf, dump, OUT
from edges import spread_by_radius

R = r"C:\dev\strehl-out\M107-chroma\renders"
GAL = r"C:\dev\strehl-out\ORCH-gallery3"
COV = {"tweezers-cpl": 0.9726, "leaf-2-cpl": 0.9344, "bee-3-cpl": 0.9315}

# per-channel sample offset within one OUTPUT pixel, in output px
OFFSETS = {
    "linear":   {"R": (0.0, 0.0), "G": (0.25, 0.25), "B": (0.5, 0.5)},
    # COSITE_SHIFT has already carried R and B onto the quad centre here.
    "binned":   {"R": (0.25, 0.25), "G": (0.25, 0.25), "B": (0.25, 0.25)},
    "demosaic": {"R": (0.0, 0.0), "G": (0.0, 0.0),   "B": (0.0, 0.0)},
}
# The wrong table, kept so the double-count can be reproduced on demand:
# giving `binned` the uncorrected offsets manufactures 1.0 sensel of R-B error.
OFFSETS_UNCORRECTED = dict(OFFSETS, binned=OFFSETS["linear"])
SENSEL_PER_PX = {"linear": 2.0, "binned": 2.0, "demosaic": 1.0}


def srgb_to_linear(v):
    v = np.asarray(v, dtype=np.float64)
    return np.where(v <= 0.04045, v / 12.92, ((v + 0.055) / 1.055) ** 2.4)


def load_arm(stack, arm):
    if arm == "demosaic":
        p = os.path.join(GAL, f"{stack}.tif")
    else:
        p = os.path.join(R, f"{stack}-{arm}.tif")
    img = tifffile.imread(p).astype(np.float64) / 65535.0
    if arm in ("binned", "demosaic"):
        img = srgb_to_linear(img)     # undo the transfer curve before fitting
    return img, p


def esf_arm(img, arm, x0, y0, size, dmax=12.0):
    roi = img[y0:y0 + size, x0:x0 + size, :]
    g = roi[:, :, 1]
    gy, gx = np.gradient(g)
    mag = np.hypot(gx, gy)
    m = mag >= np.percentile(mag, 90.0)
    if m.sum() < 32:
        return None
    ang2 = np.arctan2(2 * gx[m] * gy[m], gx[m] ** 2 - gy[m] ** 2)
    w = mag[m] ** 2
    if w.sum() <= 0:
        return None
    a = 0.5 * np.arctan2((w * np.sin(ang2)).sum(), (w * np.cos(ang2)).sum())
    n = np.array([np.cos(a), np.sin(a)])
    yy, xx = np.nonzero(m)
    off = OFFSETS[arm]
    # place the centroid on the GREEN lattice, which is where it was measured
    p = np.array([(w * xx).sum() / w.sum() + off["G"][0],
                  (w * yy).sum() / w.sum() + off["G"][1]])
    ys, xs = (np.arange(roi.shape[0], dtype=np.float64),
              np.arange(roi.shape[1], dtype=np.float64))
    out = {}
    for ci, cn in enumerate(("R", "G", "B")):
        X, Y = np.meshgrid(xs + off[cn][0], ys + off[cn][1])
        f = fit_plane_esf(roi[:, :, ci], X, Y, n, p, dmax=dmax)
        if f is None:
            return None
        out[cn] = f
    return {"planes": out, "normal": [float(n[0]), float(n[1])],
            "contrast": float(np.percentile(g, 98) - np.percentile(g, 2))}


def find_rois(img, size, stride, min_contrast, margin=64, top=2000):
    from scipy.ndimage import uniform_filter
    H, W, _ = img.shape
    out = []
    for y0 in range(margin, H - size - margin, stride):
        for x0 in range(margin, W - size - margin, stride):
            g = img[y0:y0 + size, x0:x0 + size, 1]
            c = float(np.percentile(g, 98) - np.percentile(g, 2))
            if c < min_contrast:
                continue
            gy, gx = np.gradient(g)
            jxx, jyy, jxy = (uniform_filter(a, 3) for a in (gx * gx, gy * gy, gx * gy))
            tr = jxx + jyy
            det = jxx * jyy - jxy * jxy
            disc = np.sqrt(np.maximum(tr * tr - 4 * det, 0))
            coh = np.divide(disc, tr, out=np.zeros_like(tr), where=tr > 1e-12)
            mag = np.hypot(gx, gy)
            m = mag >= np.percentile(mag, 90)
            ch = float(coh[m].mean())
            if ch < 0.80:
                continue
            yy, xx = np.nonzero(m)
            ww = mag[yy, xx] ** 2
            mx, my = (ww * xx).sum() / ww.sum(), (ww * yy).sum() / ww.sum()
            dx, dy = xx - mx, yy - my
            cxx = (ww * dx * dx).sum() / ww.sum()
            cyy = (ww * dy * dy).sum() / ww.sum()
            cxy = (ww * dx * dy).sum() / ww.sum()
            t2, d2 = cxx + cyy, cxx * cyy - cxy * cxy
            lam = 0.5 * (t2 - np.sqrt(max(t2 * t2 - 4 * d2, 0)))
            st = float(np.sqrt(max(lam, 0)))
            if st > 1.6:
                continue
            out.append({"x0": x0, "y0": y0, "size": size, "contrast": c,
                        "coherence": ch, "straight": st,
                        "score": c * ch / (0.5 + st)})
    out.sort(key=lambda d: -d["score"])
    return out[:top]


def run(stack, arms=("linear", "binned", "demosaic"), nrois=40):
    res = {}
    # ROIs are chosen ONCE, on the `linear` arm's green channel, and reused for
    # every arm at the matching scale -- so the three arms are compared on the
    # same edges rather than on whichever edges each arm happened to like.
    base, bp = load_arm(stack, "linear")
    H, W, _ = base.shape
    cands = find_rois(base, size=48, stride=96, min_contrast=0.010)
    sel = spread_by_radius(cands, W / 2.0, H / 2.0, nbins=8, per_bin=8)[:nrois]
    print(f"  {stack}: {len(cands)} candidate ROIs -> {len(sel)} kept")
    for arm in arms:
        img, path = load_arm(stack, arm)
        f = img.shape[1] / W          # 1.0 for binned arms, 2.0 for demosaic
        rows = []
        for c in sel:
            size = int(48 * f)
            x0, y0 = int(c["x0"] * f), int(c["y0"] * f)
            e = esf_arm(img, arm, x0, y0, size, dmax=12.0 * f)
            if e is None:
                continue
            P = e["planes"]
            k = SENSEL_PER_PX[arm] * COV[stack] / f
            rows.append({
                "stack": stack, "arm": arm, "x0": x0, "y0": y0,
                "radius": c["radius"] * f, "rx": c["rx"] * f, "ry": c["ry"] * f,
                "contrast": e["contrast"], "normal": e["normal"],
                # everything below is in SOURCE SENSEL
                "dR": (P["R"]["d0"] - P["G"]["d0"]) * k,
                "dB": (P["B"]["d0"] - P["G"]["d0"]) * k,
                "wG": P["G"]["w"] * k,
                "wR": (P["R"]["w"] - P["G"]["w"]) * k,
                "wB": (P["B"]["w"] - P["G"]["w"]) * k,
                "rms_amp": max(P[c2]["rms"] / max(P[c2]["amp"], 1e-12)
                               for c2 in ("R", "G", "B")),
                "d0_max": max(abs(P[c2]["d0"]) for c2 in ("R", "G", "B")) / f,
                "w_min": min(P[c2]["w"] for c2 in ("R", "G", "B")) * k,
                "w_max": max(P[c2]["w"] for c2 in ("R", "G", "B")) * k,
            })
        res[arm] = rows
        print(f"    {arm:9s} n={len(rows)}  file={os.path.basename(path)}")
    return res


if __name__ == "__main__":
    out = {}
    for s in ("tweezers-cpl", "leaf-2-cpl", "bee-3-cpl"):
        print(f"== {s} ==")
        out[s] = run(s)
    dump("e4_render_arms", out)
