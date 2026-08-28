r"""Why does coffee-bean read above its rim-free pedestal?

The extended ladder acquits twelve of the thirteen on the headline number and
leaves coffee-bean 4.4 points above it.  Two explanations survive that fact and
they are not the same: a rim, or a shoulder whose fluctuation is not shaped
like the synthetic's.  The ladder's roughener is band-limited Gaussian.  A
bean surface covered in specular crystal is not Gaussian; it is heavy-tailed,
and a max over six samples is exactly the statistic that a heavy tail inflates
while leaving the standard deviation alone.

Two in-image controls, neither of which needs a synthetic scene:

  KURTOSIS  excess kurtosis of the per-edge shoulder residual, against the
            synthetic's.  A heavier tail at matched sd means the ladder
            under-prices that subject's pedestal.
  DARK ARM  the same statistic on the DARK shoulder, t=-7..-2, which is the
            same texture on the same edges.  Ringing is a bright overshoot
            paired with a dark undershoot; texture is symmetric.  rimaxis
            already computes it and printcert4 already ignores it.
"""
import io
import json
import os
import sys

import numpy as np

import vr_lib as V
import vr_specificity as S
from vr_ladder import THIRTEEN, CONTROLS
import rimv6


def shoulder_stats(em):
    P = np.asarray(em["prof"], float)
    b = P[:, rimv6.IB]
    d = P[:, rimv6.ID]
    rb = b - b.mean(axis=1, keepdims=True)
    s = rb.std(axis=1, ddof=1)
    x = (rb / np.maximum(s[:, None], 1e-9)).ravel()
    return dict(kurt=float(((x ** 4).mean()) - 3.0),
                p999=float(np.percentile(x, 99.9)),
                sd=float(np.median(s)),
                bright=float(np.median(b.max(axis=1) - 1.0)),
                dark=float(np.median(-(d.min(axis=1)))),
                n=int(P.shape[0]))


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    print("%-26s %7s %8s %8s %9s %9s %8s"
          % ("subject", "sd", "kurt", "p99.9", "bright", "dark", "d/b"))
    out = []
    base = S.scene()
    for amp, tag in ((0.048, "SYNTH sd~0.119"), (0.090, "SYNTH sd~0.196")):
        g = S.roughen(base, amp, seed=S.SEED + 1)
        rec, sel, ref, em = V.run_pipeline(g, np.zeros(g.shape, bool), ntile=40)
        st = shoulder_stats(em)
        print("%-26s %7.4f %8.2f %8.2f %8.3f%% %8.3f%% %8.2f"
              % (tag, st["sd"], st["kurt"], st["p999"], 100 * st["bright"],
                 100 * st["dark"], st["dark"] / max(st["bright"], 1e-9)))
        st["subject"] = tag
        out.append(st)
    print("-" * 82)
    for name in THIRTEEN + CONTROLS:
        p = os.path.join(V.SHIP, name + "--SHIP-V4.tiff")
        g, clip = V.read_lum(p)
        rec, sel, ref, em = V.run_pipeline(g, clip)
        if em is None or not len(em["prof"]):
            print("%-26s no profiles" % name)
            continue
        st = shoulder_stats(em)
        print("%-26s %7.4f %8.2f %8.2f %8.3f%% %8.3f%% %8.2f"
              % (name, st["sd"], st["kurt"], st["p999"], 100 * st["bright"],
                 100 * st["dark"], st["dark"] / max(st["bright"], 1e-9)))
        st["subject"] = name
        out.append(st)
        del g, clip, em
    json.dump(out, io.open(os.path.join(V.SCRATCH, "shoulder.json"), "w",
                           encoding="utf-8"), indent=1, default=float)
