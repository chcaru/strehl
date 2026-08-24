"""Does the gather running on the CFA PLANE, not the mosaic, cost extra sharpness?

Arm 4 left this ARGUED (P56). The code says it plainly:
  warpmap.rs:469   resampler.sample_checked(src, sx, sy)  -- src is a PlaneRef
  image_out.rs:18  "-> demosaic to full resolution [this module]"
so frames are warped at 3516x2344 per plane and only demosaiced to 7032x4688 at
write time. A Catmull-Rom tap span of +-2 plane pixels is +-4 mosaic pixels, so
the same kernel blurs twice as far in output units.

TWO INDEPENDENT ARMS, which must agree or neither is reported:

  LITERAL   decimate the field into the four 2x2 sub-planes, gather each on its
            own plane grid at step k, re-interleave. This is what strehl does.
  STRETCH   gather the full-resolution field once with a Catmull-Rom whose taps
            are spread 2x. This is the same geometry expressed as a kernel.

If the plane-resolution penalty is real, both read the same extra cost over a
direct full-resolution gather, and that cost should account for the gap between
the synthetic k=0.9974 cost (x7b, +0.1851) and the end-to-end B0->B1 measured
through the shipped binary (arm 4, -0.2851).
"""
import json
import sys
from pathlib import Path

import numpy as np

import m95cov as M

B0 = Path(r"C:\dev\strehl-out\M95-resample\single-noalign.tif")
OUT = Path(__file__).resolve().parents[1] / "out" / "x10_planeres.json"


def stretch_taps(t, factor=2):
    """Catmull-Rom taps evaluated on a grid `factor` times coarser."""
    return M.catmull_rom(t)


def gather_full(reg, s0y, s0x, step, n=M.TILE):
    i = np.arange(n, dtype=np.float64)
    t = M.gather_1d(reg, s0y + i * step, 0)
    return M.gather_1d(t, s0x + i * step, 1)


def gather_stretched(reg, s0y, s0x, step, n=M.TILE):
    """Full-resolution gather with the kernel dilated 2x.

    Sampling position p in mosaic units sits at p/2 in plane units. A tap at
    plane offset j lands at mosaic offset 2j, so the kernel is the same weights
    applied to samples two mosaic pixels apart.
    """
    def one(a, coords, axis):
        a = np.moveaxis(np.asarray(a, dtype=np.float64), axis, 0)
        half = coords / 2.0
        i0 = np.floor(half).astype(np.int64)
        w = M.catmull_rom((half - i0).astype(np.float64))
        nn = a.shape[0]
        out = np.zeros((len(coords),) + a.shape[1:], dtype=np.float64)
        for j in range(4):
            idx = np.clip(2 * (i0 - 1 + j), 0, nn - 1)
            out += w[j][:, None] * a[idx]
        return np.moveaxis(out, 0, axis)

    i = np.arange(n, dtype=np.float64)
    t = one(reg, s0y + i * step, 0)
    return one(t, s0x + i * step, 1)


