#!/usr/bin/env python3
"""Commission the DETAIL metric, both ways, before any dose number is quoted.

WHY THIS EXISTS.  The first pass of detail.py reported that planting 20 px of
misregistration into bee-3-cpl RAISED high-band amplitude to 1.82x the
undamaged merge.  That is not a discovery, it is an instrument failure, and
BUILD-TRIAGE names it in advance:

    "Band amplitude cannot tell detail from noise ... broadband noise alone
     manufactures a 2.05x false sharpness advantage for the noisier arm."

Misregistering a stack does two things that both ADD high-frequency energy:
it doubles edges (ghosting), and it stops the merge from cancelling noise,
because the frames it averages no longer agree.  A metric that rises under
damage cannot be used to argue that damage is small -- the sign is wrong
before the magnitude is even read.

So the metric is commissioned in BOTH directions on a known input:

    BLUR   a Gaussian of known sigma applied to the undamaged merge.  Detail
           has unambiguously been removed.  The metric MUST fall.
    SHARP  an unsharp mask of known strength.  High-frequency contrast has
           unambiguously been added.  The metric MUST rise.

A statistic that only ever falls under damage passes a degradation-only test
trivially, which is why the SHARP arm is here.  A statistic that rises under
both is measuring energy, not detail, and is disqualified.

MONOTONICITY IS THE ACTUAL REQUIREMENT.  A single blur and a single sharpen
can be passed by a metric that is merely noisy, so each direction is run as a
LADDER and the metric must be monotone along it.
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent / "BUILD-TRIAGE"))
import tri  # noqa: E402
from detail import pick_sites  # noqa: E402

ROOT = Path(r"C:\dev\strehl-out\V-DRIFT")
TILE = 256


def gauss(img: np.ndarray, sigma: float) -> np.ndarray:
    """Separable Gaussian, FFT-free so there is no window to argue about."""
    if sigma <= 0:
        return img
    r = int(np.ceil(4 * sigma))
    x = np.arange(-r, r + 1)
    k = np.exp(-(x * x) / (2 * sigma * sigma))
    k /= k.sum()
    out = np.apply_along_axis(lambda m: np.convolve(m, k, mode="same"), 0, img)
    return np.apply_along_axis(lambda m: np.convolve(m, k, mode="same"), 1, out)


def main() -> int:
    base = tri.luma(tri.load16(str(ROOT / "merge" / "d0.tif")))
    k = 0.9321
    sites = pick_sites(base, k, 12, TILE)
    print(f"commissioning on d0.tif, {len(sites)} sites, {TILE}px tiles, k={k}\n")

    def measure(fn) -> tuple[float, float]:
        h, s = [], []
        for (y, x) in sites:
            t = fn(y, x)
            h.append(tri.band_amp(t, k)["high"])
            s.append(tri.edge_slope(t))
        return float(np.median(h)), float(np.median(s))

    ref_h, ref_s = measure(lambda y, x: base[y:y + TILE, x:x + TILE])
    print(f"{'arm':>12s} {'high':>10s} {'vs ref':>9s} {'slope':>10s} {'vs ref':>9s}")
    print("-" * 56)
    print(f"{'reference':>12s} {ref_h:10.1f} {1.0:9.4f} {ref_s:10.2f} {1.0:9.4f}")

    rows = {"blur": [], "sharp": []}
    pad = 40
    for sigma in (0.5, 1.0, 2.0, 4.0):
        def f(y, x, s=sigma):
            big = base[y - pad:y + TILE + pad, x - pad:x + TILE + pad]
            return gauss(big, s)[pad:pad + TILE, pad:pad + TILE]
        h, sl = measure(f)
        rows["blur"].append((sigma, h / ref_h, sl / ref_s))
        print(f"{'blur s=' + str(sigma):>12s} {h:10.1f} {h/ref_h:9.4f} {sl:10.2f} {sl/ref_s:9.4f}")

    for amt in (0.25, 0.5, 1.0, 2.0):
        def f(y, x, a=amt):
            big = base[y - pad:y + TILE + pad, x - pad:x + TILE + pad]
            sharp = big + a * (big - gauss(big, 1.0))
            return sharp[pad:pad + TILE, pad:pad + TILE]
        h, sl = measure(f)
        rows["sharp"].append((amt, h / ref_h, sl / ref_s))
        print(f"{'sharp a=' + str(amt):>12s} {h:10.1f} {h/ref_h:9.4f} {sl:10.2f} {sl/ref_s:9.4f}")

    print()
    bad = 0
    for mi, mname in ((1, "band high"), (2, "edge_slope")):
        bl = [r[mi] for r in rows["blur"]]
        sh = [r[mi] for r in rows["sharp"]]
        down = all(b < 1.0 for b in bl) and all(bl[i] > bl[i + 1] for i in range(len(bl) - 1))
        up = all(s > 1.0 for s in sh) and all(sh[i] < sh[i + 1] for i in range(len(sh) - 1))
        ok = down and up
        bad += not ok
        print(f"[{'PASS' if ok else 'FAIL'}] {mname:10s} "
              f"blur ladder monotone down: {down} ({bl[0]:.3f} -> {bl[-1]:.3f});  "
              f"sharpen ladder monotone up: {up} ({sh[0]:.3f} -> {sh[-1]:.3f})")

    print(f"\n{'DETAIL METRIC COMMISSIONED' if bad == 0 else f'{bad} METRIC(S) DISQUALIFIED'}")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
