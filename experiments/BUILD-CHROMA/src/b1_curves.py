"""B1 -- through-focus response curves per CFA channel, across the whole field.

Two passes over the bracket.

  Pass 1 (registration). Phase-correlate every tile's G1 lattice against the
  reference frame's, on every REG_STRIDE-th frame. The resulting track is
  repaired against a robust Theil-Sen line, median-filtered, interpolated to
  every frame, and ROUNDED. Nothing is ever resampled: the rounded shift is
  applied by integer indexing only (rule 6). The shift is estimated on GREEN
  ALONE and applied identically to all four planes, so no per-channel spatial
  correction can leak into the axial measurement.

  Pass 2 (focus). Decode each frame, form Sobel gradient energy on each of the
  four native CFA lattices, build a summed-area table, and read the 27-px box
  mean off it at a fixed grid of sample points offset by that frame's integer
  shift. The summed-area path is exactly equal to `uniform_filter` at interior
  points and is asserted so in B0 V5.

The output is F[plane][k, tile, point] -- a through-focus curve per channel per
point -- plus each point's field radius, which is what the LoCA-vs-lateral
discrimination is binned on.

Tiles span the entire frame rather than one ROI. That is the substantive
difference from M107 Instrument B, which measured a single 512x512 ROI per
stack and therefore could not bin by radius at all.
"""

import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
from common import (OUT, PLANES, WIN, frames, read_cfa, planes_of,
                    grad_energy, integral, box_at,
                    ref_spectrum, phase_shift_ref, integer_track)

TILE = 160          # measurement window per tile, plane px
CORR = 192          # correlation window, plane px
STRIDE = 10         # sample-point spacing inside a tile, plane px
HALF = TILE // 2    # 80
MARGIN = 140        # keep tile centres this far from the plane edge
REG_STRIDE = 6      # correlate every Nth frame; the track is smooth in k
MAX_SHIFT = 40

PLANE_W, PLANE_H = 3514, 2344
CX, CY = PLANE_W / 2.0, PLANE_H / 2.0     # optical centre := sensor centre


def tile_centres(ncol=9, nrow=6):
    xs = np.linspace(MARGIN, PLANE_W - MARGIN, ncol)
    ys = np.linspace(MARGIN, PLANE_H - MARGIN, nrow)
    return [(int(round(x)), int(round(y))) for y in ys for x in xs]


def point_offsets():
    o = np.arange(-HALF + STRIDE, HALF, STRIDE)      # -70 .. +70
    oy, ox = np.meshgrid(o, o, indexing="ij")
    return oy.ravel(), ox.ravel()


def corr_win(pl, cx, cy):
    h = CORR // 2
    return pl[cy - h:cy + h, cx - h:cx + h].astype(np.float64)


def register(fs, cent, kref):
    """Integer shift track per (frame, tile). Green only. Never resampled."""
    nk, nt = len(fs), len(cent)
    ks = np.unique(np.r_[np.arange(0, nk, REG_STRIDE), nk - 1, kref])
    g1ref = planes_of(read_cfa(fs[kref]))["G1"]
    spec = [ref_spectrum(corr_win(g1ref, cx, cy)) for (cx, cy) in cent]
    del g1ref
    sdy = np.zeros((ks.size, nt))
    sdx = np.zeros((ks.size, nt))
    t0 = time.time()
    for j, k in enumerate(ks):
        g1 = planes_of(read_cfa(fs[k]))["G1"]
        for t, (cx, cy) in enumerate(cent):
            sdy[j, t], sdx[j, t] = phase_shift_ref(spec[t], corr_win(g1, cx, cy))
        if j % 12 == 0:
            print(f"   reg {j}/{ks.size}  ({time.time()-t0:.0f}s)")
    del spec

    kk = np.arange(nk, dtype=float)
    idy = np.zeros((nk, nt), int)
    idx = np.zeros((nk, nt), int)
    track_res = np.zeros(nt)
    for t in range(nt):
        a, b, r = integer_track(sdy[:, t], sdx[:, t], max_shift=MAX_SHIFT)
        idy[:, t] = np.rint(np.interp(kk, ks.astype(float), a.astype(float)))
        idx[:, t] = np.rint(np.interp(kk, ks.astype(float), b.astype(float)))
        track_res[t] = r
    return idy, idx, track_res, ks, sdy, sdx


def run(stack, win=WIN, ncol=9, nrow=6, tag="main", max_frames=None):
    fs = frames(stack)
    if max_frames:
        fs = fs[:max_frames]
    nk = len(fs)
    cent = tile_centres(ncol, nrow)
    nt = len(cent)
    oy, ox = point_offsets()
    npt = oy.size
    kref = nk // 2
    print(f"== {stack} [{tag}] : {nk} frames, {nt} tiles, {npt} pts/tile, win={win}")

    idy, idx, track_res, ks, sdy, sdx = register(fs, cent, kref)
    print(f"   shift dy [{idy.min()},{idy.max()}] dx [{idx.min()},{idx.max()}]"
          f"  max track residual {track_res.max():.2f} px"
          f"  tiles residual>2px {int((track_res > 2).sum())}/{nt}")

    tx = np.array([c[0] for c in cent])
    ty = np.array([c[1] for c in cent])
    px0 = tx[:, None] + ox[None, :]        # (tile, point)
    py0 = ty[:, None] + oy[None, :]

    F = {c: np.zeros((nk, nt, npt), np.float32) for c in PLANES}
    t0 = time.time()
    for k, path in enumerate(fs):
        pls = planes_of(read_cfa(path))
        yy = py0 + idy[k][:, None]
        xx = px0 + idx[k][:, None]
        assert yy.min() >= WIN and xx.min() >= WIN
        assert yy.max() < PLANE_H - WIN and xx.max() < PLANE_W - WIN
        for c in PLANES:
            sat = integral(grad_energy(pls[c].astype(np.float32)))
            F[c][k] = box_at(sat, yy, xx, win).astype(np.float32)
        if k % 60 == 0:
            print(f"   foc {k}/{nk}  ({time.time()-t0:.0f}s)")

    rad = np.hypot(px0 - CX, py0 - CY)
    npz = os.path.join(OUT, "json", f"b1_{stack}_{tag}.npz")
    np.savez_compressed(
        npz,
        R=F["R"], G1=F["G1"], G2=F["G2"], B=F["B"],
        px=px0, py=py0, rad=rad, tile_x=tx, tile_y=ty,
        track_res=track_res, idy=idy, idx=idx,
        reg_k=ks, reg_dy=sdy, reg_dx=sdx,
        nk=nk, kref=kref, win=win, stack=np.array(stack))
    print(f"   -> {npz}  ({time.time()-t0:.0f}s)")
    return npz


if __name__ == "__main__":
    args = sys.argv[1:]
    stacks = args if args else ["lavendar-cpl", "coffee-bean",
                                "couch-fibers-cpl", "bee-2-cpl"]
    for s in stacks:
        run(s)
