"""M47 -- does fact 127's deconvolution-wins fraction survive the ISO-50 gain fix?

Re-measures M20-V's `v7_corpus.py` statistic on the two ISO-50 stacks with BOTH
gains in the same pass, so the old value is an in-run control rather than a
quotation.  A run whose `iso/436.8` column does not reproduce 30.5 / 65.8 is a
harness defect, not a finding -- that is the input that makes this FAIL (rule 20).

109MSDCF (ISO 160) is the placebo: both columns must be identical there, because
max(160,100) == 160.  If it moves, the harness is wrong.

Statistic, verbatim from v7_corpus.py: 9x9 BIASED box variance on the G1 plane,
nvar = g*max(m,0) + (RN_e*g)^2, sig = sqrt(max(v-nvar,0)),
rel = sqrt(nvar)/max(sig,1e-6), minimised over frames, then the fraction below
M20's crossover 0.3440 and M20-V's oracle 0.5734.

Read-only: rawpy.imread never writes.  Rule 32: the plane is copied inside the
`with` on the same line as the slice.
"""
import glob
import os
import sys

import numpy as np
import rawpy
from scipy.ndimage import uniform_filter

W, BLACK, CROSS, ORACLE = 9, 512.0, 0.3440, 0.5734

STACKS = [
    ("109MSDCF", r"D:\personal\macro\109MSDCF", 160.0),   # placebo, ISO 160
    ("119MSDCF", r"D:\personal\macro\119MSDCF", 50.0),
    ("coffee-bean", r"D:\personal\macro\coffee-bean", 50.0),
]
PUBLISHED = {"109MSDCF": 15.1, "119MSDCF": 30.5, "coffee-bean": 65.8}


def gains(iso):
    """(marked-ISO gain, base-ISO-floored gain, read noise in e-)."""
    return iso / 436.8, max(iso, 100.0) / 436.8, (1.47 if iso >= 400 else 4.20)


def run(name, d, iso):
    files = sorted(glob.glob(os.path.join(d, "*.ARW")))
    g_old, g_new, rn = gains(iso)
    best = {"old": None, "new": None}
    for f in files:
        with rawpy.imread(f) as r:
            gp = r.raw_image_visible[0::2, 1::2].astype(np.float32) - BLACK
        m = uniform_filter(gp, W)
        m2 = uniform_filter(gp * gp, W)
        v = np.maximum(m2 - m * m, 0.0)
        mpos = np.maximum(m, 0.0)
        for key, g in (("old", g_old), ("new", g_new)):
            nvar = g * mpos + (rn * g) ** 2
            sig = np.sqrt(np.maximum(v - nvar, 0.0))
            rel = np.sqrt(nvar) / np.maximum(sig, 1e-6)
            best[key] = rel if best[key] is None else np.minimum(best[key], rel)
            del nvar, sig, rel
        del gp, m, m2, v, mpos
    out = {}
    for key in ("old", "new"):
        b = best[key]
        out[key] = dict(
            p50=float(np.median(b)),
            f_cross=float(np.mean(b < CROSS)) * 100.0,
            f_oracle=float(np.mean(b < ORACLE)) * 100.0,
        )
    return len(files), g_old, g_new, out


def main():
    print("M47 -- fact 127 / 138 under the corrected ISO-50 gain")
    print(f"{'stack':>13} {'ISO':>5} {'fr':>4} | {'g(marked)':>10} {'g(floored)':>11} | "
          f"{'<0.344 old':>11} {'<0.344 new':>11} | {'<0.573 old':>11} {'<0.573 new':>11} | "
          f"{'p50 old':>8} {'p50 new':>8} | published")
    for name, d, iso in STACKS:
        n, go, gn, o = run(name, d, iso)
        print(f"{name:>13} {iso:>5.0f} {n:>4} | {go:>10.5f} {gn:>11.5f} | "
              f"{o['old']['f_cross']:>10.1f}% {o['new']['f_cross']:>10.1f}% | "
              f"{o['old']['f_oracle']:>10.1f}% {o['new']['f_oracle']:>10.1f}% | "
              f"{o['old']['p50']:>8.4f} {o['new']['p50']:>8.4f} | {PUBLISHED[name]:.1f}%")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
