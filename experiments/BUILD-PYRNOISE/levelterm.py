"""The level term: is it GLOBAL drift the merge removes, or LOCAL content it does not?

`photom.py` found that the claim's patch reads admission 1.494 raw and exactly
1.000 once a per-frame level is removed, while 109MSDCF -- the corpus's
quietest stack -- moves only 2.6% under the same correction. So the excess at
the claim's patch is a per-frame LEVEL term and nothing else.

That is not yet an exoneration, because the correction in `photom.py` was fitted
ON THE PATCH ITSELF and a per-patch fit absorbs two different things:

  GLOBAL photometric drift. The exposure really did wander across the bracket;
    the run's own banner measures `gain span 1.1010`. The MERGE fits and removes
    exactly this, globally, from a low-detail region of the reference frame. A
    single unstacked frame cannot. If this is the whole term, the admission test
    is charging the subject for something neither arm ever sees, and the
    rejection is an artifact of my instrument.

  LOCAL content change. The patch itself really did get brighter or darker as it
    swept through focus -- a bright blur washing across it, say. The merge does
    NOT remove this. If this is the term, the region genuinely is non-stationary
    and the rejection stands.

THE DISCRIMINATOR. A global gain is one number per frame that must be the SAME
at every patch. A local content change is not. So: fit the level series at
several widely separated patches and compare them. Then redo admission using
ONLY a whole-plane per-frame gain -- one scalar per frame, which is what the
merge actually applies -- and see whether the claim's patch still lands at 1.

COMMISSIONING, because this conclusion now rests on the level term being real:
  K1  ARITHMETIC PREDICTION. For a stationary patch with per-pixel noise sd
      `sigma` at level L, adding a per-frame gain of sd `s_g` gives
      temporal^2 = sigma^2 + (s_g * L)^2, so the admission ratio must be
      exactly sqrt(1 + (sd_of_frame_means / sigma)^2). Every term on the right
      is measured independently of the ratio on the left. If the prediction
      reproduces the observed 1.494 the mechanism is not a story.
  K3  PLANTED POSITIVE CONTROL. Plant a gain drift of known size into a
      synthetic stationary bracket and require the ratio to move by the
      predicted amount -- the same discipline that caught a non-potent plant
      earlier in this campaign.
  K4  WHAT AN UNCORRECTED MERGE WOULD DO. A per-frame gain inflates a SELECTION
      arm (a mosaic of differently-scaled frames) and is averaged away by an
      ESTIMATION arm, so it inflates an arm-vs-arm ratio too. The pinned binary
      corrects it. Whether the claim's 925d03d build did is unknown to me, so
      the size of that inflation is measured here rather than assumed away.
"""

import json
import pathlib
import sys

import numpy as np

import admission
import pyrnoise as pn

RENDERS = pathlib.Path(r"C:\dev\strehl-out\BUILD-PYRNOISE\renders")
CLAIM = pathlib.Path(r"C:\dev\strehl-out\BUILD-PYRNOISE\claim")
RNG = np.random.default_rng(4242)

PATCHES = {"claim":  (292, 500, 100, 100),
           "pinned": (284, 702, 100, 100),
           "best":   (504, 312, 100, 100),
           "far-SE": (3100, 1900, 100, 100),
           "far-NE": (3100, 400, 100, 100),
           "mid":    (1700, 1100, 100, 100)}


def load(sub):
    d = RENDERS / sub
    frames = sorted(p.stem for p in d.glob("frame*.tif"))
    return {f: pn.green(d / f"{f}.tif") for f in frames}, frames


def patch_means(imgs, frames, roi):
    return np.array([pn.crop(imgs[f], roi).mean() for f in frames])


def adm(core_stack, big_stack):
    t = float(core_stack.std(axis=0, ddof=1).mean())
    s = float(np.mean([pn.hp_sd(b) for b in big_stack]))
    return t / s, t, s


