"""Which spatial-frequency bands of this corpus actually CONTAIN SIGNAL?

`docs/research/V-LINEAR.md` sec.5.3 found, over four hand-picked frame pairs,
that strehl's linear develops carry essentially the same 0.20-0.48 cyc/px power
whether the tile is in focus or 20 focus steps away (ratios 1.015, 1.043, 1.004,
1.138).  If that holds generally, the band on which every strehl-vs-anything
fine-scale number has ever been quoted is a NOISE band, and no stacker can win
or lose there because there is nothing there to resolve.

This generalises that spot-check into the band-SELECTION instrument for the
head-to-head, and it is deliberately run BEFORE any comparator output exists.
The decision rule it feeds is fixed in ./PREREGISTRATION.md sec.2 and was
committed (9b192e79) before this file was first executed.

THE TEST.  Defocus is a low-pass filter.  At a fixed tile position, compare the
frame where that tile is sharpest against frames 20 steps away, which are badly
defocused THERE.  A band carrying real scene detail loses most of its power when
the lens moves off it; a band that is sensor noise does not care where the focus
is, because noise is not imaged.

    R_band = P_band(best-focus frame) / P_band(defocused frames)

Best focus is chosen by the 0.05-0.20 cyc/px SELECTION band -- above the tone
scale, below every contested band -- and required to be an interior maximum, so
that a tile which never came into focus in this sweep is dropped rather than
answered.  Selecting on 0.05-0.20 and reporting 0.20+ keeps the selection
statistically independent of the reported one for approximately white noise, so
the reported bands carry no winner's curse.  The selection band's own R is
printed but is ineligible to be the comparison band, for exactly that reason.

FALSIFIER (rule 20).  R comfortably above 2 in the 0.25-0.30 or 0.30-0.40 bands
kills the noise-floor reading of V-LINEAR sec.5.3, restores those bands as a
legitimate arena, and sends the head-to-head ahead on them.  The test is built so
that outcome is easy to reach: the CONFIRMED subset below keeps only the tiles
that provably resolve, which is the most favourable honest population there is.

TWO POPULATIONS are reported:
  ALL        every tile with an interior selection-band maximum;
  CONFIRMED  the subset whose SELECTION band itself moved by >=2x, i.e. tiles
             where the lens demonstrably came into and out of focus.  If the fine
             bands are flat even here, no gentler reading of the data survives.

INVOCATION (rule 47).  Reads only:
    C:\\dev\\strehl-out\\V-LINEAR\\lintiff\\DSC000{01..63}.tif
        63 files, 197,798,923 bytes each, 7032x4688 u16 RGB, made by
        experiments/V-LINEAR/develop_frames.ps1 from D:\\personal\\macro\\113MSDCF
        with `strehl develop --linear-srgb --demosaic`, STREHL_ALIGN=0.
Writes nothing.  Prints only.  No comparator, no Zerene, no Lightroom file is
opened by this script.

    python bandsignal.py [ntiles_y=5] [ntiles_x=6] [far=20]
"""
import os
import sys

import numpy as np
import tifffile

_HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(_HERE, "..", "V-HEADTOHEAD2"))
import h2                                                        # noqa: E402
from h2h2b import band_power                                     # noqa: E402

LIN = r"C:\dev\strehl-out\V-LINEAR\lintiff"
NFRAMES = 63
T = 256
MARGIN = 700
BOOT = 10000
RNG = np.random.default_rng(20260827)

# The 7 bands the whole project quotes, plus a finer sweep to locate the
# signal/noise crossover rather than merely bracketing it.
BANDS = list(h2.BANDS)
FINE = [(0.02, 0.05), (0.05, 0.08), (0.08, 0.11), (0.11, 0.14), (0.14, 0.17),
        (0.17, 0.20), (0.20, 0.25), (0.25, 0.30), (0.30, 0.40), (0.40, 0.48)]
SEL_LO, SEL_HI = 0.05, 0.20          # selection band, fixed in PREREGISTRATION


def ratio_ci(pf, pd, n=BOOT):
    """Sum-of-power ratio with a percentile bootstrap CI over TILES.

    Ratio-of-sums, not mean-of-ratios: a tile with almost no power in the
    denominator would otherwise dominate a mean of per-tile ratios.
    """
    k = len(pf)
    idx = RNG.integers(0, k, size=(n, k))
    num = pf[idx].sum(1)
    den = pd[idx].sum(1)
    good = den > 0
    r = num[good] / den[good]
    return pf.sum() / pd.sum(), np.percentile(r, 2.5), np.percentile(r, 97.5)


def verdict(r, lo):
    if r >= 2.0 and lo >= 1.5:
        return "PASS"
    if r >= 1.3:
        return "MARGINAL"
    return "FAIL(noise)"


