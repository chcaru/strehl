"""Shared pieces for the super-resolution held-out experiment.

Geometry follows the engine exactly (crates/strehl-cli/src/align_cmd.rs,
warp_frame_fullres_coordinates_impl): a warp-map placement is a pull from
reference plane coordinates (relative to the plane centre gw/2, gh/2) to frame
plane coordinates; sensor coordinate = 2 * plane coordinate, sensor pixel k has
its centre at coordinate k. Per-channel CA composes as a' = s a, b' = s b + t
for red and blue (crates/strehl-core/src/optics.rs, OpticalProfile::compose).
"""
import json
import struct
from concurrent.futures import ProcessPoolExecutor

import numpy as np
import rawpy

BLACK = 512.0
# Camera WB from the ARW (R, G, B multipliers / G); applied before demosaic as the engine does.
# Applied form (A7C2_FE100GM_2XTC_X4CPL_RADIAL): the fitted translation is recorded, not applied.
CA = {"r": (-508.4e-6, (0.0, 0.0)), "b": (174.4e-6, (0.0, 0.0))}
GAIN_DN_PER_E = 100 / 436.8  # profile relation at ISO 100
READ_E = 4.2


def hexf(h):
    return struct.unpack(">d", bytes.fromhex(h))[0]


def load_alignment(path):
    a = json.load(open(path))
    lines = [l for l in a["warpmap"].splitlines() if l[:1].isdigit()]
    plane = [l for l in a["warpmap"].splitlines() if l.startswith("plane ")][0]
    gw, gh = map(int, plane.split()[1].split("x"))
    place = []
    for l in lines:
        f = l.split("#")[0].split()
        if f[1] != "placed":
            place.append(None)
            continue
        place.append((complex(hexf(f[2]), hexf(f[3])), complex(hexf(f[4]), hexf(f[5]))))
    paths = [s["path"].replace("\\\\?\\", "") for s in a["binding"]["sources"]]
    return place, paths, (gw, gh)


def channel_transform(t, ch, use_ca):
    a, b = t
    if use_ca and ch in CA:
        eps, (tx, ty) = CA[ch]
        s = 1.0 + eps
        return (a * s, b * s + complex(tx, ty))
    return (a, b)


def ref_to_frame(t, xs, ys, centre):
    """Reference sensor coords -> frame sensor coords (pull)."""
    z = (xs / 2 - centre.real) + 1j * (ys / 2 - centre.imag)
    q = t[0] * z + t[1] + centre
    return 2 * q.real, 2 * q.imag


def frame_to_ref(t, xs, ys, centre):
    q = (xs / 2) + 1j * (ys / 2)
    z = (q - centre - t[1]) / t[0] + centre
    return 2 * z.real, 2 * z.imag


def decode_patch(args):
    path, boxes = args
    with rawpy.imread(path) as r:
        raw = r.raw_image.copy()  # full buffer; active area is the top-left 7032x4688
        wb = np.array(r.camera_whitebalance[:3], dtype=np.float64)
    out = []
    for (x0, y0, x1, y1) in boxes:
        out.append(raw[y0:y1, x0:x1].copy())
    return out, wb / wb[1]


def decode_many(jobs, workers=24):
    with ProcessPoolExecutor(workers) as ex:
        return list(ex.map(decode_patch, jobs, chunksize=2))


def cfa_channel(x, y):
    """RGGB at the active origin: 0=R, 1=G, 2=B."""
    x = np.asarray(x) & 1
    y = np.asarray(y) & 1
    return np.where((x == 0) & (y == 0), 0, np.where((x == 1) & (y == 1), 2, 1))


# ---- Malvar-He-Cutler demosaic (the engine's per-source reconstruction family) ----
from scipy.ndimage import convolve

