"""Did restoring the noise-driven shrink recover sharpness, and what did it cost?

ORCH's instruction is explicit: report **sharpness and background noise
separately**. They move in opposite directions here -- that is the entire
substance of the disagreement -- and a single gradient-RMS score would hide the
trade rather than price it.

Three things are measured, in this order:

1.  **A byte-identity control, first.** `tighten_by_acuity` can only ever LOWER
    a radius, so on a subject whose geometric rule already collapses everywhere
    the switch may be inert. If the two arms are byte-identical then every
    number below is a statement about nothing, and no amount of staring at the
    deltas would reveal that. It is checked before anything else is printed.

2.  **Sharpness at viewing scale.** Full-resolution gradient RMS is dominated by
    per-pixel noise, and noise is exactly the quantity the disputed term is
    known to add -- so a full-res gradient statistic would credit the term for
    its own cost. Box-downsampling by 3 first suppresses the noise term by ~3x
    while leaving real edge structure, which is why BUILD-RENDER's gallery delta
    is stated at viewing scale. Both scales are printed anyway, because the gap
    between them is itself diagnostic.

3.  **Background noise, on tiles chosen from ONE arm.** The flattest tiles are
    selected in the OFF arm and then measured in both. Choosing them per-arm
    would let each arm pick its own quietest region and the comparison would
    chase the effect it is supposed to measure.

Everything is normalised by the tile's own level: these arms can differ in
overall level, and an un-normalised gradient statistic moves with brightness.
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import numpy as np
import tifffile

OUT = Path(r"C:\dev\strehl-out\ACUITY")
SUBJECTS = [
    "couch-fibers-cpl",
    "bee-2-cpl",
    "bee-1-cpl",
    "highly-angled-ruler-mm-cpl",
    "dry-erase-marker-head-cpl",
    "bee-3-cpl",
    "pencil-steep-angle-cpl",
]
VIEW_BIN = 3
TILE = 128
N_FLAT = 24


def green(path: Path) -> np.ndarray:
    a = tifffile.imread(str(path))
    assert a.dtype == np.uint16, f"{path}: {a.dtype}"
    return a[..., 1].astype(np.float64)


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for blk in iter(lambda: fh.read(1 << 20), b""):
            h.update(blk)
    return h.hexdigest()[:16].upper()


def downsample(a: np.ndarray, k: int) -> np.ndarray:
    h, w = (a.shape[0] // k) * k, (a.shape[1] // k) * k
    return a[:h, :w].reshape(h // k, k, w // k, k).mean(axis=(1, 3))


def grad_rms(a: np.ndarray) -> float:
    dx = np.diff(a, axis=1)
    dy = np.diff(a, axis=0)
    n0 = min(dx.shape[0], dy.shape[0])
    n1 = min(dx.shape[1], dy.shape[1])
    g2 = dx[:n0, :n1] ** 2 + dy[:n0, :n1] ** 2
    return float(np.sqrt(g2.mean()))


def sharpness(a: np.ndarray, k: int) -> float:
    """Gradient RMS normalised by level, so a brightening cannot move it."""
    d = downsample(a, k) if k > 1 else a
    lvl = float(np.median(d))
    assert lvl > 0.0, "median level must be positive"
    return grad_rms(d) / lvl


def flat_tiles(a: np.ndarray, n: int) -> list[tuple[int, int]]:
    """Indices of the n flattest TILE-sized tiles, by within-tile gradient."""
    h, w = a.shape
    cand: list[tuple[float, int, int]] = []
    for y in range(0, h - TILE, TILE):
        for x in range(0, w - TILE, TILE):
            t = a[y : y + TILE, x : x + TILE]
            if float(np.median(t)) < 64.0:  # clipped black carries no noise
                continue
            cand.append((grad_rms(t), y, x))
    cand.sort()
    return [(y, x) for _, y, x in cand[:n]]


def noise_on(a: np.ndarray, tiles: list[tuple[int, int]]) -> float:
    """Mean within-tile sd relative to level, over tiles fixed by the OFF arm."""
    vals = []
    for y, x in tiles:
        t = a[y : y + TILE, x : x + TILE]
        lvl = float(np.median(t))
        if lvl <= 0.0:
            continue
        vals.append(float(np.std(t)) / lvl)
    assert vals, "no usable flat tiles"
    return float(np.mean(vals))


def main() -> int:
    rows = []
    inert = []
    for s in SUBJECTS:
        pa, pb = OUT / f"{s}.acu-off.tif", OUT / f"{s}.acu-on.tif"
        if not (pa.exists() and pb.exists()):
            print(f"{s:20s} pending")
            continue

        da, db = digest(pa), digest(pb)
        if da == db:
            inert.append(s)
            print(f"{s:20s} !! ARMS BYTE-IDENTICAL ({da}) -- the switch is INERT here")
            continue

        a, b = green(pa), green(pb)
        tiles = flat_tiles(a, N_FLAT)
        rows.append(
            (
                s,
                da,
                db,
                sharpness(a, VIEW_BIN),
                sharpness(b, VIEW_BIN),
                sharpness(a, 1),
                sharpness(b, 1),
                noise_on(a, tiles),
                noise_on(b, tiles),
                len(tiles),
            )
        )

    if not rows:
        print("\nnothing measurable")
        return 1

    print(f"{'subject':20s} {'sharp@view off':>14s} {'on':>10s} {'delta':>8s}"
          f" {'sharp@1:1':>10s} {'delta':>8s} {'bg noise':>9s} {'delta':>8s}")
    ok = True
    for s, _da, _db, sv_a, sv_b, s1_a, s1_b, n_a, n_b, ntile in rows:
        dv = 100.0 * (sv_b - sv_a) / sv_a
        d1 = 100.0 * (s1_b - s1_a) / s1_a
        dn = 100.0 * (n_b - n_a) / n_a
        print(f"{s:20s} {sv_a:14.6f} {sv_b:10.6f} {dv:+7.2f}%"
              f" {s1_a:10.6f} {d1:+7.2f}% {n_a:9.5f} {dn:+7.2f}%   ({ntile} tiles)")
        if s == "couch-fibers-cpl" and dv <= 0.0:
            ok = False

    print()
    print("READING: sharp@view is the number BUILD-RENDER's gallery delta is stated in.")
    print("         couch-fibers-cpl was charged -6.58% by the deletion (0.9342).")
    print("         Restoring the term should move sharp@view UP by a comparable amount.")
    print("         bg noise going up is the KNOWN, ACCEPTED cost -- it is priced, not hidden.")
    if inert:
        print(f"\nINERT ARMS: {', '.join(inert)} -- switch changed no bytes on these")
    print(f"\nVERDICT: {'RECOVERS SHARPNESS' if ok else 'DOES NOT RECOVER -- deletion is not the mechanism'}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
