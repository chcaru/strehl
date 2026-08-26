"""MEASURE co-registration between the warped single-frame renders and the merge.

The hull is only honest if my per-frame renders land on the grid the merge lands
on. I have an ARGUMENT for that (same sidecar, same placements, same Catmull-Rom
kernel; the merge logs "205 placed / 0 refused"; both come out 2344x3520). An
argument is not a measurement, and the brief warned that a mis-registered basis
voids every number downstream. So this measures it.

WHY THE FIRST ATTEMPT FAILED, AND WHAT IT TAUGHT
    Correlating raw luma gave NCC ~0.98 at EVERY offset with peaks pinned to the
    search boundary. Two real causes:
      (a) raw luma is dominated by smooth content and a large DC, so the
          correlation surface is flat and its argmax is noise;
      (b) a single frame in a focus bracket is DEFOCUSED almost everywhere, so
          most tiles carry no registration signal against an all-in-focus merge.
    The positive control caught this before any number was reported. That is
    what it is for.

METHOD NOW
    * High-pass both images so correlation is driven by fine detail, which is
      what actually carries registration.
    * Select tiles by high-pass energy of the WARPED FRAME -- only where that
      frame is genuinely in focus and therefore has something to say.
    * Integer shifts only; sub-pixel resampling would blur the measured quantity.
    * Quality gates reported per tile, never hidden: the peak must be INTERIOR
      (not pinned to the search boundary) and must stand clear of the surface
      median by a margin. Failing tiles are counted UNUSABLE and the counts are
      asserted to sum, so a skipped tile cannot read as a clean one.

POSITIVE CONTROL
    Measured drift across this bracket is 0.715 plane px total, so an "unwarped"
    arm cannot demonstrate sensitivity: warped and unwarped differ by under one
    pixel and an integer detector cannot separate them. The control is a PLANTED
    shift -- offset a tile by a known integer and require recovery RELATIVE TO
    THAT TILE'S OWN BASELINE PEAK. (Comparing the planted peak to zero rather
    than to the baseline was a bug in the first version and produced six
    spurious misses.)

If sensitivity is not proven, this script REFUSES to report a registration
number rather than reporting one it cannot defend.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np

from bhull2 import load16


def luma(a: np.ndarray) -> np.ndarray:
    a = a.astype(np.float32)
    return 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]


def blur(a: np.ndarray, passes: int = 2) -> np.ndarray:
    k = np.array([1.0, 4.0, 6.0, 4.0, 1.0], dtype=np.float32)
    k /= k.sum()
    out = a
    for _ in range(passes):
        for ax in (0, 1):
            pad = [(0, 0)] * a.ndim
            pad[ax] = (2, 2)
            p = np.pad(out, pad, mode="reflect")
            acc = np.zeros_like(out)
            sl = [slice(None)] * a.ndim
            for i, w in enumerate(k):
                sl[ax] = slice(i, i + out.shape[ax])
                acc += w * p[tuple(sl)]
            out = acc
    return out


def highpass(a: np.ndarray) -> np.ndarray:
    return a - blur(a)


def ncc_surface(tile: np.ndarray, ref: np.ndarray, rad: int):
    t = tile - tile.mean()
    tn = np.sqrt((t * t).sum())
    h, w = tile.shape
    surf = np.full((2 * rad + 1, 2 * rad + 1), -2.0, dtype=np.float32)
    for dy in range(-rad, rad + 1):
        for dx in range(-rad, rad + 1):
            r = ref[rad + dy:rad + dy + h, rad + dx:rad + dx + w]
            r = r - r.mean()
            rn = np.sqrt((r * r).sum())
            surf[dy + rad, dx + rad] = (t * r).sum() / max(tn * rn, 1e-9)
    iy, ix = np.unravel_index(int(np.argmax(surf)), surf.shape)
    return (iy - rad, ix - rad), float(surf[iy, ix]), surf


def evaluate(tile, ref, rad, margin):
    (dy, dx), pk, surf = ncc_surface(tile, ref, rad)
    interior = abs(dy) < rad and abs(dx) < rad
    med = float(np.median(surf))
    return (dy, dx), pk, med, interior, (pk - med) >= margin


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--merge", required=True)
    ap.add_argument("--warped", required=True)
    ap.add_argument("--rad", type=int, default=10)
    ap.add_argument("--tiles", type=int, default=8)
    ap.add_argument("--size", type=int, default=192)
    ap.add_argument("--margin", type=float, default=0.15)
    ap.add_argument("--plant-shift", default="3,-2")
    a = ap.parse_args()

    M = luma(load16(Path(a.merge)))
    W = luma(load16(Path(a.warped)))
    assert M.shape == W.shape, "geometry mismatch -- basis is not comparable"
    print(f"  merge  : {Path(a.merge).name}  {M.shape}")
    print(f"  warped : {Path(a.warped).name} {W.shape}")
    Mh, Wh = highpass(M), highpass(W)

    ts, rad = a.size, a.rad
    h, w = M.shape
    cands = []
    for cy in range(rad + ts, h - ts - rad, 160):
        for cx in range(rad + ts, w - ts - rad, 160):
            cands.append((float(np.abs(Wh[cy:cy + ts, cx:cx + ts]).mean()), cy, cx))
    cands.sort(reverse=True)
    picks = cands[:a.tiles]
    print(f"  tiles  : {a.tiles} of {len(cands)} candidates, by high-pass energy of")
    print("           the WARPED FRAME, i.e. where that frame is actually in focus")
    print(f"  gates  : peak interior to +/-{rad} px, peak-median >= {a.margin}")

    print(f"\n  {'tile':<16} {'hp energy':>10} {'dy,dx':>9} {'ncc':>7} {'median':>8} "
          f"{'interior':>9} {'clear':>7} {'status':>9}")
    usable = unusable = 0
    offs, rows = [], []
    for e, cy, cx in picks:
        tile = Wh[cy:cy + ts, cx:cx + ts]
        ref = Mh[cy - rad:cy + ts + rad, cx - rad:cx + ts + rad]
        (dy, dx), pk, med, interior, clear = evaluate(tile, ref, rad, a.margin)
        ok = interior and clear
        if ok:
            usable += 1
            offs.append((dy, dx))
        else:
            unusable += 1
        rows.append((cy, cx, dy, dx, ok))
        print(f"  y{cy:<5} x{cx:<7} {e:>10.1f} {f'{dy:+d},{dx:+d}':>9} {pk:>7.4f} "
              f"{med:>8.4f} {str(interior):>9} {str(clear):>7} "
              f"{'USABLE' if ok else 'UNUSABLE':>9}")

    assert usable + unusable == len(picks), "tile partition does not sum"
    print(f"\n  tiles examined {len(picks)} = usable {usable} + unusable {unusable}")

    py, px = (int(t) for t in a.plant_shift.split(","))
    print(f"\n  POSITIVE CONTROL: plant dy={py:+d} dx={px:+d}, recover RELATIVE to "
          "each tile's own baseline peak")
    hit = tot = 0
    for cy, cx, bdy, bdx, ok in rows:
        if not ok:
            continue
        tile = Wh[cy + py:cy + py + ts, cx + px:cx + px + ts]
        ref = Mh[cy - rad:cy + ts + rad, cx - rad:cx + ts + rad]
        (dy, dx), pk, med, interior, clear = evaluate(tile, ref, rad, a.margin)
        exp = (bdy + py, bdx + px)
        good = (dy, dx) == exp and interior
        tot += 1
        hit += good
        print(f"    y{cy:<5} x{cx:<7} baseline {bdy:+d},{bdx:+d} expect "
              f"{exp[0]:+d},{exp[1]:+d} got {dy:+d},{dx:+d}  "
              f"{'OK' if good else ('BOUNDARY' if not interior else 'MISS')}")
    print(f"    plant recovered on {hit}/{tot} usable tiles")

    if usable == 0:
        print("\n  VERDICT: INDETERMINATE -- no usable tile. No number reported.")
        return 2
    mx = max(max(abs(d) for d in o) for o in offs)
    print(f"\n  worst |shift| over {usable} usable tiles : {mx} px")
    if not tot or hit != tot:
        print("  VERDICT: WITHHELD -- detector sensitivity not proven, so the "
              "registration number is not reportable.")
        return 3
    print(f"  VERDICT: {'CO-REGISTERED, 0 px on every usable tile' if mx == 0 else f'shift up to {mx} px'}"
          f" | sensitivity PROVEN ({hit}/{tot})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
