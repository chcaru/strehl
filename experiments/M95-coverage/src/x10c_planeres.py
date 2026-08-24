"""Plane-resolution gather penalty -- corrected control set.

THE DEFECT IN x10b's K7, and it is the same class as arm 4's Mitchell control:
a true-positive firing on a wrong premise. K7 asserted "d plane px must cost the
same as 2d mosaic px", i.e. that a plane gather is merely the same kernel on a
coarser grid. It read 0.0221 / 0.0692 / 0.0960 dex apart and failed its own bar.

The premise is wrong, and working out why is the finding. The band under
measurement, 0.30-0.48 cyc per MOSAIC px, sits at 0.60-0.96 cyc per PLANE px,
which is ABOVE a single plane's Nyquist limit of 0.5. One CFA plane cannot
represent that band at all. The mosaic carries it only because the four
sub-planes interleave into a lattice twice as fine. So gathering each plane
independently is not a wider kernel; it is a hard band limit at 0.25 cyc per
mosaic px, and everything above that survives only as reconstruction leakage.

K7 CORRECTED -- MECHANISM. Run the plane arm with a near-ideal kernel
(Lanczos-8). If the penalty is kernel width, a near-ideal kernel removes it. If
the penalty is the plane band limit, it persists regardless of kernel. That
distinguishes the two mechanisms, which the old K7 could not.
"""
import json
import sys
from pathlib import Path

import numpy as np

import m95cov as M

B0 = Path(r"C:\dev\strehl-out\M95-resample\single-noalign.tif")
OUT = Path(__file__).resolve().parents[1] / "out" / "x10c_planeres.json"


def gather_full(reg, s0y, s0x, step, n=M.TILE, kernel="catmull-rom"):
    i = np.arange(n, dtype=np.float64)
    t = M.gather_1d(reg, s0y + i * step, 0, kernel)
    return M.gather_1d(t, s0x + i * step, 1, kernel)


