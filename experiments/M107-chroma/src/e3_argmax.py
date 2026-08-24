"""E3 -- per-channel argmax over the focus stack. The core experiment for
hypothesis (b), longitudinal (axial) chromatic aberration.

Instrument B. For every frame k and every CFA plane c, a focus response
F_c(x,y,k) = box-mean of Sobel gradient energy. Per pixel, per plane, the
sub-frame argmax by parabolic refinement gives four index maps.

  k_R - kG  and  k_B - kG        the signal          (kG = mean of the two greens)
  k_G1 - k_G2                    the NULL

The null is the whole design. G1 and G2 are the SAME WAVELENGTH on DIFFERENT
lattice sites with INDEPENDENT noise, so it carries every channel-dependent-SNR,
lattice and estimator bias the instrument has and none of the axial-CA signal.
A signal that does not beat it is not a signal.

Frames are gathered through the same warp sidecar the render used, so a fixed
output pixel follows one scene point.
"""

import sys, os, json, time
import numpy as np
from scipy.ndimage import uniform_filter, map_coordinates, sobel

sys.path.insert(0, os.path.dirname(__file__))
from common import frames, dump, OUT, PLANES

WIN = 27          # plane px, matching the shipped box_mean_27 support

# CFA site of each plane within the 2x2 quad, as (x_offset, y_offset) in sensel.
# RGGB per CfaPlane::rggb_at, confirmed against rawpy raw_pattern [[0,1],[3,2]].
SITE = {"R": (0, 0), "G1": (1, 0), "G2": (0, 1), "B": (1, 1)}


def read_warpmap(path):
    """Parse a strehl sidecar. Returns (meta, list of (a_complex, b_complex) or None)."""
    meta, warps = {}, []
    import struct
    def f64(h):
        return struct.unpack(">d", bytes.fromhex(h))[0]
    for line in open(path):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        t = line.split()
        if t[0] in ("stack-name", "stack-digest", "frames", "plane", "reference",
                    "strategy", "resampler"):
            meta[t[0]] = t[1]
            continue
        if t[0] == "strehl-warpmap" or t[0] in ("heldout-px", "cycle-floor-px", "note"):
            continue
        if len(t) >= 6 and t[1] in ("placed", "unplaced", "refused"):
            if t[1] != "placed":
                warps.append(None)
            else:
                a = complex(f64(t[2]), f64(t[3]))
                b = complex(f64(t[4]), f64(t[5]))
                warps.append((a, b))
    return meta, warps


def gather_planes(cfa, warp, px0, py0, pw, ph, order=3, _no_crop=False):
    """Sample the four CFA planes of `cfa` at reference plane coords, through `warp`.

    Plane coordinates are the strehl convention: one plane pixel per 2x2 quad.
    `warp` maps reference plane coords -> this frame's plane coords, as z -> a z + b.

    The source plane is CROPPED to the warped bounding box before interpolation:
    `map_coordinates(order=3)` spline-prefilters its whole input, so passing the
    full 3520x2344 plane costs ~20x more than passing the ~660x660 that is read.
    Verified equal to the uncropped result by control N1 in `e3_controls.py`
    (`python e3_controls.py n1`); pass `_no_crop=True` to take the slow path.
    """
    ys, xs = np.mgrid[py0:py0 + ph, px0:px0 + pw].astype(np.float64)
    if warp is None:
        sx, sy = xs, ys
    else:
        a, b = warp
        z = xs + 1j * ys
        w = a * z + b
        sx, sy = w.real, w.imag
    out = {}
    pad = 8
    for name, (ox, oy) in SITE.items():
        pl = cfa[oy::2, ox::2]
        if _no_crop:
            out[name] = map_coordinates(pl, [sy, sx], order=order, mode="nearest")
            continue
        x_lo = max(int(np.floor(sx.min())) - pad, 0)
        y_lo = max(int(np.floor(sy.min())) - pad, 0)
        x_hi = min(int(np.ceil(sx.max())) + pad, pl.shape[1])
        y_hi = min(int(np.ceil(sy.max())) + pad, pl.shape[0])
        sub = pl[y_lo:y_hi, x_lo:x_hi]
        out[name] = map_coordinates(sub, [sy - y_lo, sx - x_lo], order=order,
                                    mode="nearest")
    return out


def focus(plane):
    gx = sobel(plane, axis=1, mode="nearest")   # 2-D plane only -- rule 23
    gy = sobel(plane, axis=0, mode="nearest")
    return uniform_filter(gx * gx + gy * gy, WIN, mode="nearest")


def subframe_argmax(F):
    """F is (nk, ny, nx). Returns (k_hat, prominence, interior_mask, unimodal_mask)."""
    nk = F.shape[0]
    ki = F.argmax(axis=0)
    interior = (ki > 0) & (ki < nk - 1)
    kk = np.clip(ki, 1, nk - 2)
    I, J = np.ogrid[: F.shape[1], : F.shape[2]]
    y0 = F[kk - 1, I, J]
    y1 = F[kk, I, J]
    y2 = F[kk + 1, I, J]
    den = y0 - 2 * y1 + y2
    off = np.where(np.abs(den) > 1e-12, 0.5 * (y0 - y2) / np.where(den == 0, 1, den), 0.0)
    off = np.clip(off, -1.0, 1.0)
    k_hat = kk + off
    med = np.median(F, axis=0)
    prom = y1 / np.maximum(med, 1e-9)
    # unimodality: count local maxima above the half-height of the global peak
    lo = F.min(axis=0)
    thr = lo + 0.5 * (y1 - lo)
    up = (F[1:-1] > F[:-2]) & (F[1:-1] >= F[2:]) & (F[1:-1] > thr)
    nmax = up.sum(axis=0)
    return k_hat, prom, interior, nmax <= 1