_G_AT_RB = np.array([[0, 0, -1, 0, 0], [0, 0, 2, 0, 0], [-1, 2, 4, 2, -1], [0, 0, 2, 0, 0], [0, 0, -1, 0, 0]]) / 8.0
_RB_ROW = np.array([[0, 0, 0.5, 0, 0], [0, -1, 0, -1, 0], [-1, 4, 5, 4, -1], [0, -1, 0, -1, 0], [0, 0, 0.5, 0, 0]]) / 8.0
_RB_COL = _RB_ROW.T
_RB_DIAG = np.array([[0, 0, -1.5, 0, 0], [0, 2, 0, 2, 0], [-1.5, 0, 6, 0, -1.5], [0, 2, 0, 2, 0], [0, 0, -1.5, 0, 0]]) / 8.0


def mhc(mos, x0, y0):
    """Demosaic a WB'd mosaic whose top-left pixel has active coords (x0, y0)."""
    h, w = mos.shape
    yy, xx = np.mgrid[y0:y0 + h, x0:x0 + w]
    ch = cfa_channel(xx, yy)
    r_site, b_site = ch == 0, ch == 2
    g_site = ch == 1
    # green rows: row with red (y even) vs row with blue (y odd)
    g_in_rrow = g_site & ((yy & 1) == 0)
    g_in_brow = g_site & ((yy & 1) == 1)
    m = mos.astype(np.float64)
    c_g = convolve(m, _G_AT_RB, mode="mirror")
    c_row = convolve(m, _RB_ROW, mode="mirror")
    c_col = convolve(m, _RB_COL, mode="mirror")
    c_diag = convolve(m, _RB_DIAG, mode="mirror")
    R = np.where(r_site, m, 0.0)
    G = np.where(g_site, m, c_g)
    B = np.where(b_site, m, 0.0)
    R = np.where(g_in_rrow, c_row, R)
    R = np.where(g_in_brow, c_col, R)
    R = np.where(b_site, c_diag, R)
    B = np.where(g_in_brow, c_row, B)
    B = np.where(g_in_rrow, c_col, B)
    B = np.where(r_site, c_diag, B)
    return np.stack([R, G, B])


def keys_weights(t):
    """Catmull-Rom (Keys a=-0.5) weights for fractional offsets t in [0,1)."""
    t2, t3 = t * t, t * t * t
    w0 = -0.5 * t3 + t2 - 0.5 * t
    w1 = 1.5 * t3 - 2.5 * t2 + 1
    w2 = -1.5 * t3 + 2 * t2 + 0.5 * t
    w3 = 0.5 * t3 - 0.5 * t2
    return np.stack([w0, w1, w2, w3])


def cr_sample(img, xs, ys):
    """Catmull-Rom sample of a 2-D array at pixel coords (pixel k centre at k). NaN when out of support."""
    h, w = img.shape
    ix = np.floor(xs).astype(int)
    iy = np.floor(ys).astype(int)
    wx = keys_weights(xs - ix)
    wy = keys_weights(ys - iy)
    ok = (ix >= 1) & (iy >= 1) & (ix + 2 < w) & (iy + 2 < h)
    ixc = np.clip(ix, 1, w - 3)
    iyc = np.clip(iy, 1, h - 3)
    out = np.zeros(xs.shape)
    for j in range(4):
        row = np.zeros(xs.shape)
        for i in range(4):
            row += wx[i] * img[iyc + j - 1, ixc + i - 1]
        out += wy[j] * row
    return np.where(ok, out, np.nan)


def cr_matrix_rows(xs, ys, gx0, gy0, gw, gh):
    """Sparse rows (indices, weights) of Catmull-Rom interpolation of a grid
    whose pixel (0,0) sits at coords (gx0, gy0)."""
    lx, ly = xs - gx0, ys - gy0
    ix = np.floor(lx).astype(int)
    iy = np.floor(ly).astype(int)
    wx = keys_weights(lx - ix)
    wy = keys_weights(ly - iy)
    ok = (ix >= 1) & (iy >= 1) & (ix + 2 < gw) & (iy + 2 < gh)
    cols, vals = [], []
    for j in range(4):
        for i in range(4):
            cols.append((iy + j - 1) * gw + (ix + i - 1))
            vals.append(wy[j] * wx[i])
    return ok, np.stack(cols, 1), np.stack(vals, 1)
