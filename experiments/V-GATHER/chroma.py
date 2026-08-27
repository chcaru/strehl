"""Statistic D -- is the fullres gather's chroma-noise excess RESTORED or CREATED?

Ports the two gather orders from crates/strehl-cli/src/align_cmd.rs exactly:
  OLD  warp_frame_in_place_plane   (1545-1630): deinterleave 4 CFA phase planes,
       Catmull-Rom gather each on the PLANE lattice at dest (px,py).
  NEW  warp_frame_in_place_fullres (1682-1815): Malvar-demosaic to 3 full-res
       planes, gather the site's OWN channel at 2*T(px+dx/2, py+dy/2), re-mosaic.
Both are followed by the pipeline's final Malvar demosaic, so NEW demosaics twice.

Malvar stencils F_G/F_H/F_V/F_X copied tap-for-tap from
crates/strehl-core/src/demosaic.rs:161-217 (weights in eighths).
Catmull-Rom tap copied from crates/strehl-core/src/restore.rs.

THE ATTRIBUTION ARGUMENT
  NOGATHER = mosaic -> Malvar, no resampling at all.  Every photon of sensor
  noise that a single demosaic can express is present in it and nothing has
  been low-passed away.  It is therefore the CEILING on "restored" noise: no
  amount of removing a low-pass can take an arm above it.  Anything above
  NOGATHER was MANUFACTURED by the pipeline, not uncovered in the sensor.
"""
from __future__ import annotations
import numpy as np

RNG_BASE = 20240607

# ---------------------------------------------------------------- Malvar
F_G = [(0,0,4.),(-1,0,2.),(1,0,2.),(0,-1,2.),(0,1,2.),(-2,0,-1.),(2,0,-1.),(0,-2,-1.),(0,2,-1.)]
F_H = [(0,0,5.),(-1,0,4.),(1,0,4.),(-2,0,-1.),(2,0,-1.),(-1,-1,-1.),(1,-1,-1.),(-1,1,-1.),(1,1,-1.),(0,-2,.5),(0,2,.5)]
F_V = [(0,0,5.),(0,-1,4.),(0,1,4.),(0,-2,-1.),(0,2,-1.),(-1,-1,-1.),(1,-1,-1.),(1,1,-1.),(-1,1,-1.),(-2,0,.5),(2,0,.5)]
F_X = [(0,0,6.),(-1,-1,2.),(1,-1,2.),(-1,1,2.),(1,1,2.),(-2,0,-1.5),(2,0,-1.5),(0,-2,-1.5),(0,2,-1.5)]

def _conv(pad, H, W, taps):
    acc = np.zeros((H, W), np.float64)
    for dx, dy, w in taps:
        acc += w * pad[2+dy:2+dy+H, 2+dx:2+dx+W]
    return acc * 0.125

def malvar(mos):
    """RGGB: (x even,y even)=R, even row=R row, odd row=B row (demosaic.rs)."""
    H, W = mos.shape
    pad = np.pad(mos, 2, mode="reflect")
    cG, cH, cV, cX = (_conv(pad, H, W, t) for t in (F_G, F_H, F_V, F_X))
    yy, xx = np.mgrid[0:H, 0:W]
    er, ec = (yy % 2 == 0), (xx % 2 == 0)
    isR, isB = er & ec, (~er) & (~ec)
    isG1, isG2 = er & (~ec), (~er) & ec
    r = np.where(isR, mos, np.where(isB, cX, np.where(isG1, cH, cV)))
    g = np.where(isR | isB, cG, mos)
    b = np.where(isB, mos, np.where(isR, cX, np.where(isG1, cV, cH)))
    return r, g, b

# ---------------------------------------------------------------- Catmull-Rom
def _wts(phi):
    o = np.stack([phi + 1.0, phi, phi - 1.0, phi - 2.0])   # t = x - (i+n)
    a = np.abs(o)
    w = np.where(a < 1.0, 1.5*a**3 - 2.5*a**2 + 1.0,
        np.where(a < 2.0, -0.5*a**3 + 2.5*a**2 - 4.0*a + 2.0, 0.0))
    return w

