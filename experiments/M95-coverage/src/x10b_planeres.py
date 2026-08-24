"""Does the gather running on the CFA PLANE, not the mosaic, cost extra sharpness?

Arm 4 left this ARGUED (P56). The code says it plainly:
  warpmap.rs:469   resampler.sample_checked(src, sx, sy)  -- src is a PlaneRef
  image_out.rs:18  "-> demosaic to full resolution [this module]"
so frames are warped at 3516x2344 per plane and only demosaiced to 7032x4688 at
write time. A Catmull-Rom tap span of +-2 plane pixels is +-4 mosaic pixels.

TWO DEFECTS IN x10_planeres.py, both caught by its own null control:

  STRETCH was ill-posed. Applying a 2x-dilated kernel to the full field reads
  only every other sample of the WHOLE field, which is decimation. The real
  plane gather reads every other sample OF ITS OWN SUB-LATTICE, and the four
  sub-lattices together cover everything. Dropped rather than patched, because
  a corrected version is just LITERAL again and would not be independent.

  PLANES had the geometry wrong twice: a literal `+ oy - oy` that is identically
  zero, and no constraint that the mosaic offset be even. strehl's warp is
  expressed in PLANE units, so the induced mosaic offset is always 2x a plane
  quantity and therefore even; an odd mosaic offset would map output red sites
  onto source blue sites, which no CFA pipeline can do. It read +0.4915 dex at
  integer phase, where a copy must read zero.

CORRECTED GEOMETRY. Output mosaic pixel m = 2r + oy belongs to sub-plane oy at
plane row r. Requiring the plane arm and the full-resolution arm to cover the
same scene span gives each sub-plane its own co-sited start:

    P_oy = (S + oy*step - oy) / 2,   S the source mosaic origin, S even.

INDEPENDENT CROSS-CHECK (K7). One plane pixel is two mosaic pixels, so a
sub-pixel offset of d plane px must cost the same as a full-resolution gather
offset by d in plane units, i.e. 2d mosaic px. If the plane path is merely the
same kernel on a coarser grid, those two ladders coincide.
"""
import json
import sys
from pathlib import Path

import numpy as np

import m95cov as M

B0 = Path(r"C:\dev\strehl-out\M95-resample\single-noalign.tif")
OUT = Path(__file__).resolve().parents[1] / "out" / "x10b_planeres.json"


def gather_full(reg, s0y, s0x, step, n=M.TILE):
    """One Catmull-Rom gather on the mosaic grid at full resolution."""
    i = np.arange(n, dtype=np.float64)
    t = M.gather_1d(reg, s0y + i * step, 0)
    return M.gather_1d(t, s0x + i * step, 1)


