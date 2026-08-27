"""Did any source frame resolve detail that the delivered master lost?

This is the question that decides whether softness in a stack is a MERGE
DEFECT or a PROPERTY OF THE CAPTURE. A stack is only worth making if the
output is at least as sharp, everywhere, as the best frame was there. If some
frame in the bracket resolved a region and the master did not, the merge threw
away detail that was handed to it.

Method, and why it is built this way:

  * Work on the GREEN CFA plane, not on a demosaiced RGB image. Demosaicing is
    an interpolation and its kernel differs between rawpy and the tool under
    test; comparing sharpness through two different interpolators measures the
    interpolators. The green plane is the raw sensor samples with no
    reconstruction at all, so a difference in it is a difference in captured
    detail. Green is chosen because a Bayer quad has two green sites, giving
    the densest true sampling.

  * Sharpness is the standard deviation of the Laplacian over the tile,
    normalised by the tile's own mean, so a brighter frame does not score as a
    sharper one. Focus stacking selects on local contrast, so this is the same
    quantity the merge itself is choosing on.

  * The master is compared on its own green channel. That is not the same
    signal as the raw green plane -- it has been through demosaic, matrix and
    the sRGB curve -- so the ABSOLUTE scores are not comparable between the
    two. What IS comparable is each one's score against its own kind. So the
    test reported here is deliberately a RANKING and a VISUAL one: find the
    frame that best resolves the tile, write both tiles as PNGs at matched
    scale, and look at them. Numbers localise; the eye adjudicates.

Rule 32: `rawpy.raw_image_visible` is a view into memory freed when the `with`
block exits. Every read here copies inside the block.

Usage:
  python frame_vs_master.py <subject> <master.tiff> <x> <y> <size> <outdir> [stride]
"""

import sys
import pathlib
import numpy as np
import rawpy
import tifffile
from PIL import Image


def lap_energy(a):
    """std(Laplacian)/mean -- exposure-invariant local contrast."""
    a = a.astype(np.float64)
    lap = (
        -4.0 * a[1:-1, 1:-1]
        + a[:-2, 1:-1]
        + a[2:, 1:-1]
        + a[1:-1, :-2]
        + a[1:-1, 2:]
    )
    m = a.mean()
    return float(lap.std() / m) if m > 0 else 0.0


def green_plane(path):
    """The green CFA samples of an RGGB frame, as a half-resolution plane.

    Averages the two green sites of each quad. No interpolation: every value
    here is a real sensor reading.
    """
    with rawpy.imread(str(path)) as raw:
        v = raw.raw_image_visible.astype(np.float32).copy()  # rule 32
    g0 = v[0::2, 1::2]
    g1 = v[1::2, 0::2]
    ny = min(g0.shape[0], g1.shape[0])
    nx = min(g0.shape[1], g1.shape[1])
    return (g0[:ny, :nx] + g1[:ny, :nx]) * 0.5


def norm8(a):
    a = a.astype(np.float64)
    lo = np.percentile(a, 0.5)
    hi = np.percentile(a, 99.5)
    if hi <= lo:
        hi = lo + 1
    return np.clip((a - lo) / (hi - lo) * 255.0, 0, 255).astype(np.uint8)


def main():
    subject = sys.argv[1]
    master = pathlib.Path(sys.argv[2])
    x, y, size = int(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5])
    outdir = pathlib.Path(sys.argv[6])
    stride = int(sys.argv[7]) if len(sys.argv) > 7 else 8
    outdir.mkdir(parents=True, exist_ok=True)

    src = pathlib.Path(r"D:\personal\macro") / subject
    frames = sorted(src.glob("*.ARW"))
    print(f"{subject}: {len(frames)} frames, scanning every {stride}")

    m = tifffile.imread(str(master))
    print(f"master {m.shape} {m.dtype}")
    mt = m[y : y + size, x : x + size, :]
    mg = mt[..., 1]
    print(f"master tile G lap_energy = {lap_energy(mg):.5f}")

    hx, hy, hs = x // 2, y // 2, size // 2

    rows = []
    for i in range(0, len(frames), stride):
        g = green_plane(frames[i])
        tile = g[hy : hy + hs, hx : hx + hs]
        if tile.size == 0:
            continue
        rows.append((lap_energy(tile), i, frames[i].name))
    rows.sort(reverse=True)

    print(f"\ngreen-plane lap_energy over the SAME region ({hx},{hy}) {hs}x{hs}:")
    print(f"  {'rank':>4} {'frame':>18} {'idx':>5} {'lap_energy':>11}")
    for r, (e, i, n) in enumerate(rows[:8]):
        print(f"  {r + 1:>4} {n:>18} {i:>5} {e:>11.5f}")
    print("  ...")
    for e, i, n in rows[-3:]:
        print(f"  {'':>4} {n:>18} {i:>5} {e:>11.5f}")

    best_e, best_i, best_n = rows[0]
    g = green_plane(frames[best_i])
    btile = g[hy : hy + hs, hx : hx + hs]
    Image.fromarray(norm8(btile)).resize((hs * 2, hs * 2), Image.NEAREST).save(
        outdir / f"{subject}--BESTFRAME-{best_n.replace('.ARW', '')}-green.png"
    )
    Image.fromarray(norm8(mg)).save(outdir / f"{subject}--MASTER-green.png")
    Image.fromarray((mt / 257.0).round().clip(0, 255).astype(np.uint8)).save(
        outdir / f"{subject}--MASTER-rgb.png"
    )
    print(f"\nwrote tiles to {outdir}")
    print(f"best frame: {best_n} (index {best_i}, lap_energy {best_e:.5f})")


if __name__ == "__main__":
    main()
