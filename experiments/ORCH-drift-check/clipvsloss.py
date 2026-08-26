"""Is flower-bud's 45% amplitude loss CAUSED by the clamp?

spectralratio.py found, on flower-bud-alone-cpl's SHARPEST quintile, an
amplitude ratio of ~0.55 flat across every frequency bin. Flat-in-frequency
rules out blur (which falls toward Nyquist). A broadband amplitude scale-down
localised to high-contrast tiles is what CLIPPING looks like, and this is the
arm that clips 1.4015% against the reference's 0.0001%.

If the clamp is the mechanism then per tile:
  clip fraction 0        -> amplitude ratio healthy (compare couch-fibers)
  clip fraction rising   -> amplitude ratio falling

and the two must be correlated. If clip-free tiles are ALSO destroyed, the
clamp is not the mechanism and something else is wrong with the merge.

Control: couch-fibers-cpl clips exactly 0.0000% in both arms. Running it here
is the placebo -- it must show no relationship, because there is no clipping
to drive one.

Usage:
  python clipvsloss.py <dir> <subject> --ref ctrl --test blend
"""

import argparse
import sys
from pathlib import Path

import numpy as np
import tifffile


def rgb(path: Path) -> np.ndarray:
    a = tifffile.imread(str(path))
    assert a.dtype == np.uint16, f"{path.name}: expected uint16, got {a.dtype}"
    return a


def highpass_rms(g: np.ndarray) -> float:
    """RMS of a 3x3 Laplacian -- an amplitude proxy that ignores DC."""
    lap = (
        4.0 * g[1:-1, 1:-1] - g[:-2, 1:-1] - g[2:, 1:-1] - g[1:-1, :-2] - g[1:-1, 2:]
    )
    return float(np.sqrt((lap.astype(np.float64) ** 2).mean()))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("dir")
    ap.add_argument("subject")
    ap.add_argument("--ref", default="ctrl")
    ap.add_argument("--test", default="blend")
    ap.add_argument("--tile", type=int, default=128)
    a = ap.parse_args()

    d = Path(a.dir)
    R = rgb(d / f"{a.subject}--{a.ref}.tiff")
    T = rgb(d / f"{a.subject}--{a.test}.tiff")
    assert R.shape == T.shape, f"{R.shape} vs {T.shape}"

    gr = R[:, :, 1].astype(np.float32)
    gt = T[:, :, 1].astype(np.float32)

    # clipping measured on ALL channels, both rails, in the TEST arm
    lo_t = (T == 0).any(axis=2)
    hi_t = (T == 65535).any(axis=2)
    lo_r = (R == 0).any(axis=2)
    hi_r = (R == 65535).any(axis=2)

    t = a.tile
    h, w = gr.shape
    ny, nx = h // t, w // t

    thr = np.percentile(gr, 20.0)
    lit = gr > thr

    rows = []
    for iy in range(ny):
        for ix in range(nx):
            sl = (slice(iy * t, (iy + 1) * t), slice(ix * t, (ix + 1) * t))
            if lit[sl].mean() < 0.9:
                continue
            hr = highpass_rms(gr[sl])
            ht = highpass_rms(gt[sl])
            if hr <= 0:
                continue
            rows.append(
                (
                    float(lo_t[sl].mean() + hi_t[sl].mean()),  # test clip frac
                    float(lo_r[sl].mean() + hi_r[sl].mean()),  # ref clip frac
                    hr,
                    ht / hr,
                )
            )

    if not rows:
        print("no fully-lit tiles")
        return 2

    arr = np.array(rows)
    ct, cr, refamp, ratio = arr[:, 0], arr[:, 1], arr[:, 2], arr[:, 3]

    print(f"subject : {a.subject}   {gr.shape}  tile={t}")
    print(f"tiles   : {len(rows)} fully-lit")
    print(f"clip    : test {ct.mean():.4%} of pixels, ref {cr.mean():.4%}")
    print(f"amplitude ratio overall mean {ratio.mean():.4f}")

    clean = ct == 0.0
    dirty = ct > 0.0
    print(f"\n--- partitioned by whether the TEST tile clips at all ---")
    print(f"  {'group':<22}{'nTiles':>8}{'ampRatio':>11}{'refAmp':>10}")
    print(f"  {'clip-free tiles':<22}{clean.sum():8d}{ratio[clean].mean():11.4f}{refamp[clean].mean():10.1f}")
    if dirty.any():
        print(f"  {'tiles with any clip':<22}{dirty.sum():8d}{ratio[dirty].mean():11.4f}{refamp[dirty].mean():10.1f}")
    else:
        print(f"  {'tiles with any clip':<22}{0:8d}{'--':>11}{'--':>10}   (placebo: nothing to drive an effect)")

    if dirty.sum() >= 5:
        print("\n--- amplitude ratio by test-tile clip fraction ---")
        edges = [0.0, 1e-6, 1e-4, 1e-3, 1e-2, 5e-2, 1.01]
        names = ["0%", "<0.01%", "0.01-0.1%", "0.1-1%", "1-5%", ">5%"]
        print(f"  {'clip band':<12}{'nTiles':>8}{'ampRatio':>11}{'refAmp':>10}")
        for i, nm in enumerate(names):
            m = (ct >= edges[i]) & (ct < edges[i + 1])
            if m.sum():
                print(f"  {nm:<12}{m.sum():8d}{ratio[m].mean():11.4f}{refamp[m].mean():10.1f}")

        sel = ct > 0
        if sel.sum() >= 3:
            c = np.corrcoef(np.log10(ct[sel]), ratio[sel])[0, 1]
            print(f"\n  corr(log10 clip fraction, amplitude ratio) over clipped tiles = {c:+.3f}")

        # Confound guard: clipping and sharpness both track contrast. Ask
        # whether clipping still explains loss AT MATCHED reference amplitude.
        print("\n--- confound guard: matched on reference amplitude ---")
        print(f"  {'refAmp quintile':<18}{'clean n':>9}{'clean r':>9}{'dirty n':>9}{'dirty r':>9}")
        order = np.argsort(refamp)
        for i in range(5):
            q = order[i * len(order) // 5 : (i + 1) * len(order) // 5]
            qc = q[clean[q]]
            qd = q[dirty[q]]
            cs = f"{ratio[qc].mean():9.4f}" if len(qc) else f"{'--':>9}"
            ds = f"{ratio[qd].mean():9.4f}" if len(qd) else f"{'--':>9}"
            print(f"  q{i} amp~{refamp[q].mean():<9.0f}{len(qc):9d}{cs}{len(qd):9d}{ds}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