def sample_cr(src, sx, sy):
    H, W = src.shape
    ix, iy = np.floor(sx).astype(np.int64), np.floor(sy).astype(np.int64)
    wx, wy = _wts(sx - ix), _wts(sy - iy)
    num = np.zeros_like(sx); den = np.zeros_like(sx)
    for m in range(4):
        jy = np.clip(iy + m - 1, 0, H - 1)
        for n in range(4):
            jx = np.clip(ix + n - 1, 0, W - 1)
            w = wy[m] * wx[n]
            num += w * src[jy, jx]; den += w
    return np.where(np.abs(den) > 1e-12, num / np.where(den == 0, 1, den), 0.0)

# ---------------------------------------------------------------- the two arms
def make_T(theta, scale, tx, ty, cx, cy):
    c, s = scale*np.cos(theta), scale*np.sin(theta)
    def T(x, y):
        dx, dy = x - cx, y - cy
        return c*dx - s*dy + cx + tx, s*dx + c*dy + cy + ty
    return T

def gather_old(mos, T):
    out = np.empty_like(mos)
    gh, gw = mos.shape[0]//2, mos.shape[1]//2
    py, px = np.mgrid[0:gh, 0:gw].astype(np.float64)
    sx, sy = T(px, py)                       # dest (px,py) -- NO site offset
    for dy in range(2):
        for dx in range(2):
            out[dy::2, dx::2] = sample_cr(mos[dy::2, dx::2], sx, sy)
    return out

def gather_new(mos, T):
    r, g, b = malvar(mos)
    out = np.empty_like(mos)
    gh, gw = mos.shape[0]//2, mos.shape[1]//2
    py, px = np.mgrid[0:gh, 0:gw].astype(np.float64)
    for dy in range(2):
        for dx in range(2):
            ci = (0 if (dx == 0 and dy == 0) else 2 if (dx == 1 and dy == 1) else 1)
            plane = (r, g, b)[ci]
            sxp, syp = T(px + dx*0.5, py + dy*0.5)   # site offset INCLUDED
            out[dy::2, dx::2] = sample_cr(plane, 2.0*sxp, 2.0*syp)
    return out

# ---------------------------------------------------------------- statistic D
def boxblur(y, r):
    k = 2*r+1
    c = np.cumsum(np.pad(y, ((r+1, r), (0, 0)), mode="edge"), axis=0)
    y1 = (c[k:] - c[:-k])/k
    c = np.cumsum(np.pad(y1, ((0, 0), (r+1, r)), mode="edge"), axis=1)
    return (c[:, k:] - c[:, :-k])/k

def hp(y, r=3):
    return y - boxblur(y, r)

M = 24   # crop margin: keep the boundary-reflect region out of every statistic

def stats(r, g, b):
    lum = 0.2126*r + 0.7152*g + 0.0722*b
    chr_ = r - b
    sl = hp(lum)[M:-M, M:-M]; sc = hp(chr_)[M:-M, M:-M]
    return float(np.sqrt((sl**2).mean())), float(np.sqrt((sc**2).mean())), sc

def radial_spectrum(img, nb=32):
    a = img - img.mean()
    win = np.hanning(a.shape[0])[:, None] * np.hanning(a.shape[1])[None, :]
    P = np.abs(np.fft.fftshift(np.fft.fft2(a*win)))**2
    H, W = P.shape
    fy = np.fft.fftshift(np.fft.fftfreq(H))[:, None]
    fx = np.fft.fftshift(np.fft.fftfreq(W))[None, :]
    rad = np.sqrt(fx**2 + fy**2)
    edges = np.linspace(0, 0.5*np.sqrt(2), nb+1)
    prof = []
    for i in range(nb):
        m = (rad >= edges[i]) & (rad < edges[i+1])
        prof.append(P[m].mean() if m.any() else np.nan)
    diag = P[(np.abs(fx) > 0.35) & (np.abs(fy) > 0.35)].mean()
    axis = P[((np.abs(fx) > 0.35) & (np.abs(fy) < 0.10)) |
             ((np.abs(fy) > 0.35) & (np.abs(fx) < 0.10))].mean()
    return np.array(prof), 0.5*(edges[:-1]+edges[1:]), float(diag), float(axis)
