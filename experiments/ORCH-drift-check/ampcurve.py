"""If the deficit is not organised by distance, what IS it organised by?

veildist.py refuted the spatial story on tweezers: within a fixed reference-
amplitude band the band-pass ratio does not improve near the silhouette, it is
slightly BETTER there (far - near = -0.0539 and -0.0332 in the two informative
terciles), and the no-silhouette placebo shows the same sign of trend. So the
gate's band-pass deficit is not a near-field effect around an outline.

The gate's own quintile column says what it IS organised by. On tweezers:

    q0  refAmp   44.5   ratio 1.0811
    q1  refAmp   56.4   ratio 1.0599
    q2  refAmp   80.7   ratio 0.7094   <- catastrophic
    q3  refAmp  677.0   ratio 0.8923
    q4  refAmp 1149.7   ratio 0.9953

That is not monotone. The blend WINS in the flattest tiles, collapses in the
mid-contrast tiles, and recovers at the top. Five bins cannot resolve a shape
like that -- there is an 8x gap in reference amplitude between q2 and q3 with
nothing sampled inside it.

This resolves it. Logarithmic bins in reference amplitude, every subject, so the
curve's shape is visible rather than inferred from five points.

WHAT THE SHAPES WOULD MEAN

  monotone falling      a sharpness-dependent loss; the merge blurs detail in
                        proportion to how much detail there is
  dip at mid contrast   a SELECTION failure. Where contrast is too low for the
                        focus measure to discriminate but too high for the gate
                        to fall back to the mean, the estimator is choosing
                        between frames it cannot tell apart. Flat tiles are safe
                        because averaging is correct there; sharp tiles are safe
                        because the peak is unambiguous.
  flat                  a global gain or DC problem, not a detail problem

A null control is included: reference against itself must be exactly 1.0 in every
bin, or the binning itself is lying.
"""

import sys
from pathlib import Path

import numpy as np
import tifffile
from scipy import ndimage

TILE = 128
S_LO, S_HI = 0.535, 1.874


def bandpass(g: np.ndarray) -> np.ndarray:
    return ndimage.gaussian_filter(g, S_LO) - ndimage.gaussian_filter(g, S_HI)


def curve(name: str, R: np.ndarray, T: np.ndarray, null: bool = False) -> None:
    gr = R[:, :, 1].astype(np.float32)
    gt = gr if null else T[:, :, 1].astype(np.float32)
    lit = gr > np.quantile(gr[::4, ::4], 0.20)
    br, bt = bandpass(gr), bandpass(gt)

    h, w = gr.shape
    amps, rats, clipf = [], [], []
    zero = (T == 0).any(axis=2)
    for y in range(0, h - TILE + 1, TILE):
        for x in range(0, w - TILE + 1, TILE):
            sl = (slice(y, y + TILE), slice(x, x + TILE))
            if lit[sl].mean() < 0.5:
                continue
            ar = float(np.abs(br[sl]).mean())
            if ar < 1e-6:
                continue
            amps.append(ar)
            rats.append(float(np.abs(bt[sl]).mean()) / ar)
            clipf.append(float(zero[sl].mean()))
    amp = np.array(amps)
    rat = np.array(rats)
    cf = np.array(clipf)

    tag = "  [NULL: reference vs itself]" if null else ""
    print(f"\n{name}{tag}    tiles {len(amp)}")
    print(f"  {'refAmp band':>18}{'n':>7}{'ratio':>9}{'clip-free':>11}{'  ':>2}bar")
    lo, hi = np.quantile(amp, 0.005), np.quantile(amp, 0.995)
    edges = np.geomspace(max(lo, 0.5), hi, 11)
    edges = np.concatenate([[0.0], edges, [np.inf]])
    for i in range(len(edges) - 1):
        m = (amp >= edges[i]) & (amp < edges[i + 1])
        if m.sum() < 5:
            continue
        r = rat[m].mean()
        clean = m & (cf == 0)
        rc = rat[clean].mean() if clean.sum() >= 5 else float("nan")
        hs = "inf" if np.isinf(edges[i + 1]) else f"{edges[i + 1]:.0f}"
        cs = f"{rc:11.4f}" if not np.isnan(rc) else f"{'--':>11}"
        bar = "#" * max(0, min(40, int(round(r * 20))))
        print(f"  {edges[i]:8.0f}-{hs:>8}{m.sum():7d}{r:9.4f}{cs}  {bar}")


def main() -> int:
    if len(sys.argv) < 3:
        print("usage: ampcurve.py <dir> <subject> [<subject> ...]", file=sys.stderr)
        return 2
    d = Path(sys.argv[1])
    subjects = sys.argv[2:]
    done = missing = 0
    first = True
    for subject in subjects:
        rp, tp = d / f"{subject}--ctrl.tiff", d / f"{subject}--blend.tiff"
        if not (rp.exists() and tp.exists()):
            print(f"MISSING pair for {subject}: need both {rp.name} and {tp.name}")
            missing += 1
            continue
        R, T = tifffile.imread(rp), tifffile.imread(tp)
        assert R.dtype == np.uint16 and T.dtype == np.uint16
        assert R.shape == T.shape, f"{subject}: shape mismatch"
        if first:
            curve(subject, R, R, null=True)
            first = False
        curve(subject, R, T)
        done += 1
    # Every requested subject lands in exactly one counted outcome, and the
    # outcomes sum to the number requested -- so a subject that was silently
    # skipped cannot be read as a subject that passed. Called with no subjects
    # at all, this used to print nothing and exit 0.
    print(f"\nSUMMARY  requested {len(subjects)}  scored {done}  missing {missing}")
    assert done + missing == len(subjects), "outcomes do not partition the input"
    return 1 if missing else 0


if __name__ == "__main__":
    raise SystemExit(main())
