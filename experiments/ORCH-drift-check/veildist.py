"""Is the band-pass deficit spatially tied to the silhouette, or is that a proxy?

ORCH-veiling 23.5 records the honest state of the silhouette finding: six subjects
separate cleanly by a HUMAN JUDGEMENT about what each subject is. That is
evidence, not mechanism. BUILD-HALO has since measured a mechanism directly --
a defocused subject veils the backdrop for hundreds of pixels, and the merge
elects those veiled samples -- but it measured it as a LUMINANCE deficit, and the
gate's complaint is a BAND-PASS AMPLITUDE deficit. Those are not the same
quantity: a purely additive veil is a DC offset and moves no band-pass amplitude
at all.

So the two findings are not yet joined. This joins them, or fails to.

PRE-REGISTERED PREDICTIONS, written before the first run:

  P1  On a silhouette subject the band-pass ratio is LOWEST near the outline and
      RECOVERS toward 1.0 with distance. Veiling is a near-field effect and
      BUILD-HALO measured it dying by d~320 px.
  P2  On a no-silhouette subject the profile is FLAT in distance and >= 1.0
      everywhere. couch-fibers and flat-on-ruler are the placebos.
  P3  THE CONFOUND, and the reason this script is not just a plot. Tiles near a
      silhouette are also the SHARPEST tiles, and 22.1 already measured that the
      ratio varies strongly with tile sharpness. So distance may be nothing but a
      proxy for reference amplitude. The test only means something if the
      distance trend SURVIVES WITHIN a fixed amplitude band. If it does not, P1
      is refuted and the spatial story dies with it.

REFUTATION. If the within-band distance trend is flat on tweezers, the veil does
not explain the gate's deficit, whatever it does to luminance.
"""

import sys
from pathlib import Path

import numpy as np
import tifffile
from scipy import ndimage

TILE = 128
S_LO, S_HI = 0.535, 1.874  # the gate's own band, 0.1-0.35 c/px


def bandpass(g: np.ndarray) -> np.ndarray:
    return ndimage.gaussian_filter(g, S_LO) - ndimage.gaussian_filter(g, S_HI)


def outline_distance(ref_lum: np.ndarray) -> np.ndarray:
    """Distance in full-res px to the nearest coarse-scale luminance outline.

    Coarse scale on purpose: the subject's OUTLINE, not its internal texture.
    A fine-scale gradient would light up on every hair and make 'distance to an
    edge' mean 'distance to any detail', which is the confound, not the signal.
    """
    small = ndimage.gaussian_filter(ref_lum[::8, ::8], 2.0)
    gy, gx = np.gradient(small)
    gm = np.hypot(gx, gy)
    strong = gm > np.quantile(gm, 0.995)
    if not strong.any():
        return np.full(small.shape, np.inf, dtype=np.float32)
    return (ndimage.distance_transform_edt(~strong) * 8.0).astype(np.float32)


def analyse(name: str, R: np.ndarray, T: np.ndarray) -> None:
    print(f"\n{'=' * 74}\n{name}\n{'=' * 74}")
    gr = R[:, :, 1].astype(np.float32)
    gt = T[:, :, 1].astype(np.float32)

    lit = gr > np.quantile(gr[::4, ::4], 0.20)
    dist = outline_distance(gr)
    br, bt = bandpass(gr), bandpass(gt)

    h, w = gr.shape
    recs = []
    for y in range(0, h - TILE + 1, TILE):
        for x in range(0, w - TILE + 1, TILE):
            sl = (slice(y, y + TILE), slice(x, x + TILE))
            if lit[sl].mean() < 0.5:
                continue
            ar = float(np.abs(br[sl]).mean())
            if ar < 1e-6:
                continue
            at = float(np.abs(bt[sl]).mean())
            d = float(dist[y // 8 + TILE // 16, x // 8 + TILE // 16])
            recs.append((d, ar, at / ar))
    if not recs:
        print("  no tiles")
        return
    d = np.array([r[0] for r in recs])
    amp = np.array([r[1] for r in recs])
    rat = np.array([r[2] for r in recs])
    print(f"  tiles {len(recs)}   ratio mean {rat.mean():.4f}")

    edges = [0, 60, 140, 260, 460, 800, np.inf]
    print(f"\n  MARGINAL: band-pass ratio vs distance to outline")
    print(f"  {'d (px)':>12}{'n':>7}{'refAmp':>10}{'ratio':>9}")
    for i in range(len(edges) - 1):
        m = (d >= edges[i]) & (d < edges[i + 1])
        if m.sum() < 4:
            continue
        hi = "inf" if edges[i + 1] == np.inf else f"{edges[i + 1]:.0f}"
        print(f"  {edges[i]:5.0f}-{hi:>6}{m.sum():7d}{amp[m].mean():10.1f}{rat[m].mean():9.4f}")

    # P3. Within a fixed amplitude tercile, does distance still predict?
    print(f"\n  WITHIN-AMPLITUDE (the confound guard -- P3)")
    qs = np.quantile(amp, [0, 1 / 3, 2 / 3, 1.0])
    for t in range(3):
        m0 = (amp >= qs[t]) & (amp <= qs[t + 1] if t == 2 else amp < qs[t + 1])
        if m0.sum() < 12:
            continue
        print(f"    amplitude tercile {t}  ({qs[t]:.0f}-{qs[t + 1]:.0f} DN, n={m0.sum()})")
        near = m0 & (d < 140)
        far = m0 & (d >= 260)
        for lab, mm in (("near <140px", near), ("far >=260px", far)):
            if mm.sum() >= 4:
                print(f"      {lab:<14} n={mm.sum():5d}  refAmp {amp[mm].mean():8.1f}"
                      f"  ratio {rat[mm].mean():.4f}")
        if near.sum() >= 4 and far.sum() >= 4:
            delta = rat[far].mean() - rat[near].mean()
            print(f"      far - near = {delta:+.4f}   "
                  f"{'RECOVERS with distance' if delta > 0.02 else 'flat or inverted'}")


def main() -> int:
    d = Path(sys.argv[1])
    for subject in sys.argv[2:]:
        rp, tp = d / f"{subject}--ctrl.tiff", d / f"{subject}--blend.tiff"
        if not (rp.exists() and tp.exists()):
            print(f"missing pair for {subject}")
            continue
        R, T = tifffile.imread(rp), tifffile.imread(tp)
        assert R.dtype == np.uint16 and T.dtype == np.uint16
        assert R.shape == T.shape, f"{subject}: shape mismatch"
        analyse(subject, R, T)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
