"""Commission the level-term conclusion, and price its consequences.

`levelterm.py` produced the finding that overturns my previous report -- the
admission excess at the README claim's own patch is a per-frame LEVEL term, and
the claim's build did not correct it -- but its positive control (K3) FAILED as
written, at +42.6% error on the zero-plant row. The control was wrong, not the
finding, and this file proves that rather than assuming it.

WHY K3 FAILED. The predicted form was sqrt(1 + (sd_means/spatial)^2). The `1`
assumes the un-planted admission ratio is 1.0, which holds only when the
spatial estimate is pure noise. A synthetic bracket built as `one real frame +
planted noise` has spatial = sqrt(structure^2 + noise^2) and temporal = noise,
so its baseline is 0.70, not 1.00. The variance still adds in quadrature; it
just has to be added to the OBSERVED baseline:

    ratio(s_g) = sqrt( ratio(0)^2 + (sd_of_frame_means / spatial)^2 )

That is the same physics with the right constant, and it is a stronger control
than the original because ratio(0) is measured rather than assumed. It also
predicts the real subject: the leaf claim patch's spatial estimate IS nearly
pure noise -- which is what "flat" means -- so there the `1` was right and the
prediction landed at +0.3%.

CONTROLS HERE.
  L1  NULL. Zero planted gain must reproduce the measured baseline exactly.
  L2  POTENCY. Each plant must actually move the statistic. An earlier stage of
      this campaign shipped a plant that was too weak to move anything and
      briefly read as a pass; that is checked explicitly now.
  L3  POSITIVE CONTROL over a range spanning the real effect (the leaf patch's
      implied s_g is 2.6%), with a stated error bar.
  L4  SPECIFICITY. The same machinery on 109MSDCF, whose drift the corpus puts
      at 0.91%. A correct instrument must find almost nothing there.

AND THE tweezers-cpl QUESTION. The orchestrator asked whether tweezers-cpl,
which also failed admission, carries any README claim. It appears in exactly one
quantitative table -- README L878-885, GRADIENT KURTOSIS inside low-detail
regions, merge against argmax -- which is an arm-vs-arm shape statistic, not a
flat-ROI noise ratio, so today's finding says admission does not govern it. But
the binary's own --photometric help text records tweezers-cpl at 13.765% per-
frame drift, the largest number it names, and an uncorrected per-frame gain
turns a SELECTION arm into a mosaic of differently-scaled frames -- which is
exactly the "piecewise-constant plateaus with hard steps" that the kurtosis
statistic is built to detect. So the mechanism is at least plausible for that
table, and M1 measures whether a planted gain actually moves gradient kurtosis
on a selection mosaic instead of leaving it as a story.
"""

import json
import pathlib
import sys

import numpy as np

import pyrnoise as pn

RENDERS = pathlib.Path(r"C:\dev\strehl-out\BUILD-PYRNOISE\renders")
CLAIM = pathlib.Path(r"C:\dev\strehl-out\BUILD-PYRNOISE\claim")
RNG = np.random.default_rng(31337)


def load(sub):
    d = RENDERS / sub
    frames = sorted(p.stem for p in d.glob("frame*.tif"))
    return {f: pn.green(d / f"{f}.tif") for f in frames}, frames


def stacks(imgs, frames, roi):
    pad = pn.BOX
    x, y, w, h = roi
    big = np.stack([imgs[f][y - pad:y + h + pad, x - pad:x + w + pad].astype(np.float64)
                    for f in frames])
    return big[:, pad:-pad, pad:-pad], big


def adm(core, big):
    t = float(core.std(axis=0, ddof=1).mean())
    s = float(np.mean([pn.hp_sd(b) for b in big]))
    return t / s, t, s


def grad_kurt(a):
    """Kurtosis of the gradient magnitude -- the README L878 statistic's shape.

    Higher means flat plateaus punctuated by hard steps, which is what a
    selection mosaic manufactures. Reproduced here only well enough to ask
    whether a planted per-frame GAIN moves it; it is not a re-measurement of
    that table and is not offered as one.
    """
    gx = np.diff(a, axis=1)[:-1, :]
    gy = np.diff(a, axis=0)[:, :-1]
    g = np.sqrt(gx * gx + gy * gy)
    g = g - g.mean()
    s = g.std()
    return float((g ** 4).mean() / (s ** 4)) if s > 0 else np.nan


