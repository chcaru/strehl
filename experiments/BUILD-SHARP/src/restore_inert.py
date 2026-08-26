"""Is the shipped restoration inert? Measured on real subjects, not a wedge.

s24 reported the restoration "wired, default off, and MEASURED INERT at the
sigma^2 I gave it". This establishes or refutes that on the owner's own captures
at the shipped configuration, and it is deliberately NOT a synthetic wedge: s31
was burned by a 1.297x that was real on a grating the rig cannot deliver.

BANDS. The head-to-head deficit is quoted in cycles per PRIOR pixel --
`V-HEADTOHEAD/spec.py:70` computes `r = hypot(fy, fx) * arm.scale` with the
comment "-> cycles per PRIOR pixel", and strehl's raster carries 3.5063% more
pixels per scene unit. So the comparator's bands land HERE at:

    comparator 0.20-0.30 cyc/prior-px  ->  0.193-0.290 cycles per strehl pixel
    comparator 0.30-0.40 cyc/prior-px  ->  0.290-0.387 cycles per strehl pixel

Those are the bands reported below. Reporting the comparator's numbers
unconverted would be the same class of error as the f-column units mix-up that
cost this project three wrong conclusions.

DISCRIMINATION. A band-power rise is admissible as evidence of change and NOT on
its own as evidence of improvement: it rises equally when a filter preserves
detail, manufactures it, or merely amplifies noise. So tiles are ranked by the
OFF arm and reported in three populations -- flattest (out of focus: any rise
there is noise or ringing), median, and sharpest (where detail actually is).
Ranking on the OFF arm means the arm under test cannot bias its own selection.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import tifffile

TILE = 256
# (label, lo, hi) in cycles per STREHL output pixel.
SCALE = 1.035063
BANDS = [
    ("0.10-0.19 (comparator 0.10-0.20)", 0.10 / SCALE, 0.20 / SCALE),
    ("0.19-0.29 (comparator 0.20-0.30)", 0.20 / SCALE, 0.30 / SCALE),
    ("0.29-0.39 (comparator 0.30-0.40)", 0.30 / SCALE, 0.40 / SCALE),
    ("0.39-0.46 (comparator 0.40-0.48)", 0.40 / SCALE, 0.48 / SCALE),
]


def green(path: Path) -> np.ndarray:
    a = tifffile.imread(str(path))
    if a.ndim != 3:
        raise SystemExit(f"{path}: expected RGB, got {a.shape}")
    return a[:, :, 1].astype(np.float64)


def band_powers(t: np.ndarray) -> dict[str, float]:
    """Windowed band variance, window-energy corrected, DC removed."""
    n = t.shape[0]
    c = t - t.mean()
    w = np.hanning(n)[:, None] * np.hanning(n)[None, :]
    c = c * w
    f = np.fft.fft2(c)
    p = (np.abs(f) ** 2) / (n * n) ** 2
    p /= (w ** 2).mean()
    fy = np.fft.fftfreq(n)[:, None]
    fx = np.fft.fftfreq(n)[None, :]
    r = np.hypot(fy, fx)
    return {lbl: float(p[(r >= lo) & (r < hi)].sum()) for lbl, lo, hi in BANDS}


def tile_grid(shape: tuple[int, int]) -> list[tuple[int, int]]:
    h, w = shape
    ys = range(TILE, h - 2 * TILE, TILE)
    xs = range(TILE, w - 2 * TILE, TILE)
    return [(y, x) for y in ys for x in xs]


def main() -> int:
    if len(sys.argv) != 3:
        raise SystemExit("usage: restore_inert.py <off.tif> <on.tif>")
    poff, pon = Path(sys.argv[1]), Path(sys.argv[2])
    off, on = green(poff), green(pon)
    if off.shape != on.shape:
        raise SystemExit(f"shape mismatch {off.shape} vs {on.shape}")

    d = on - off
    nz = int(np.count_nonzero(d))
    print(f"green plane {off.shape[1]}x{off.shape[0]}")
    print(f"  pixels changed by restore : {nz} of {d.size} ({100.0*nz/d.size:.4f}%)")
    print(f"  max |on - off|            : {np.abs(d).max():.1f} DN")
    print(f"  rms |on - off|            : {np.sqrt((d*d).mean()):.4f} DN")
    if nz == 0:
        print("\n  VERDICT: BYTE-IDENTICAL on green. The restoration is INERT -- it is")
        print("  not merely small, it changes nothing at all at the shipped config.")
        return 0

    coords = tile_grid(off.shape)
    # Rank by the OFF arm so the arm under test cannot bias tile selection.
    score = []
    for y, x in coords:
        t = off[y:y + TILE, x:x + TILE]
        score.append(float(np.abs(np.diff(t, axis=0)).mean()
                           + np.abs(np.diff(t, axis=1)).mean()))
    order = np.argsort(np.asarray(score))
    n = len(order)
    pops = {
        "flattest 5%  (defocus: a rise here is noise/ringing)": order[: max(1, n // 20)],
        "median 10%": order[n // 2 - max(1, n // 20): n // 2 + max(1, n // 20)],
        "sharpest 5% (detail sites)": order[-max(1, n // 20):],
    }

    print(f"\n  {n} tiles of {TILE}x{TILE}; ratios are ON / OFF, >1 means restore added power")
    for pname, idx in pops.items():
        acc_on = {lbl: 0.0 for lbl, _, _ in BANDS}
        acc_off = {lbl: 0.0 for lbl, _, _ in BANDS}
        for i in idx:
            y, x = coords[i]
            bo = band_powers(off[y:y + TILE, x:x + TILE])
            bn = band_powers(on[y:y + TILE, x:x + TILE])
            for lbl in acc_on:
                acc_on[lbl] += bn[lbl]
                acc_off[lbl] += bo[lbl]
        print(f"\n  {pname}  (n={len(idx)})")
        for lbl, _, _ in BANDS:
            o, w = acc_off[lbl], acc_on[lbl]
            # amplitude ratio: band power is contrast^2
            ratio = float(np.sqrt(w / o)) if o > 0 else float("nan")
            print(f"    {lbl:36s} amplitude ON/OFF = {ratio:.4f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