def gather_planes(reg, s0y, s0x, step, n=M.TILE):
    """strehl's geometry: gather each 2x2 sub-plane on its own plane grid."""
    out = np.zeros((n, n), dtype=np.float64)
    r = np.arange(n // 2, dtype=np.float64)
    for oy in (0, 1):
        for ox in (0, 1):
            plane = reg[oy::2, ox::2]
            p0y = (s0y + oy * step - oy) / 2.0
            p0x = (s0x + ox * step - ox) / 2.0
            t = M.gather_1d(plane, p0y + r * step, 0)
            out[oy::2, ox::2] = M.gather_1d(t, p0x + r * step, 1)
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

    def run(k, fn, extra=0.0):
        vals = []
        for ty, tx in tiles:
            o0y = round(cy + (ty - cy) / k)
            o0x = round(cx + (tx - cx) / k)
            sy = k * (o0y - cy) + cy + extra
            sx = k * (o0x - cx) + cx + extra
            # the source mosaic origin must be even: strehl's warp is in plane
            # units, so the mosaic offset it induces is always 2x a plane value.
            ci = int(np.floor(sy + (M.TILE - 1) * k / 2.0)) & ~1
            cj = int(np.floor(sx + (M.TILE - 1) * k / 2.0)) & ~1
            y0, x0 = (ci - M.PAD // 2) & ~1, (cj - M.PAD // 2) & ~1
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
    for tag, fn in (("full", gather_full), ("planes", gather_planes)):
        c, _, n = run(1.0, fn)
        ok[f"K1_{tag}"] = abs(c) < 0.006
        print(f"K1 NULL   {tag:<7} k=1.0, integer phase   {c:+.6f} dex  "
              f"{'PASS' if ok[f'K1_{tag}'] else 'FAIL'}   ({n} tiles)")
        res[f"K1_null_{tag}"] = c

    c, _, _ = run(1.0, gather_planes, extra=2.0)
    ok["K4"] = abs(c) < 0.006
    print(f"K4 SHIFT  planes  +2 mosaic px (=1 plane) {c:+.6f} dex  "
          f"{'PASS' if ok['K4'] else 'FAIL'}")
    res["K4_integer_plane_shift"] = c

    print("\nK7 EQUIVALENCE  d plane px must cost the same as 2d mosaic px:")
    eq = []
    for d in (0.125, 0.25, 0.5):
        cp, _, _ = run(1.0, gather_planes, extra=2.0 * d)
        cf, _, _ = run(1.0, gather_full, extra=d)
        eq.append(abs(cp - cf))
        print(f"   d={d:<6} planes(+{2 * d:.2f} mosaic px) {cp:+.4f}   "
              f"full(+{d:.3f} plane px) {cf:+.4f}   apart {abs(cp - cf):.4f}")
    ok["K7"] = max(eq) < 0.02
    print(f"   {'PASS' if ok['K7'] else 'FAIL'}  (bar: max gap < 0.02 dex)")
    res["K7_equivalence_gaps"] = eq

    res["controls"] = ok
    if not all(ok.values()):
        print("\nCONTROLS FAILED -- reporting no arm numbers.")
        OUT.write_text(json.dumps(res, indent=2), encoding="utf-8")
        return 1

    print("\n--- ARMS: cost of one gather, by the grid it runs on ---")
    print(f"{'k':>8} {'FULL-RES':>10} {'PLANE-RES':>10} {'PENALTY':>10}")
    rows = {}
    for k in (0.9974, 0.9315):
        cf, sf, _ = run(k, gather_full)
        cp, sp, _ = run(k, gather_planes)
        rows[k] = {"full": cf, "planes": cp, "sem_full": sf, "sem_planes": sp}
        print(f"{k:>8.4f} {cf:>+10.4f} {cp:>+10.4f} {cp - cf:>+10.4f}")
    res["arms"] = {str(k): v for k, v in rows.items()}

    a = rows[0.9974]
    E2E = 0.2851        # arm 4, |B0 -> B1|, shipped binary, k = 0.9974
    gap = E2E - a["full"]
    pen = a["planes"] - a["full"]
    print("\n--- does this close the gap arm 4 left ARGUED (P56)? ---")
    print(f"  end-to-end B0->B1 through the shipped binary : {E2E:+.4f} dex")
    print(f"  synthetic FULL-resolution gather, k=0.9974   : {a['full']:+.4f} dex")
    print(f"  unexplained gap                              : {gap:+.4f} dex")
    print(f"  measured PLANE-resolution penalty            : {pen:+.4f} dex")
    print(f"  plane-res total ({a['planes']:+.4f}) vs end-to-end ({E2E:+.4f}): "
          f"{abs(a['planes'] - E2E):.4f} dex apart")
    print(f"  the penalty accounts for {100 * pen / gap:.0f}% of the gap")
    res["e2e_gap_dex"] = float(gap)
    res["plane_penalty_dex"] = float(pen)
    res["penalty_share_of_gap"] = float(pen / gap)
    res["planeres_vs_e2e_dex"] = float(abs(a["planes"] - E2E))

    OUT.write_text(json.dumps(res, indent=2), encoding="utf-8")
    print(f"\nwrote {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