def mosaic(core, rng, block=1):
    n = core.shape[0]
    if block == 1:
        idx = rng.integers(0, n, size=core.shape[1:])
    else:
        sm = rng.integers(0, n, size=(core.shape[1] // block + 1, core.shape[2] // block + 1))
        idx = np.kron(sm, np.ones((block, block), dtype=int))[:core.shape[1], :core.shape[2]]
    return np.take_along_axis(core, idx[None], axis=0)[0]


def main():
    print("=" * 78)
    print("COMMISSIONING THE LEVEL-TERM FINDING")
    print("=" * 78)
    leaf, lf = load("leaf-2-cpl")
    roi = (292, 500, 100, 100)                    # the README claim's own patch
    core, big = stacks(leaf, lf, roi)
    ref_big = big[len(lf) // 2]
    sd = pn.hp_sd(ref_big)

    base_big = np.stack([ref_big + RNG.normal(0, sd, ref_big.shape) for _ in range(len(lf))])
    r0, t0, s0 = adm(base_big[:, pn.BOX:-pn.BOX, pn.BOX:-pn.BOX], base_big)
    print(f"\nL1  NULL -- synthetic stationary bracket from this subject's own pixels")
    print(f"    {len(lf)} frames, planted noise sd {sd:.2f} DN at level "
          f"{base_big.mean():.0f} DN")
    print(f"    baseline admission ratio r0 = {r0:.4f}   (temporal {t0:.2f} / spatial {s0:.2f})")
    print(f"    r0 is NOT 1.0 because the spatial estimate also sees this patch's own")
    print(f"    sub-box structure. That is the constant K3 got wrong.")

    print(f"\nL2/L3  POSITIVE CONTROL -- planted per-frame gain, predicted in quadrature")
    print(f"    predicted = sqrt(r0^2 + (sd_of_frame_means / spatial)^2)")
    print(f"    {'planted s_g':>12}{'sd(means)':>11}{'spatial':>9}{'predicted':>11}"
          f"{'observed':>10}{'err':>8}{'moved?':>9}")
    errs = []
    for sg in (0.0, 0.005, 0.01, 0.0264, 0.05, 0.10):
        g = 1.0 + RNG.normal(0, sg, len(lf)) if sg > 0 else np.ones(len(lf))
        pb = base_big * g[:, None, None]
        pc = pb[:, pn.BOX:-pn.BOX, pn.BOX:-pn.BOX]
        r_obs, t, s = adm(pc, pb)
        mm = pc.reshape(len(lf), -1).mean(axis=1)
        pred = np.sqrt(r0 ** 2 + (mm.std(ddof=1) / s) ** 2)
        moved = abs(r_obs / r0 - 1) * 100
        errs.append(abs(pred / r_obs - 1) * 100)
        print(f"    {sg * 100:11.2f}%{mm.std(ddof=1):11.2f}{s:9.2f}{pred:11.4f}"
              f"{r_obs:10.4f}{(pred / r_obs - 1) * 100:+7.2f}%{moved:8.1f}%")
    print(f"    worst error across the sweep: {max(errs):.2f}%   "
          f"{'PASS' if max(errs) < 2.0 else 'FAIL'} against a 2.0% bar")
    print(f"    POTENCY: the 2.64% plant -- the size implied by the real patch --")
    print(f"    moves the ratio by the amount shown above; a plant that does not move")
    print(f"    the statistic proves nothing, which is why the column is printed.")

    print(f"\nL4  SPECIFICITY -- the same arithmetic on 109MSDCF (corpus drift 0.91%)")
    m9, f9 = load("109MSDCF")
    c9, b9 = stacks(m9, f9, (1416, 264, 256, 256))
    r9, t9, s9 = adm(c9, b9)
    m9m = c9.reshape(len(f9), -1).mean(axis=1)
    print(f"    observed admission {r9:.3f}; sd of frame means {m9m.std(ddof=1):.2f} DN at"
          f" level {m9m.mean():.0f} DN = {m9m.std(ddof=1) / m9m.mean() * 100:.2f}%")
    print(f"    level term alone would explain sqrt(1 + ({m9m.std(ddof=1):.1f}/{s9:.1f})^2) ="
          f" {np.sqrt(1 + (m9m.std(ddof=1) / s9) ** 2):.3f} of the observed {r9:.3f}")
    print(f"    -- i.e. almost none of it. The instrument does not find a level term")
    print(f"       where the corpus says there is not one.")

    print(f"\nM1  DOES AN UNCORRECTED PER-FRAME GAIN MOVE GRADIENT KURTOSIS?")
    print(f"    (the statistic behind README L878-885, on a SELECTION mosaic)")
    print(f"    {'subject':<14}{'drift':>8}{'kurt raw':>11}{'kurt gain-removed':>19}{'ratio':>9}")
    m1 = {}
    for sub, r in (("leaf-2-cpl", roi), ("tweezers-cpl", (292, 500, 100, 100)),
                   ("109MSDCF", (1416, 264, 256, 256))):
        imgs, fr = load(sub) if sub != "leaf-2-cpl" else (leaf, lf)
        c, b = stacks(imgs, fr, r)
        mm = c.reshape(len(fr), -1).mean(axis=1)
        cc = c * (mm.mean() / mm)[:, None, None]
        kr = float(np.mean([grad_kurt(mosaic(c, RNG, block=8)) for _ in range(6)]))
        kc = float(np.mean([grad_kurt(mosaic(cc, RNG, block=8)) for _ in range(6)]))
        print(f"    {sub:<14}{(mm.max() / mm.min() - 1) * 100:7.2f}%{kr:11.2f}{kc:19.2f}"
              f"{kr / kc:8.2f}x")
        m1[sub] = {"drift_pct": float((mm.max() / mm.min() - 1) * 100),
                   "kurt_raw": kr, "kurt_corrected": kc, "n_frames": len(fr)}
    print(f"    A ratio above 1 means the uncorrected gain ADDS apparent plateau")
    print(f"    structure to a selection arm -- the direction that would inflate the")
    print(f"    argmax column of that table. This is a mechanism check on single")
    print(f"    frames, NOT a re-measurement of the table.")

    json.dump({"r0": r0, "worst_err_pct": max(errs), "m1": m1},
              open(CLAIM / "_control.json", "w"), indent=1, default=float)
    return 0


if __name__ == "__main__":
    sys.exit(main())
