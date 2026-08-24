"""Phase A -- per-frame background level in SCENE coordinates.

The confounded measurement this replaces sampled fixed SENSOR patches. Under a
5% magnification change a corner patch sweeps ~230 px across the scene, so it
samples different scene content in every frame and any illumination gradient in
the background masquerades as photometric drift.

Here every patch centre is transported through the bracket's own alignment
placement, so the same scene point is sampled in every frame. Both variants are
recorded from the same decode, so the difference between them is the confound
and nothing else.

Patches are chosen by measurement, not by eye: a candidate grid is sampled in
every frame, and a patch is admitted only if it is smooth in EVERY frame. The
bee's wing is sharp in some frames and blurred in others but never smooth in
all of them, so structure is excluded by the criterion rather than by judgement.

Output: data/levels-<stack>.npz
"""
import glob
import os
import sys
import time
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import rawpy

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MACRO = r"D:\personal\macro"

# 64 quad px -> 128 sensor px on a side; ~4096 green photosites per patch.
HALF = 64
# Candidate grid, in plane (quad) coordinates, inset from the edge by enough
# that the warp never walks a patch off the sensor.
GRID_NX, GRID_NY = 21, 14
INSET = 0.86


# ---------------------------------------------------------------------------
# sidecar
# ---------------------------------------------------------------------------

def read_warpmap(path):
    """Parse a strehl warp sidecar. Returns (plane_w, plane_h, ref, warps).

    `warps[k]` is (a_re, a_im, b_re, b_im) or None for a refused frame. The
    hex bit patterns are authoritative; the trailing decimals are a comment.
    """
    plane = ref = None
    warps = {}
    n = None
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line or line.startswith("#"):
                continue
            tok = line.split()
            if tok[0] == "plane":
                w, h = tok[1].split("x")
                plane = (int(w), int(h))
            elif tok[0] == "reference":
                ref = int(tok[1])
            elif tok[0] == "frames":
                n = int(tok[1])
            elif tok[0] == "end":
                break
            elif tok[0].isdigit():
                idx = int(tok[0])
                if tok[1] == "placed":
                    vals = [np.frombuffer(bytes.fromhex(t), dtype=">f8")[0]
                            for t in tok[2:6]]
                    warps[idx] = tuple(float(v) for v in vals)
                else:
                    warps[idx] = None
    assert plane and ref is not None and n is not None, path
    return plane[0], plane[1], ref, [warps.get(i) for i in range(n)]


def apply_at(w, x, y, cx, cy):
    """strehl's Similarity::apply_at -- q = a*(p-c) + b, then + c."""
    a_re, a_im, b_re, b_im = w
    dx, dy = x - cx, y - cy
    qx = a_re * dx - a_im * dy + b_re
    qy = a_im * dx + a_re * dy + b_im
    return qx + cx, qy + cy


# ---------------------------------------------------------------------------
# per-frame worker
# ---------------------------------------------------------------------------

_G = {}


def _init(stack, centres, warps, cx, cy):
    _G["stack"] = stack
    _G["centres"] = centres
    _G["warps"] = warps
    _G["c"] = (cx, cy)


def _patch_stats(norm, gmask, r0, c0):
    """Median and relative spatial MAD of the green photosites in a patch."""
    sub = norm[r0:r0 + 2 * HALF, c0:c0 + 2 * HALF]
    gm = gmask[r0:r0 + 2 * HALF, c0:c0 + 2 * HALF]
    v = sub[gm]
    if v.size == 0:
        return np.nan, np.nan
    med = float(np.median(v))
    mad = float(np.median(np.abs(v - med)))
    return med, (mad / med if med > 1e-6 else np.nan)