def stacks(imgs, frames, roi):
    pad = pn.BOX
    x, y, w, h = roi
    big = np.stack([imgs[f][y - pad:y + h + pad, x - pad:x + w + pad].astype(np.float64)
                    for f in frames])
    return big[:, pad:-pad, pad:-pad], big


def mosaic_mean_ratio(core, k=None, trials=6, rng=None):
    """Simulated selection arm against a simulated estimation arm, from single
    frames only. No merge, no build. This is an ARM-VS-ARM ratio by construction,
    which is the orchestrator's question 3 in its purest form."""
    rng = rng or RNG
    n = core.shape[0]
    k = k or n
    sm = pn.hp_sd(core[:k].mean(axis=0))
    rs = [sm / pn.hp_sd(np.take_along_axis(core[:k], rng.integers(0, k, size=core.shape[1:])[None], axis=0)[0])
          for _ in range(trials)]
    return float(np.mean(rs))


def main():
    print("=" * 78)
    print("GLOBAL DRIFT OR LOCAL CONTENT? -- AND THE ARITHMETIC THAT DECIDES")
    print("=" * 78)
    leaf, lf = load("leaf-2-cpl")
    plane_mean = np.array([leaf[f].mean() for f in lf])
    g_global = plane_mean / plane_mean.mean()

    print(f"\nJ1  IS THE LEVEL SERIES THE SAME AT EVERY PATCH?")
    print(f"    A global gain is one number per frame and must be identical")
    print(f"    everywhere; local content change is not.")
    series = {}
    for lbl, roi in PATCHES.items():
        m = patch_means(leaf, lf, roi)
        series[lbl] = m / m.mean()
        print(f"    {lbl:<8} level {m.mean():7.0f}  span {m.max() / m.min():.4f}"
              f"  corr with whole-plane gain {np.corrcoef(series[lbl], g_global)[0, 1]:+.4f}")
    print(f"    whole-plane   span {plane_mean.max() / plane_mean.min():.4f}"
          f"   (banner, over all 182 frames: 1.1010)")
    keys = list(series)
    cc = np.array([[np.corrcoef(series[a], series[b])[0, 1] for b in keys] for a in keys])
    off = cc[~np.eye(len(keys), dtype=bool)]
    print(f"    pairwise correlation between patches: min {off.min():+.4f}"
          f"  median {np.median(off):+.4f}  max {off.max():+.4f}")

    print(f"\nJ2  ADMISSION USING ONLY THE WHOLE-PLANE GAIN -- one scalar per frame,")
    print(f"    which is what the merge actually applies.")
    print(f"    {'patch':<8}{'raw':>8}{'global-gain':>13}{'patch-gain':>12}   verdict (global)")
    j2 = {}
    for lbl, roi in PATCHES.items():
        core, big = stacks(leaf, lf, roi)
        r_raw = adm(core, big)[0]
        r_glob = adm(core / g_global[:, None, None], big)[0]
        m = patch_means(leaf, lf, roi)
        r_loc = adm(core * (m.mean() / m)[:, None, None], big)[0]
        j2[lbl] = (r_raw, r_glob, r_loc)
        print(f"    {lbl:<8}{r_raw:8.3f}{r_glob:13.3f}{r_loc:12.3f}   "
              f"{'PASS' if r_glob <= admission.BAR else 'FAIL'}")

    print(f"\nK1  ARITHMETIC PREDICTION -- every term measured independently of the ratio")
    print(f"    predicted admission = sqrt(1 + (sd of frame means / spatial noise sd)^2)")
    print(f"    {'patch':<8}{'sd(means)':>11}{'spatial':>9}{'predicted':>11}{'observed':>10}{'err':>8}")
    for lbl, roi in PATCHES.items():
        core, big = stacks(leaf, lf, roi)
        m = patch_means(leaf, lf, roi)
        r_obs, t, s = adm(core, big)
        pred = np.sqrt(1.0 + (m.std(ddof=1) / s) ** 2)
        print(f"    {lbl:<8}{m.std(ddof=1):11.2f}{s:9.2f}{pred:11.3f}{r_obs:10.3f}"
              f"{(pred / r_obs - 1) * 100:+7.1f}%")
    m9, f9 = load("109MSDCF")
    roi9 = (1416, 264, 256, 256)
    c9, b9 = stacks(m9, f9, roi9)
    m9m = patch_means(m9, f9, roi9)
    r9, t9, s9 = adm(c9, b9)
    print(f"    {'109':<8}{m9m.std(ddof=1):11.2f}{s9:9.2f}"
          f"{np.sqrt(1.0 + (m9m.std(ddof=1) / s9) ** 2):11.3f}{r9:10.3f}"
          f"{(np.sqrt(1.0 + (m9m.std(ddof=1) / s9) ** 2) / r9 - 1) * 100:+7.1f}%")

    print(f"\nK3  PLANTED POSITIVE CONTROL -- a gain drift of KNOWN size into a")
    print(f"    synthetic stationary bracket built from this subject's own pixels.")
    roi = PATCHES["claim"]
    core, big = stacks(leaf, lf, roi)
    ref_big = big[len(lf) // 2]
    sd = pn.hp_sd(ref_big)
    base_big = np.stack([ref_big + RNG.normal(0, sd, ref_big.shape) for _ in range(len(lf))])
    base_core = base_big[:, pn.BOX:-pn.BOX, pn.BOX:-pn.BOX]
    L = base_core.mean()
    print(f"    {'planted s_g':>12}{'sd(means)':>11}{'predicted':>11}{'observed':>10}{'err':>8}")
    for sg in (0.0, 0.01, 0.0264, 0.05):
        g = 1.0 + RNG.normal(0, sg, len(lf)) if sg > 0 else np.ones(len(lf))
        pb = base_big * g[:, None, None]
        pc = pb[:, pn.BOX:-pn.BOX, pn.BOX:-pn.BOX]
        r_obs = adm(pc, pb)[0]
        mm = pc.reshape(len(lf), -1).mean(axis=1)
        s = float(np.mean([pn.hp_sd(b) for b in pb]))
        pred = np.sqrt(1.0 + (mm.std(ddof=1) / s) ** 2)
        print(f"    {sg * 100:11.2f}%{mm.std(ddof=1):11.2f}{pred:11.3f}{r_obs:10.3f}"
              f"{(pred / r_obs - 1) * 100:+7.1f}%")

    print(f"\nK4  WHAT AN UNCORRECTED PER-FRAME GAIN DOES TO AN ARM-VS-ARM RATIO.")
    print(f"    A selection arm is a mosaic of differently-scaled frames and keeps the")
    print(f"    gain spread; an estimation arm averages it away. So it inflates the")
    print(f"    ratio -- this is the mechanism I owed the orchestrator, in its only")
    print(f"    surviving form. Measured on single frames, with and without the gain.")
    print(f"    {'patch':<8}{'raw mosaic/mean':>17}{'gain-removed':>14}{'inflation':>11}")
    k4 = {}
    for lbl in ("claim", "pinned", "best"):
        core, big = stacks(leaf, lf, PATCHES[lbl])
        m = core.reshape(len(lf), -1).mean(axis=1)
        r_raw = mosaic_mean_ratio(core)
        r_cor = mosaic_mean_ratio(core * (m.mean() / m)[:, None, None])
        k4[lbl] = (r_raw, r_cor)
        print(f"    {lbl:<8}{r_raw:17.4f}{r_cor:14.4f}{r_cor / r_raw:10.2f}x")
    print(f"    1/sqrt({len(lf)}) = {1 / np.sqrt(len(lf)):.4f}x is the stationary ideal.")

    json.dump({"j2": j2, "k4": k4,
               "plane_span": float(plane_mean.max() / plane_mean.min()),
               "series": {k: v.tolist() for k, v in series.items()}},
              open(CLAIM / "_levelterm.json", "w"), indent=1, default=float)
    return 0


if __name__ == "__main__":
    sys.exit(main())
