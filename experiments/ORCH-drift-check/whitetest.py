"""Is the reference's content in the notch bin STRUCTURE or NOISE?

structure.py showed the two arms' band-pass content in the notch bin is
essentially uncorrelated: r(aligned) = 0.1156 against a shift placebo of
-0.0258 and a strong-edge pole of 0.9713. By its pre-registered rule that reads
as (B) -- not the same structure attenuated.

That rule was too coarse and I am correcting it here rather than resting on it.
Low correlation is produced by BOTH of these:

  (B1) the reference kept NOISE and the pyramid averaged it away.
       The pyramid is right. The notch is a feature.

  (B3) the reference held real DETAIL, the pyramid's fallback mean crushed the
       coefficient to a few percent of it, and what survives in the pyramid tile
       is mostly averaging residue rather than the attenuated signal. Then r is
       low too -- and the pyramid is not merely attenuating detail, it is
       replacing it with something uncorrelated, which is WORSE than the clean
       0.33x attenuation the ratio suggested.

A two-arm correlation cannot separate those, because both predict low r. But
they disagree about a SINGLE-IMAGE property of the reference, which needs no
second arm at all:

  under (B1) the reference's band-pass content in the notch bin is white sensor
             noise passed through the band-pass filter.
  under (B3) it is scene structure.

And "white noise through this band-pass" is not a matter of opinion -- it is
computable. Band-passing an i.i.d. field imposes a known spatial
autocorrelation, entirely determined by the DoG kernel. So the negative pole is
derived from first principles on synthetic noise rather than borrowed from
some region assumed to be featureless.

THE TWO POLES, both empirical, neither assumed:

  synthetic   bandpass(i.i.d. Gaussian). Exactly what "pure noise" reads as
              through THIS filter at THIS tile size. Computed, not sampled from
              the image, so no scene content can contaminate it.
  strong      the 273-811 DN bins, where both arms agree to within 3% and the
              content is certainly real edges.

PRE-REGISTERED, before running (ORCH, this session):

  ctrl autocorr in the notch bin near the SYNTHETIC pole   -> (B1). The gate is
      right, the notch is correct behaviour, and my fallback hypothesis dies.
  ctrl autocorr in the notch bin near the STRONG pole      -> (B3). The fallback
      mean is destroying real structure and replacing it with residue.
  between                                                  -> unresolved, and I
      report it as unresolved.

Reported for the pyramid arm too, because under (B3) the pyramid's own content
in those tiles should sit at the synthetic pole -- it having become residue.
"""

import sys
from pathlib import Path

import numpy as np
import tifffile
from scipy import ndimage

TILE = 128
S_LO, S_HI = 0.535, 1.874
LAGS = (1, 2, 4)
SEED = 20260825


def bandpass(g: np.ndarray) -> np.ndarray:
    return ndimage.gaussian_filter(g, S_LO) - ndimage.gaussian_filter(g, S_HI)


def autocorr(t: np.ndarray, lag: int) -> float:
    """Mean of the horizontal and vertical normalised autocorrelation at `lag`.

    Both axes, averaged, so a subject with a strong directional bias (the
    row/column fixed-pattern noise this sensor is known to carry) cannot masquerade
    as isotropic structure through one axis alone.
    """
    a = t.astype(np.float64)
    a = a - a.mean()
    d = (a * a).sum()
    if d < 1e-12:
        return float("nan")
    h = (a[:, :-lag] * a[:, lag:]).sum() / d
    v = (a[:-lag, :] * a[lag:, :]).sum() / d
    return float(0.5 * (h + v))


def synthetic_pole(n: int = 24) -> dict:
    """What pure white noise reads as through this band-pass, at this tile size."""
    rng = np.random.default_rng(SEED)
    acc = {lag: [] for lag in LAGS}
    for _ in range(n):
        # Generated larger and cropped so the tile carries no filter edge
        # artefacts -- a boundary effect would inflate the correlation and make
        # the noise pole look more structured than noise actually is.
        f = bandpass(rng.standard_normal((TILE + 32, TILE + 32)).astype(np.float32))
        t = f[16 : 16 + TILE, 16 : 16 + TILE]
        for lag in LAGS:
            acc[lag].append(autocorr(t, lag))
    return {lag: float(np.mean(v)) for lag, v in acc.items()}


