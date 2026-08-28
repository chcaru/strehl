#!/usr/bin/env python3
"""Probe: geometry, timing, and whether the two statistics behave at all.

Prints, for one frame of one subject: plane shape, per-band variance and
covariance in a deliberately STRUCTURED tile and a deliberately FLAT tile.
The thing being checked is that `cov` separates them while `var` does not
separate them nearly as well -- i.e. that the noise correction has power.
"""
from __future__ import annotations

import os
import sys
import time

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ora  # noqa: E402

TS = 128


def main() -> int:
    subject = sys.argv[1] if len(sys.argv) > 1 else "flowers-cpl"
    fs = ora.frames_of(subject)
    print(f"subject : {subject}  frames={len(fs)}")
    k = len(fs) // 2
    t0 = time.time()
    g1, g2 = ora.green_pair(fs[k])
    t1 = time.time()
    print(f"frame {k}: green sub-plane shape={g1.shape} decode={t1 - t0:.2f}s "
          f"level={float(g1.mean()):.1f} DN")
    st = ora.tile_stats(g1, g2, TS)
    t2 = time.time()
    print(f"tiles   : {st['nr']}x{st['nc']} = {st['nr'] * st['nc']} of {TS}px  "
          f"bands={ora.NBAND}  stats={t2 - t1:.2f}s")

    # Rank tiles by band-1 covariance (noise-free signal power) to find a
    # genuinely structured tile and a genuinely flat one, then print both.
    c = st["cov"][1]
    flat_i = int(np.argmin(c))
    rich_i = int(np.argmax(c))
    for name, i in (("RICHEST", rich_i), ("FLATTEST", flat_i)):
        r, cc = divmod(i, st["nc"])
        print(f"\n{name} tile r={r} c={cc}  level={st['level'][r, cc]:.1f} DN")
        print("  band   var(=sig+noise)     cov(=sig)      noise=var-cov   sig/noise")
        for b in range(ora.NBAND):
            v = st["var"][b, r, cc]
            cv = st["cov"][b, r, cc]
            n = v - cv
            print(f"  {b}    {v:14.2f} {cv:14.2f} {n:14.2f} "
                  f"{(cv / n if n > 0 else float('nan')):10.4f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