def run(stack, sidecar, px0, py0, pw, ph, warp=True, order=3, tag=""):
    fs = frames(stack)
    meta, warps = read_warpmap(sidecar)
    assert int(meta["frames"]) == len(fs), (meta["frames"], len(fs))
    print(f"  {stack}: {len(fs)} frames, plane {meta['plane']}, ref {meta['reference']}, "
          f"warp={'ON' if warp else 'OFF'}")
    import rawpy
    F = {c: np.empty((len(fs), ph, pw), dtype=np.float32) for c in PLANES}
    t0 = time.time()
    for k, path in enumerate(fs):
        with rawpy.imread(path) as r:
            cfa = r.raw_image_visible.astype(np.float32)     # copy inside `with`
            black = float(np.mean(r.black_level_per_channel))
        cfa -= black
        pls = gather_planes(cfa, warps[k] if warp else None, px0, py0, pw, ph, order)
        for c in PLANES:
            F[c][k] = focus(pls[c].astype(np.float32))
        if k % 50 == 0:
            print(f"    frame {k}/{len(fs)} ({time.time()-t0:.0f}s)")

    res = {}
    for c in PLANES:
        k_hat, prom, interior, uni = subframe_argmax(F[c])
        res[c] = {"k": k_hat, "prom": prom, "interior": interior, "uni": uni}

    conf = np.ones((ph, pw), bool)
    for c in PLANES:
        conf &= res[c]["interior"] & res[c]["uni"] & (res[c]["prom"] >= 3.0)
    # drop the box-filter border, which sees outside the ROI
    m = WIN
    edge = np.zeros((ph, pw), bool); edge[m:-m, m:-m] = True
    conf &= edge

    kG = 0.5 * (res["G1"]["k"] + res["G2"]["k"])
    dR = res["R"]["k"] - kG
    dB = res["B"]["k"] - kG
    null = res["G1"]["k"] - res["G2"]["k"]

    out = {
        "stack": stack, "tag": tag, "warp": warp, "order": order,
        "roi": [px0, py0, pw, ph], "nframes": len(fs),
        "reference": int(meta["reference"]),
        "confident_px": int(conf.sum()), "total_px": int(edge.sum()),
        "confident_frac": float(conf.sum() / max(edge.sum(), 1)),
        "median_dR": float(np.median(dR[conf])) if conf.any() else None,
        "median_dB": float(np.median(dB[conf])) if conf.any() else None,
        "median_null": float(np.median(null[conf])) if conf.any() else None,
        "mean_dR": float(np.mean(dR[conf])) if conf.any() else None,
        "mean_dB": float(np.mean(dB[conf])) if conf.any() else None,
        "mean_null": float(np.mean(null[conf])) if conf.any() else None,
        "iqr_dR": [float(np.percentile(dR[conf], 25)), float(np.percentile(dR[conf], 75))],
        "iqr_dB": [float(np.percentile(dB[conf], 25)), float(np.percentile(dB[conf], 75))],
        "iqr_null": [float(np.percentile(null[conf], 25)), float(np.percentile(null[conf], 75))],
    }
    npz = os.path.join(OUT, "json", f"e3_{stack}_{tag}.npz")
    np.savez_compressed(npz, kR=res["R"]["k"], kG1=res["G1"]["k"], kG2=res["G2"]["k"],
                        kB=res["B"]["k"], conf=conf, dR=dR, dB=dB, null=null)
    out["npz"] = npz
    print(f"    confident {out['confident_frac']*100:.2f}% of {out['total_px']} px")
    print(f"    median k_R-kG = {out['median_dR']:+.4f} frames")
    print(f"    median k_B-kG = {out['median_dB']:+.4f} frames")
    print(f"    median NULL k_G1-k_G2 = {out['median_null']:+.4f} frames")
    return out


if __name__ == "__main__":
    R = r"C:\dev\strehl-out\M107-chroma\renders"
    jobs = [
        # stack, sidecar, plane-x0, plane-y0, w, h, tag
        ("tweezers-cpl", f"{R}\\tweezers-cpl-warpmap.txt", 1200, 900, 512, 512, "body"),
        ("bee-3-cpl", f"{R}\\bee-3-cpl-warpmap.txt", 400, 1300, 512, 512, "leg-hairs"),
        ("leaf-2-cpl", f"{R}\\leaf-2-cpl-warpmap.txt", 900, 700, 512, 512, "veins"),
    ]
    allout = []
    for (s, side, x, y, w, h, tag) in jobs:
        print(f"== {s} [{tag}] ==")
        allout.append(run(s, side, x, y, w, h, warp=True, tag=tag))
    dump("e3_argmax", allout)
