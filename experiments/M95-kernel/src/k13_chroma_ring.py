"""K13 -- differential chroma OVERSHOOT: the colour fringe a kernel itself creates.

K12 asked "how much chromatic fringing survives each kernel" and its instrument
failed its own power bar: a planted 1.0 px lateral CA moved the statistic only
+0.0598 dex against a registered +0.10. That failure is reported, not patched.
The diagnosis is that at a strong edge R-G has a large gradient whether or not
the channels are displaced -- a coloured edge is not a fringe -- so the planted
signal sat on top of a baseline ~17x larger.

This asks the question that is actually decidable, and that actually bears on
the default decision. Kernels do not CREATE lateral CA: the same geometric
shift is applied to every channel. What a negative-lobe kernel can create is
RINGING, and ringing becomes a COLOUR fringe exactly when the channels
overshoot by different amounts. So:

    o_X(i)   = signed overshoot of channel X at output pixel i, i.e. how far
               the interpolated value falls outside [min,max] of the two
               source samples bracketing it -- the same definition K22 used
               for luma, where Catmull-Rom's 6.2500% was re-derived
               algebraically as exactly 1/16.

    DCO      = RMS over edge pixels of  sqrt((o_R - o_G)^2 + (o_B - o_G)^2)

Differential, so achromatic ringing -- every channel overshooting equally --
contributes nothing. Only overshoot that differs BETWEEN channels counts, and
that is precisely a kernel-generated colour fringe.

CONTROLS, REGISTERED BEFORE THE RUN
-----------------------------------
S1 STRUCTURAL ZERO, and it is a real positive control rather than a sanity
   check: `nearest` and `bilinear` are monotone -- their output is a convex
   combination of the two bracketing samples and CANNOT leave [min,max]. Both
   must read DCO exactly 0.000000. If either is nonzero the instrument is
   broken, because it would be reporting an overshoot that provably cannot
   exist. This cannot be fudged by choosing a threshold.

S2 NON-ZERO ON THE NEGATIVE-LOBE KERNELS. Catmull-Rom and Lanczos-3 both have
   negative lobes and must read > 0 on real edges. Two exact zeros beside two
   non-zeros IS the discrimination.

S3 ORDERING. Lanczos-3's luma overshoot is 11.1413% against Catmull-Rom's
   6.2500% (K22, both re-derived independently). So DCO(lanczos3) >
   DCO(catmull-rom) is predicted. A FAIL here would be a genuine surprise and
   would be reported as one.

Reported alongside the band sharpness so the trade is visible rather than
asserted. 1-D horizontal gather: the bracketing pair is then exact and the
overshoot definition is unambiguous.
"""

import json
import sys
from pathlib import Path

import numpy as np
import rawpy

ROOT = Path(r"C:\dev\blog\death-of-software\projects\strehl")
sys.path.insert(0, str(ROOT / "experiments" / "M95-coverage" / "src"))
import m95cov as M  # noqa: E402

OUT = ROOT / "experiments" / "M95-kernel" / "out"
STACK = Path(r"D:\personal\macro\bee-3-cpl")

KERNELS = ["nearest", "bilinear", "catmull-rom", "lanczos3"]
PHASES = [0.13, 0.27, 0.5, 0.73, 0.87]
TILE = 512
PAD = 32
NTILES = 24
EDGE_PCT = 99.0
SEED = 20260824


def _nearest_taps(t):
    hi = (t >= 0.5).astype(np.float64)
    return np.stack([1.0 - hi, hi])


def _bilinear_taps(t):
    return np.stack([1.0 - t, t])


M.KERNELS["nearest"] = (2, _nearest_taps)
M.KERNELS["bilinear"] = (2, _bilinear_taps)


def bin_quads(path):
    with rawpy.imread(str(path)) as raw:
        vis = raw.raw_image_visible.astype(np.float32)
        pat = raw.raw_pattern
        desc = raw.color_desc.decode()
        black = np.array(raw.black_level_per_channel, dtype=np.float32)
    h, w = vis.shape
    h -= h % 2
    w -= w % 2
    vis = vis[:h, :w]
    planes = {}
    for dy in (0, 1):
        for dx in (0, 1):
            idx = int(pat[dy, dx])
            planes.setdefault(desc[idx], []).append(vis[dy::2, dx::2] - black[idx])
    return (planes["R"][0].astype(np.float64),
            np.mean(planes["G"], axis=0).astype(np.float64),
            planes["B"][0].astype(np.float64))


def gather_x(a, phase, kernel):
    """Horizontal sub-pixel gather; returns output and its bracketing pair."""
    w = a.shape[1]
    coords = np.arange(PAD, w - PAD, dtype=np.float64) + phase
    out = M.gather_1d(a, coords, axis=1, kernel=kernel)
    i0 = np.floor(coords).astype(np.int64)
    lo = np.minimum(a[:, i0], a[:, i0 + 1])
    hi = np.maximum(a[:, i0], a[:, i0 + 1])
    return out, lo, hi


def overshoot(a, phase, kernel):
    out, lo, hi = gather_x(a, phase, kernel)
    return out - np.clip(out, lo, hi)