def _one(args):
    k, path = args
    centres = _G["centres"]
    w = _G["warps"][k]
    cx, cy = _G["c"]
    with rawpy.imread(path) as r:
        raw = r.raw_image_visible.astype(np.float32)
        black = float(np.mean(r.black_level_per_channel))
        white = float(r.white_level)
        colors = r.raw_colors_visible
        norm = (raw - black) / (white - black)
        gmask = (colors == 1) | (colors == 3)
        H, W = norm.shape

    n = len(centres)
    scene_med = np.full(n, np.nan, dtype=np.float64)
    scene_mad = np.full(n, np.nan, dtype=np.float64)
    sensor_med = np.full(n, np.nan, dtype=np.float64)

    for i, (px, py) in enumerate(centres):
        # Sensor-fixed: the confounded variant, same patches, no warp.
        sr0 = int(round(2 * py)) - HALF
        sc0 = int(round(2 * px)) - HALF
        sr0 -= sr0 % 2
        sc0 -= sc0 % 2
        if 0 <= sr0 <= H - 2 * HALF and 0 <= sc0 <= W - 2 * HALF:
            sensor_med[i], _ = _patch_stats(norm, gmask, sr0, sc0)
        if w is None:
            continue
        # Scene-fixed: transport the centre through the placement.
        qx, qy = apply_at(w, px, py, cx, cy)
        r0 = int(round(2 * qy)) - HALF
        c0 = int(round(2 * qx)) - HALF
        # Round to an even offset so the same CFA phases are always inside.
        r0 -= r0 % 2
        c0 -= c0 % 2
        if 0 <= r0 <= H - 2 * HALF and 0 <= c0 <= W - 2 * HALF:
            scene_med[i], scene_mad[i] = _patch_stats(norm, gmask, r0, c0)
    return k, scene_med, scene_mad, sensor_med


def run(stack, workers=8, stride=1):
    d = os.path.join(MACRO, stack)
    files = sorted(glob.glob(os.path.join(d, "*.ARW")))
    pw, ph, ref, warps = read_warpmap(os.path.join(d, "warpmap.txt"))
    n = len(files)
    assert len(warps) == n, "sidecar has %d warps, dir has %d frames" % (
        len(warps), n)

    with rawpy.imread(files[0]) as r:
        H, W = r.raw_image_visible.shape
    # Plane centre in the coordinate system the sampling uses. rawpy's visible
    # crop is up to 4 px narrower than strehl's active rect, so this centre can
    # sit up to 2 plane px from strehl's; at |a-1| <= 0.06 that is a <= 0.12 px
    # mapping error, four hundred times smaller than the patch.
    cx, cy = W / 4.0, H / 4.0

    xs = np.linspace(-INSET, INSET, GRID_NX) * (W / 4.0) + cx
    ys = np.linspace(-INSET, INSET, GRID_NY) * (H / 4.0) + cy
    centres = [(float(x), float(y)) for y in ys for x in xs]

    idx = list(range(0, n, stride))
    print("%s: %d frames (sampling %d), plane %dx%d, ref %d, %d candidate patches"
          % (stack, n, len(idx), pw, ph, ref, len(centres)))

    scene = np.full((len(idx), len(centres)), np.nan)
    smad = np.full((len(idx), len(centres)), np.nan)
    sensor = np.full((len(idx), len(centres)), np.nan)
    t0 = time.time()
    with ProcessPoolExecutor(max_workers=workers, initializer=_init,
                             initargs=(stack, centres, warps, cx, cy)) as ex:
        for j, (k, sm, sd, se) in enumerate(
                ex.map(_one, [(k, files[k]) for k in idx], chunksize=2)):
            row = idx.index(k)
            scene[row] = sm
            smad[row] = sd
            sensor[row] = se
            if (j + 1) % 25 == 0:
                print("  %d/%d  %.0f s" % (j + 1, len(idx), time.time() - t0))
    print("  decoded %d frames in %.0f s" % (len(idx), time.time() - t0))

    a = np.array([np.hypot(w[0], w[1]) if w else np.nan for w in warps])
    out = os.path.join(HERE, "data", "levels-%s.npz" % stack)
    np.savez_compressed(
        out, idx=np.array(idx), scene=scene, scene_mad=smad, sensor=sensor,
        centres=np.array(centres), a=a, ref=ref, plane=np.array([pw, ph]),
        files=np.array([os.path.basename(f) for f in files]))
    print("  wrote %s" % out)


if __name__ == "__main__":
    stacks = sys.argv[1:] or ["bee-3-cpl"]
    for s in stacks:
        run(s)
