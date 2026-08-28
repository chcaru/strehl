# -*- coding: utf-8 -*-
"""V-DILUTE: run the candidate-set arm ladder against the selection premium.

Commissioning gate, checked before any other number is believed: `argmax` at
N=79 on 112MSDCF must reproduce V-NEVERWORSE's **240.70x** within 5%. That is
the only evidence that I inherited their gauge rather than built a lookalike.

Two numbers are reported for every arm, always together, because ORCH's
criterion 2 refuses an arm that wins one by losing the other:

  PREMIUM   manufactured noise power at 0.30-0.35 cyc/px on the synthetic twin,
            divided by the plain mean's. Lower is better; 1.0 is the mean.
  SHARP     NOISE-CORRECTED signal power at 0.20-0.25 cyc/px on the REAL stack,
            relative to shipping. 0.20-0.25 is the band qualified as SIGNAL on
            this subject (S/y = 2.43); 0.30-0.35 is empty of scene content
            (S/y = 0.00) and cannot carry an acuity claim here.

Noise correction is a subtraction, not a ratio: the same arm is run on the twin,
whose residual band power IS that arm's noise contribution, and it is subtracted
from the real reading. Raw band power counts noise as sharpness.
"""
import io
import json
import os
import sys
import time

import numpy as np

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8",
                              errors="replace")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from vd_prem_lib import (OUT, PREM_BAND, SHARP_BAND, Stack, load_green,  # noqa
                         pick, raw_band, run_arm)
sys.path.insert(0, r"C:\dev\blog\death-of-software\projects\strehl"
                   r"\experiments\V-NEVERWORSE")
import vn_pyr as VP                                                      # noqa

FULL = ("mean", "shipping", "argmax", "random", "oracle", "loo1", "loo2",
        "punctured", "pool2", "capK8", "capK4", "peakfit",
        "winavg2", "winavg4", "winavg8")
SCALE = ("mean", "shipping", "argmax", "loo1", "winavg4")