def main():
    ny = int(sys.argv[1]) if len(sys.argv) > 1 else 5
    nx = int(sys.argv[2]) if len(sys.argv) > 2 else 6
    far = int(sys.argv[3]) if len(sys.argv) > 3 else 20

    allb = BANDS + FINE + [(SEL_LO, SEL_HI)]
    lo = np.array([b[0] for b in allb])
    hi = np.array([b[1] for b in allb])
    nsel = len(allb) - 1

    m0 = tifffile.memmap(os.path.join(LIN, "DSC00001.tif"), mode="r")
    H, W = m0.shape[0], m0.shape[1]
    del m0
    ys = np.linspace(MARGIN, H - MARGIN - T, ny).astype(int)
    xs = np.linspace(MARGIN, W - MARGIN - T, nx).astype(int)
    pos = [(int(y), int(x)) for y in ys for x in xs]
    ntile = len(pos)

    # power[frame, tile, band] and the tile mean, frame-major for disk locality.
    power = np.zeros((NFRAMES, ntile, len(allb)))
    means = np.zeros((NFRAMES, ntile))
    for f in range(NFRAMES):
        path = os.path.join(LIN, f"DSC{f + 1:05d}.tif")
        mm = tifffile.memmap(path, mode="r")
        for i, (y, x) in enumerate(pos):
            crop = h2.luma709(np.asarray(mm[y:y + T, x:x + T, :3], np.float64))
            means[f, i] = crop.mean()
            bp = band_power(crop, lo, hi)
            power[f, i] = np.nan if bp is None else bp
        del mm
        sys.stderr.write(f"\rframe {f + 1}/{NFRAMES}")
    sys.stderr.write("\n")

    sel = power[:, :, nsel]                       # (frame, tile) selection band
    best = np.nanargmax(sel, axis=0)              # per-tile best-focus frame

    keep, pf, pd, selr, mr = [], [], [], [], []
    for i in range(ntile):
        b = int(best[i])
        if b < 5 or b > NFRAMES - 6:              # interior maximum required
            continue
        ref = [b - far, b + far]
        ref = [r for r in ref if 0 <= r < NFRAMES]
        if not ref:
            continue
        keep.append(i)
        pf.append(power[b, i])
        pd.append(power[ref, i].mean(0))
        selr.append(power[b, i, nsel] / power[ref, i, nsel].mean())
        mr.append(means[b, i] / means[ref, i].mean())

    pf = np.array(pf)
    pd = np.array(pd)
    selr = np.array(selr)
    mr = np.array(mr)

    print(f"\ntiles: {ntile} placed, {len(keep)} with an interior selection-band "
          f"maximum, T={T}, far=+/-{far}")
    print(f"selection band {SEL_LO}-{SEL_HI} cyc/px; best-focus frames "
          f"{best[keep].min() + 1}..{best[keep].max() + 1}")
    print(f"mean-level ratio focus/defocus over kept tiles: "
          f"median {np.median(mr):.3f}, range {mr.min():.3f}-{mr.max():.3f}  "
          f"(near 1.0 => shot-noise contrast is comparable, so R is not a "
          f"brightness artefact)")

    conf = selr >= 2.0
    print(f"CONFIRMED subset (selection band moved >=2x): {conf.sum()} of "
          f"{len(keep)} tiles\n")

    for label, mask in (("ALL", np.ones(len(keep), bool)), ("CONFIRMED", conf)):
        if mask.sum() < 4:
            print(f"[{label}] too few tiles ({mask.sum()}) -- not reported\n")
            continue
        print(f"[{label}]  n={mask.sum()} tiles")
        print(f"  {'band cyc/px':>12} {'R':>8} {'CI95':>17}   verdict")
        for j, (a, b) in enumerate(allb):
            if j == nsel:
                continue
            r, cl, ch = ratio_ci(pf[mask, j], pd[mask, j])
            tag = "  <- SELECTION (winner's curse; ineligible)" \
                if (a, b) == (SEL_LO, SEL_HI) else ""
            std = "*" if (a, b) in BANDS else " "
            print(f" {std}{a:.2f}-{b:.2f}   {r:8.3f}  [{cl:6.3f},{ch:6.3f}]   "
                  f"{verdict(r, cl):<12}{tag}")
        r, cl, ch = ratio_ci(pf[mask, nsel], pd[mask, nsel])
        print(f"  {SEL_LO:.2f}-{SEL_HI:.2f}   {r:8.3f}  [{cl:6.3f},{ch:6.3f}]"
              f"   <- selection band itself, ineligible by pre-registration")
        print()

    print("* = one of the 7 bands h2.BANDS quotes; the others locate the "
          "crossover.\nDecision rule (PREREGISTRATION.md sec.2): PASS = R>=2.0 "
          "and CI low >=1.5;\nMARGINAL = 1.3<=R<2.0; FAIL = R<1.3.  The "
          "comparison band is the HIGHEST-\nfrequency PASSing band.  If none "
          "above 0.10 cyc/px passes, no head-to-head is\nreported on this "
          "corpus.")


if __name__ == "__main__":
    main()
