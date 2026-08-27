"""Does the exact-ceiling deficit survive removing the noise-floor subtraction?

THE WORRY. The instrument subtracts each image's own noise floor -- the 5th
percentile of its per-block high-pass energy -- before comparing. On three of the
four exact-ceiling subjects the MASTER's floor is HIGHER than the frames' median
(119MSDCF 908.7 vs 663.6, coffee-bubbles 8381.2 vs 6034.2, flower-bud 758.1 vs
672.3), so more is subtracted from the master than from its reference. If that
subtraction is even slightly wrong, it pushes the ratio down on exactly the
subjects where the deficit was found, which would manufacture the headline.

THE TEST, and why it is one-sided in a useful way. Recompute the ratio with the
subtraction switched off. Unsubtracted, noise counts as detail, and the master
here carries MORE noise than its frames -- so the no-subtraction arm is biased
TOWARDS the master looking sharper. If a deficit survives even under an estimator
tilted in the master's favour, the subtraction is not what produced it. If the
deficit vanishes, the headline was the floor term and must be withdrawn.

This deliberately does not run the seven commissioning arms: it is not issuing a
verdict, it is asking whether one term moves an existing verdict. Both columns
come from the same call to the same primitive, so nothing but the subtraction
differs between them.

Usage:
  python floor_sensitivity.py <size> <subject>:<n> [<subject>:<n> ...]
"""

import sys
import pathlib
import numpy as np
import tifffile

sys.path.insert(0, str(pathlib.Path(__file__).parent))
from softness_verdict3 import detail as _d  # noqa: E402
from softness_verdict3 import (  # noqa: E402
    luma_linear, contrast, shift_of, warp, boot_ci,
)
from corpus_softness import SCRATCH, BLOCK, pick_tile  # noqa: E402


def envelope(D, C, cfloor):
    D = np.where(C > cfloor, D, -np.inf)
    env = D.max(axis=0)
    valid = np.isfinite(env)
    return np.where(valid, env, 0.0), valid


def main():
    size = int(sys.argv[1])
    print(f"{'subject':<24}{'n':>5}{'sites':>7}{'subtracted':>12}"
          f"{'raw (no sub)':>14}   verdict")
    print("-" * 78)
    for spec in sys.argv[2:]:
        subject, n = spec.split(":")
        n = int(n)
        out = SCRATCH / subject
        mfull = luma_linear(tifffile.imread(str(out / "MASTER.tiff")))
        tx, ty = pick_tile(mfull, size)
        master = mfull[ty:ty + size, tx:tx + size].copy()
        del mfull

        fts = sorted(out.glob("frame-*.tiff"))[:n]
        Ds, Dr, Cs = [], [], []
        for ft in fts:
            t = luma_linear(tifffile.imread(str(ft)))[ty:ty + size, tx:tx + size].copy()
            dx, dy = shift_of(master, t)
            t = warp(t, dx, dy)
            d, fl = _d(t, BLOCK)
            Ds.append(d)
            Dr.append(d + fl)
            Cs.append(contrast(t, BLOCK))
        Ds, Dr, Cs = np.stack(Ds), np.stack(Dr), np.stack(Cs)

        cm = contrast(master, BLOCK)
        cfloor = float(np.percentile(cm, 65))
        md, mfl = _d(master, BLOCK)

        es, vs = envelope(Ds, Cs, cfloor)
        er, vr = envelope(Dr, Cs, cfloor)
        live = (cm > cfloor) & vs & vr

        sub = float(np.median((md / np.maximum(es, 1e-12))[live]))
        raw = float(np.median(((md + mfl) / np.maximum(er, 1e-12))[live]))
        lo, hi = boot_ci(((md + mfl) / np.maximum(er, 1e-12))[live])
        verdict = ("deficit SURVIVES" if hi < 1.0 else
                   "not significant" if lo < 1.0 < hi else "no deficit")
        print(f"{subject:<24}{len(fts):>5}{int(live.sum()):>7}{sub:>12.4f}"
              f"{raw:>14.4f}   {verdict} [{lo:.3f},{hi:.3f}]")


if __name__ == "__main__":
    main()