def gather_planes(reg, s0y, s0x, step, n=M.TILE):
    """Decimate into four 2x2 sub-planes, gather each on its plane grid, weave.

    Output mosaic pixel (2q + o) belongs to sub-plane o and to plane index q.
    Its source position in plane units is (s0 + 2q*step + o)/2, which is exactly
    what a plane-space gather computes.
    """
    out = np.zeros((n, n), dtype=np.float64)
    for oy in (0, 1):
        for ox in (0, 1):
            plane = reg[oy::2, ox::2]
            qs = np.arange(0, n, 2, dtype=np.float64) / 2.0 + np.arange(n // 2) * 0
            q = np.arange(n // 2, dtype=np.float64)
            py = (s0y + 2 * q * step + oy - oy) / 2.0
            px = (s0x + 2 * q * step + ox - ox) / 2.0
            t = M.gather_1d(plane, py, 0)
            g = M.gather_1d(t, px, 1)
            out[oy::2, ox::2] = g
            del qs
    return out


def main():
    if not B0.exists():
        sys.exit(f"missing {B0}")
    img = M.load_luma(B0)
    tiles = M.pick_tiles(img)
    h, w = img.shape
    cy, cx = (h - 1) / 2.0, (w - 1) / 2.0
    print(f"source: {B0.name}  {w}x{h}")
    print(f"tiles : {len(tiles)}\n")
    res = {"n_tiles": len(tiles)}

    def run(k, fn):
        vals = []
        for ty, tx in tiles:
            o0y = round(cy + (ty - cy) / k)
            o0x = round(cx + (tx - cx) / k)
            sy = k * (o0y - cy) + cy
            sx = k * (o0x - cx) + cx
            ci = int(np.floor(sy + (M.TILE - 1) * k / 2.0))
            cj = int(np.floor(sx + (M.TILE - 1) * k / 2.0))
            y0, x0 = ci - M.PAD // 2, cj - M.PAD // 2
            if y0 < 0 or x0 < 0 or y0 + M.PAD > h or x0 + M.PAD > w:
                continue
            reg = img[y0 : y0 + M.PAD, x0 : x0 + M.PAD]
            g = fn(reg, sy - y0, sx - x0, k)
            base = img[ci - M.TILE // 2 : ci + M.TILE // 2,
                       cj - M.TILE // 2 : cj + M.TILE // 2]
            vals.append(M.band_ratio(base, 1.0) - M.band_ratio(g, k))
        v = np.array(vals)
        return float(v.mean()), float(v.std(ddof=1) / np.sqrt(len(v))), len(v)

    print("--- CONTROLS ---")
    ok = {}
    for tag, fn in (("full", gather_full), ("stretch", gather_stretched),
                    ("planes", gather_planes)):
        c, _, n = run(1.0, fn)
        good = abs(c) < 0.006
        ok[tag] = good
        print(f"K1 NULL  {tag:<8} k=1.0 (integer phase)  {c:+.6f} dex  "
              f"{'PASS' if good else 'FAIL'}   ({n} tiles)")
        res[f"K1_null_{tag}"] = c
    if not all(ok.values()):
        print("\nCONTROLS FAILED -- a gather that is not a copy at integer phase")
        print("has an indexing error. Reporting no arm numbers.")
        OUT.write_text(json.dumps(res, indent=2), encoding="utf-8")
        return 1

    print("\n--- ARMS: cost of one gather, by the grid it runs on ---")
    print(f"{'k':>8} {'FULL':>10} {'STRETCH':>10} {'PLANES':>10} "
          f"{'STRETCH-FULL':>13} {'PLANES-FULL':>12}")
    rows = {}
    for k in (0.9974, 0.9315):
        cf, sf, _ = run(k, gather_full)
        cs, ss, _ = run(k, gather_stretched)
        cp, sp, _ = run(k, gather_planes)
        rows[k] = {"full": cf, "stretch": cs, "planes": cp,
                   "sem_full": sf, "sem_stretch": ss, "sem_planes": sp}
        print(f"{k:>8.4f} {cf:>+10.4f} {cs:>+10.4f} {cp:>+10.4f} "
              f"{cs - cf:>+13.4f} {cp - cf:>+12.4f}")
    res["arms"] = {str(k): v for k, v in rows.items()}

    a, b = rows[0.9974], rows[0.9315]
    agree = abs((a["stretch"] - a["full"]) - (a["planes"] - a["full"]))
    print(f"\n  LITERAL vs STRETCH agreement at k=0.9974: {agree:.4f} dex apart")
    res["literal_vs_stretch_gap"] = float(agree)

    print("\n--- does this close the gap arm 4 left ARGUED? ---")
    E2E = -0.2851       # arm 4, B0 -> B1, shipped binary, k = 0.9974
    SYNTH = a["full"]
    gap = abs(E2E) - SYNTH
    pen = a["planes"] - a["full"]
    print(f"  end-to-end B0->B1 through the shipped binary : {abs(E2E):+.4f} dex")
    print(f"  synthetic full-resolution gather at k=0.9974 : {SYNTH:+.4f} dex")
    print(f"  unexplained gap                              : {gap:+.4f} dex")
    print(f"  measured plane-resolution penalty            : {pen:+.4f} dex")
    print(f"  the penalty accounts for {100 * pen / gap:.0f}% of the gap")
    res["e2e_gap_dex"] = float(gap)
    res["plane_penalty_dex"] = float(pen)
    res["penalty_share_of_gap"] = float(pen / gap)

    OUT.write_text(json.dumps(res, indent=2), encoding="utf-8")
    print(f"\nwrote {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