frames = sorted(STACK.glob("*.ARW"))
frame = frames[len(frames) // 2]

print("=" * 82)
print("K13  differential chroma overshoot -- the colour fringe the kernel creates")
print("=" * 82)
print(f"frame   : {frame.name}")
print(f"kernels : {KERNELS}")
print(f"phases  : {PHASES}   tiles: {NTILES} x {TILE}px, edge mask top {100 - EDGE_PCT:.0f}%")

R0, G0, B0 = bin_quads(frame)
print(f"binned  : {G0.shape[1]} x {G0.shape[0]} per channel, demosaic-free quads")

rng = np.random.default_rng(SEED)
h, w = G0.shape
tiles = []
while len(tiles) < NTILES:
    y = int(rng.integers(PAD, h - PAD - TILE))
    x = int(rng.integers(PAD, w - PAD - TILE))
    tiles.append((y, x))

acc = {k: [] for k in KERNELS}
band = {k: [] for k in KERNELS}
for (y, x) in tiles:
    r = R0[y : y + TILE, x : x + TILE]
    g = G0[y : y + TILE, x : x + TILE]
    b = B0[y : y + TILE, x : x + TILE]
    gx = np.abs(np.diff(g, axis=1))
    thr = np.percentile(gx, EDGE_PCT)
    for k in KERNELS:
        for ph in PHASES:
            orr = overshoot(r, ph, k)
            og = overshoot(g, ph, k)
            ob = overshoot(b, ph, k)
            m = gx[:, PAD : PAD + orr.shape[1]] >= thr
            d = np.sqrt((orr - og) ** 2 + (ob - og) ** 2)
            acc[k].append(float(np.sqrt(np.mean(d[m] ** 2))) if m.any() else 0.0)
        pad = G0[y - PAD : y + TILE + PAD, x - PAD : x + TILE + PAD]
        band[k].append(M.band_ratio(
            M.gather(pad, 1.0, 0.5, 0.5, n_out=TILE, kernel=k), 1.0))

print("\n--- RESULTS ---")
print(f"  {'kernel':<14} {'DCO (DN)':>12} {'sd':>10} {'band':>10}")
table = {}
for k in KERNELS:
    v = float(np.mean(acc[k]))
    table[k] = {"DCO": v, "sd": float(np.std(acc[k], ddof=1)), "band": float(np.mean(band[k]))}
    print(f"  {k:<14} {v:>12.6f} {table[k]['sd']:>10.6f} {table[k]['band']:>10.4f}")

s1 = table["nearest"]["DCO"] == 0.0 and table["bilinear"]["DCO"] == 0.0
s2 = table["catmull-rom"]["DCO"] > 0.0 and table["lanczos3"]["DCO"] > 0.0
s3 = table["lanczos3"]["DCO"] > table["catmull-rom"]["DCO"]

cr = np.array(acc["catmull-rom"])
lz = np.array(acc["lanczos3"])
both = cr > 0
wins = int(np.sum(lz[both] > cr[both]))
nboth = int(both.sum())
bs = np.array([np.mean(lz[both][i]) / np.mean(cr[both][i])
               for i in rng.integers(0, nboth, size=(2000, nboth))])
ci = (float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5)))
print(f"\n  paired: lanczos3 > catmull-rom on {wins}/{nboth} samples "
      f"({100.0 * wins / nboth:.2f}%), ratio 95% CI [{ci[0]:.4f}, {ci[1]:.4f}]")

print("\n--- CONTROLS ---")
print(f"  S1 monotone kernels read EXACTLY zero : nearest={table['nearest']['DCO']:.6f} "
      f"bilinear={table['bilinear']['DCO']:.6f}   {'PASS' if s1 else 'FAIL'}")
print(f"  S2 negative-lobe kernels read > 0     : "
      f"cr={table['catmull-rom']['DCO']:.6f} lz={table['lanczos3']['DCO']:.6f}   "
      f"{'PASS' if s2 else 'FAIL'}")
ratio = (table["lanczos3"]["DCO"] / table["catmull-rom"]["DCO"]
         if table["catmull-rom"]["DCO"] > 0 else float("nan"))
print(f"  S3 lanczos3 > catmull-rom             : ratio {ratio:.4f}x   "
      f"{'PASS' if s3 else 'FAIL -- SURPRISE, report it'}")

print("\n--- HEADLINE FOR THE DEFAULT DECISION ---")
print(f"  Lanczos-3 creates {ratio:.3f}x the differential chroma overshoot of Catmull-Rom.")
print(f"  Its luma overshoot ratio (K22, algebraic) is 11.1413 / 6.2500 = "
      f"{11.1413 / 6.2500:.4f}x.")
print("  Nearest and bilinear cannot create ANY colour fringe of this kind: exactly 0.")

res = {"frame": frame.name, "kernels": KERNELS, "phases": PHASES, "n_tiles": NTILES,
       "tile": TILE, "edge_pct": EDGE_PCT, "seed": SEED, "table": table,
       "paired": {"wins": wins, "n": nboth, "pct": 100.0 * wins / nboth, "ci": ci},
       "controls": {"S1": s1, "S2": s2, "S3": s3, "lz_over_cr": ratio},
       "all_pass": bool(s1 and s2)}
OUT.mkdir(parents=True, exist_ok=True)
(OUT / "k13_chroma_ring.json").write_text(json.dumps(res, indent=2), encoding="utf-8")
print(f"\nwrote {OUT / 'k13_chroma_ring.json'}")
sys.exit(0 if (s1 and s2) else 1)