def gather_planes(reg, s0y, s0x, step, n=M.TILE, kernel="catmull-rom"):
    """strehl's geometry: gather each 2x2 sub-plane on its own plane grid."""
    out = np.zeros((n, n), dtype=np.float64)
    r = np.arange(n // 2, dtype=np.float64)
    for oy in (0, 1):
        for ox in (0, 1):
            plane = reg[oy::2, ox::2]
            p0y = (s0y + oy * step - oy) / 2.0
            p0x = (s0x + ox * step - ox) / 2.0
            t = M.gather_1d(plane, p0y + r * step, 0, kernel)
            out[oy::2, ox::2] = M.gather_1d(t, p0x + r * step, 1, kernel)
    return out


def main():
    if not B0.exists():
        sys.exit(f"missing {B0}")
    img = M.load_luma(B0)
    tiles = M.pick_tiles(img)
    h, w = img.shape
    cy, cx = (h - 1) / 2.0, (w - 1) / 2.0
    print(f"source: {B0.name}  {w}x{h}\ntiles : {len(tiles)}\n")
    res = {"n_tiles": len(tiles)}

    def run(k, fn, extra=0.0, kernel="catmull-rom"):
        vals = []
        for ty, tx in tiles:
            o0y = round(cy + (ty - cy) / k)
            o0x = round(cx + (tx - cx) / k)
            sy = k * (o0y - cy) + cy + extra
            sx = k * (o0x - cx) + cx + extra
            ci = int(np.floor(sy + (M.TILE - 1) * k / 2.0)) & ~1
            cj = int(np.floor(sx + (M.TILE - 1) * k / 2.0)) & ~1
            y0, x0 = (ci - M.PAD // 2) & ~1, (cj - M.PAD // 2) & ~1
            if y0 < 0 or x0 < 0 or y0 + M.PAD > h or x0 + M.PAD > w:
                continue
            reg = img[y0 : y0 + M.PAD, x0 : x0 + M.PAD]
            g = fn(reg, sy - y0, sx - x0, k, kernel=kernel)
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
        print(f"K1 NULL   {tag:<7} k=1.0, integer phase       {c:+.6f} dex  "
              f"{'PASS' if ok[f'K1_{tag}'] else 'FAIL'}   ({n} tiles)")
        res[f"K1_null_{tag}"] = c

    c, _, _ = run(1.0, gather_planes, extra=2.0)
    ok["K4"] = abs(c) < 0.006
    print(f"K4 SHIFT  planes  +2 mosaic px (= 1 plane px)  {c:+.6f} dex  "
          f"{'PASS' if ok['K4'] else 'FAIL'}")
    res["K4_integer_plane_shift"] = c

    base10 = []
    for ty, tx in tiles:
        base10.append(img[ty : ty + M.TILE, tx : tx + M.TILE])
    Lb, _ = M.mean_sd([M.band_ratio(t, 1.0) for t in base10])
    Lp, _ = M.mean_sd([M.band_ratio(M.fourier_blur(t, 0.30), 1.0) for t in base10])
    ok["K3"] = (Lb - Lp) >= 0.15
    print(f"K3 POSITIVE  planted Gaussian sigma=0.30 px    {Lb - Lp:+.4f} dex  "
          f"{'PASS' if ok['K3'] else 'FAIL'}")
    res["K3_planted_sigma0p30"] = Lb - Lp

    print("\nK7 MECHANISM  is the penalty kernel width, or the plane band limit?")
    pen = {}
    for kern in ("catmull-rom", "lanczos8"):
        cf, _, _ = run(0.9974, gather_full, kernel=kern)
        cp, _, _ = run(0.9974, gather_planes, kernel=kern)
        pen[kern] = cp - cf
        print(f"   {kern:<12} full {cf:+.4f}   planes {cp:+.4f}   "
              f"penalty {cp - cf:+.4f} dex")
    survives = pen["lanczos8"] > 0.5 * pen["catmull-rom"]
    ok["K7"] = True   # diagnostic, not a gate: it reports which mechanism, not pass/fail
    print(f"   a near-ideal kernel retains {100 * pen['lanczos8'] / pen['catmull-rom']:.0f}% "
          f"of the penalty ->")
    print(f"   {'PLANE BAND LIMIT (structural)' if survives else 'KERNEL WIDTH'}")
    res["K7_penalty_by_kernel"] = pen
    res["K7_structural"] = bool(survives)

    res["controls"] = ok
    gates = [v for kk, v in ok.items() if kk != "K7"]
    if not all(gates):
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
    E2E = 0.2851
    gap = E2E - a["full"]
    p = a["planes"] - a["full"]
    print("\n--- does this close the gap arm 4 left ARGUED (P56)? ---")
    print(f"  end-to-end B0->B1 through the shipped binary : {E2E:+.4f} dex")
    print(f"  synthetic FULL-resolution gather, k=0.9974   : {a['full']:+.4f} dex")
    print(f"  unexplained gap                              : {gap:+.4f} dex")
    print(f"  measured PLANE-resolution penalty            : {p:+.4f} dex")
    print(f"  plane-res arm total {a['planes']:+.4f} vs end-to-end {E2E:+.4f}: "
          f"{abs(a['planes'] - E2E):.4f} dex apart")
    print(f"  the penalty accounts for {100 * p / gap:.0f}% of the gap")
    res.update(e2e_gap_dex=float(gap), plane_penalty_dex=float(p),
               penalty_share_of_gap=float(p / gap),
               planeres_vs_e2e_dex=float(abs(a["planes"] - E2E)))

    print("\n--- what a single CFA plane can carry ---")
    print("  measurement band 0.30-0.48 cyc/mosaic px")
    print("               = 0.60-0.96 cyc/plane px, against a plane Nyquist of 0.50")
    print("  so the whole band is above what one plane can represent; it exists")
    print("  only in the interleaved lattice of all four.")

    OUT.write_text(json.dumps(res, indent=2), encoding="utf-8")
    print(f"\nwrote {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