def run(name: str, R: np.ndarray, T: np.ndarray) -> None:
    gr = R[:, :, 1].astype(np.float32)
    gt = T[:, :, 1].astype(np.float32)
    lit = gr > np.quantile(gr[::4, ::4], 0.20)
    br, bt = bandpass(gr), bandpass(gt)

    h, w = gr.shape
    amps, ac_r, ac_t = [], [], []
    for y in range(0, h - TILE + 1, TILE):
        for x in range(0, w - TILE + 1, TILE):
            sl = (slice(y, y + TILE), slice(x, x + TILE))
            if lit[sl].mean() < 0.5:
                continue
            ar = float(np.abs(br[sl]).mean())
            if ar < 1e-6:
                continue
            amps.append(ar)
            ac_r.append([autocorr(br[sl], k) for k in LAGS])
            ac_t.append([autocorr(bt[sl], k) for k in LAGS])

    amp = np.array(amps)
    AR, AT = np.array(ac_r), np.array(ac_t)
    ok = ~np.isnan(AR).any(axis=1) & ~np.isnan(AT).any(axis=1)
    amp, AR, AT = amp[ok], AR[ok], AT[ok]

    syn = synthetic_pole()
    print(f"\n{name}    tiles {len(amp)}")
    print("  SYNTHETIC NOISE POLE (bandpass of i.i.d. Gaussian, 24 draws):")
    print("     " + "  ".join(f"lag{k}={syn[k]:+.4f}" for k in LAGS))
    hdr = "".join(f"{'ctrl L' + str(k):>11}" for k in LAGS) + "".join(f"{'pyr L' + str(k):>11}" for k in LAGS)
    print(f"  {'refAmp band':>18}{'n':>7}{hdr}")
    lo, hi = np.quantile(amp, 0.005), np.quantile(amp, 0.995)
    edges = np.geomspace(max(lo, 0.5), hi, 11)
    edges = np.concatenate([[0.0], edges, [np.inf]])
    for i in range(len(edges) - 1):
        m = (amp >= edges[i]) & (amp < edges[i + 1])
        if m.sum() < 5:
            continue
        hs = "inf" if np.isinf(edges[i + 1]) else f"{edges[i + 1]:.0f}"
        cells = "".join(f"{AR[m, j].mean():11.4f}" for j in range(len(LAGS)))
        cells += "".join(f"{AT[m, j].mean():11.4f}" for j in range(len(LAGS)))
        print(f"  {edges[i]:8.0f}-{hs:>8}{m.sum():7d}{cells}")

    # The verdict, computed against the two poles rather than eyeballed.
    strong = amp >= 273.0
    notch = (amp >= 31.0) & (amp < 53.0)
    if strong.sum() >= 5 and notch.sum() >= 5:
        print(f"\n  poles at lag1:  synthetic {syn[1]:+.4f}   strong-edge ctrl {AR[strong, 0].mean():+.4f}")
        for label, M in (("ctrl", AR), ("pyramid", AT)):
            v = M[notch, 0].mean()
            ds, dt = abs(v - syn[1]), abs(v - AR[strong, 0].mean())
            call = "NOISE-like" if ds < dt else "STRUCTURE-like"
            print(
                f"  notch {label:>8} lag1 {v:+.4f}   d(synthetic)={ds:.4f}  "
                f"d(strong)={dt:.4f}  -> {call}"
            )


def main() -> int:
    if len(sys.argv) < 3:
        print("usage: whitetest.py <dir> <subject> [<subject> ...]", file=sys.stderr)
        return 2
    d = Path(sys.argv[1])
    subjects = sys.argv[2:]
    done = missing = 0
    for subject in subjects:
        rp, tp = d / f"{subject}--ctrl.tiff", d / f"{subject}--blend.tiff"
        if not (rp.exists() and tp.exists()):
            print(f"MISSING pair for {subject}")
            missing += 1
            continue
        R, T = tifffile.imread(rp), tifffile.imread(tp)
        assert R.shape == T.shape, f"{subject}: shape mismatch"
        run(subject, R, T)
        done += 1
    print(f"\nSUMMARY  requested {len(subjects)}  scored {done}  missing {missing}")
    assert done + missing == len(subjects), "outcomes do not partition the input"
    return 1 if missing else 0


if __name__ == "__main__":
    raise SystemExit(main())