def main():
    subj = sys.argv[1] if len(sys.argv) > 1 else "112MSDCF"
    ns = [int(x) for x in sys.argv[2].split(",")] if len(sys.argv) > 2 else [79]
    arms = sys.argv[3].split(",") if len(sys.argv) > 3 else list(FULL)
    seed = int(sys.argv[4]) if len(sys.argv) > 4 else 20260827
    os.makedirs(OUT, exist_ok=True)

    g = load_green(subj)
    n = len(g)
    var0, read2, gph = VP.fit_variance(g[0])
    if gph < 0:
        print("REFUSED: fitted photon gain is negative")
        return 2
    sd = np.sqrt(np.maximum(var0, 0.0))
    base = g.mean(axis=0)
    rng = np.random.default_rng(seed)
    twin_all = np.stack([base + rng.normal(0.0, 1.0, base.shape) * sd
                         for _ in range(n)])
    print("subject %s  N=%d  read2=%.2f  photon_gain=%.5f" % (subj, n, read2, gph))
    print("premium band %.2f-%.2f   sharpness band %.2f-%.2f\n"
          % (PREM_BAND + SHARP_BAND))

    varp = VP.gauss_pyr(var0, 7)
    results = {}
    for N in ns:
        idx = pick(n, N)
        assert idx[0] == 0 and idx[-1] == n - 1 and len(set(idx)) == len(idx)
        print("=" * 100)
        print("N=%d  (range pinned to frames %d..%d, no repeats)"
              % (len(idx), idx[0], idx[-1]))
        sr = Stack(g[idx])
        st = Stack(twin_all[idx])
        # An independent twin, used ONLY as the oracle's score source: its
        # noise is independent of the twin being merged, so the score has zero
        # correlation with the copied sample while N is unchanged. Built
        # lazily -- it costs ~700 MB and only one arm needs it.
        alt = None
        if "oracle" in arms:
            rng2 = np.random.default_rng(99001)
            alt = Stack(np.stack([base + rng2.normal(0.0, 1.0, base.shape) * sd
                                  for _ in idx]))

        rows = {}
        print("  %-11s %11s %11s %10s %11s %9s"
              % ("arm", "noise_pow", "PREMIUM", "sharp_raw", "sharp_corr",
                 "SHARP/ship"))
        for name in arms:
            t0 = time.time()
            rec_r = run_arm(name, sr, varp, np.random.default_rng(4242),
                            alt=alt if name == "oracle" else None)
            rec_t = run_arm(name, st, varp, np.random.default_rng(4242),
                            alt=alt if name == "oracle" else None)
            resid = rec_t - base
            npow = raw_band(resid, PREM_BAND)
            s_raw = raw_band(rec_r, SHARP_BAND)
            s_noi = raw_band(resid, SHARP_BAND)
            # Several bands, so a loss pushed out of the scored band cannot
            # hide. This answers my own objection to round 2: an arm aimed at
            # the band the premium lives in must be shown not to have moved
            # any neighbouring band either.
            multi = {}
            for b in ((0.10, 0.15), (0.17, 0.20), (0.20, 0.25), (0.25, 0.30)):
                multi["%.2f-%.2f" % b] = (raw_band(rec_r, b)
                                          - raw_band(resid, b))
            rows[name] = dict(noise_pow=npow, sharp_raw=s_raw,
                              sharp_noise=s_noi, sharp_corr=s_raw - s_noi,
                              prem_sig=raw_band(rec_r, PREM_BAND) - npow,
                              multi=multi, secs=time.time() - t0)
            print("  %-11s %11.4f %11s %10.2f %11.2f %9s   (%.0fs)"
                  % (name, npow, "-", s_raw, s_raw - s_noi, "-",
                     rows[name]["secs"]))
            del rec_r, rec_t, resid

        mn = rows["mean"]["noise_pow"] if "mean" in rows else None
        sh = rows["shipping"]["sharp_corr"] if "shipping" in rows else None
        shm = rows["shipping"]["multi"] if "shipping" in rows else None
        bands = ["0.10-0.15", "0.17-0.20", "0.20-0.25", "0.25-0.30"]
        print("\n  %-11s %11s %11s %9s | %s"
              % ("arm", "noise_pow", "PREMIUM", "SHARP/shp",
                 " ".join("%9s" % b for b in bands)))
        for name in arms:
            r = rows[name]
            prem = r["noise_pow"] / mn if mn else float("nan")
            sr_ = r["sharp_corr"] / sh if sh else float("nan")
            r["premium"] = prem
            r["sharp_rel"] = sr_
            rel = [r["multi"][b] / shm[b] if shm and shm[b] else float("nan")
                   for b in bands]
            r["multi_rel"] = dict(zip(bands, rel))
            worst = min([v for v in rel if v == v] or [float("nan")])
            r["worst_band"] = worst
            print("  %-11s %11.4f %11.2f %9.4f | %s   worst %.4f"
                  % (name, r["noise_pow"], prem, sr_,
                     " ".join("%9.4f" % v for v in rel), worst))
        results[str(len(idx))] = rows

        if len(idx) == 79 and "argmax" in rows:
            got = rows["argmax"]["premium"]
            off = abs(got - 240.70) / 240.70
            print("\n  COMMISSIONING: argmax premium at N=79 = %.2f against "
                  "V-NEVERWORSE's 240.70 (%.1f%% off)" % (got, 100 * off))
            print("  %s" % ("ok  gauge inherited"
                            if off <= 0.05 else
                            "FAILED  gauge NOT reproduced -- no other number "
                            "in this run may be quoted"))
        del sr, st, alt

    json.dump(results, io.open(os.path.join(OUT, "arms_%s_%d.json" % (subj, seed)), "w",
                               encoding="utf-8"), indent=1)
    print("\nwrote %s" % os.path.join(OUT, "arms_%s_%d.json" % (subj, seed)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
