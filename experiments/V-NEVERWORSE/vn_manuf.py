# -*- coding: utf-8 -*-
"""Does the merge MANUFACTURE mid-scale structure? A synthetic null subject.

The standing defence of every blotch conviction is that the merge is being
charged for resolved detail no single frame contains. That defence is
untestable on real data, because real frames really do differ in focus.

This removes the defence by construction. Build a stack whose frames carry
IDENTICAL scene content and differ only by independent noise at the fitted
sensor level. No frame is better focused than any other, so there is nothing
for the merge to resolve and nothing it can legitimately add. On such a stack
a sound merge must be no blotchier than its best frame -- in fact it should be
much cleaner, since averaging n frames cuts noise by sqrt(n).

Any excess here is manufactured. It cannot be resolved structure, because
there is no structure to resolve.
"""
import io
import json
import os
import sys

import numpy as np

import vn_pyr as VP
from vn_plateau import BETA, SHIP, blotch, sharpness
from vn_confexp import merge_confident
from vn_snrref import load

OUT = r"C:\dev\strehl-out\V-NEVERWORSE\manufacture"


def synth(frames, var0, seed=20260827):
    """Identical scene, independent noise at the fitted level."""
    rng = np.random.default_rng(seed)
    base = np.mean([f.astype(np.float64) for f in frames], axis=0)
    sd = np.sqrt(np.maximum(var0, 0.0))[:, :, None]
    return [base + rng.normal(0.0, 1.0, base.shape) * sd
            for _ in range(len(frames))]


def commission(base, var0):
    """Both directions, on the synthetic-null construction itself.

    The failure this guards against is a null that is not null: if the
    synthetic frames accidentally differ in focus, an excess would be
    legitimate and the whole argument collapses.
    """
    ok, bad = [], []
    rng = np.random.default_rng(7)
    sd = np.sqrt(np.maximum(var0, 0.0))[:, :, None]
    fs = [base + rng.normal(0.0, 1.0, base.shape) * sd for _ in range(6)]
    sh = [sharpness(f) for f in fs]
    rel = (max(sh) - min(sh)) / max(np.mean(sh), 1e-12)
    (ok if rel < 0.02 else bad).append(
        "NULL IS NULL: sharpness spread across the synthetic frames is "
        "%.4f of the mean (must be ~0; a real stack reads far higher)" % rel)

    # PLANTED IMPROVEMENT: give ONE frame genuinely more detail. The stack is
    # then no longer null and the sharpness spread MUST detect it, or the
    # check above is unfalsifiable.
    g = list(fs)
    h, w = base.shape[:2]
    y, x = np.mgrid[0:h, 0:w]
    g[0] = g[0] + 300.0 * ((y + x) % 2).astype(np.float64)[:, :, None]
    sh2 = [sharpness(f) for f in g]
    rel2 = (max(sh2) - min(sh2)) / max(np.mean(sh2), 1e-12)
    (ok if rel2 > 0.10 else bad).append(
        "PLANTED FOCUS ADVANTAGE detected: spread rises to %.4f (must be "
        "large, or the null check above could never fail)" % rel2)

    # PLANTED DEGRADATION: blur one frame. Also non-null, opposite sign.
    d = list(fs)
    d[1] = VP.smooth5(VP.smooth5(d[1]))
    sh3 = [sharpness(f) for f in d]
    rel3 = (max(sh3) - min(sh3)) / max(np.mean(sh3), 1e-12)
    (ok if rel3 > 0.10 else bad).append(
        "PLANTED BLUR detected: spread rises to %.4f (must be large)" % rel3)
    return ok, bad


def res_band(r):
    """Absolute 50-400 px band energy of a residual (no mean normalisation --
    the residual's mean is ~0, so a ratio to it is meaningless)."""
    return blotch(r)[1]


def res_fine(r):
    return float(VP.lap_pyr(r[:, :, 1].astype(np.float64), 1)[0][0].std())


def main():
    os.makedirs(OUT, exist_ok=True)
    subj = sys.argv[1] if len(sys.argv) > 1 else "coffee-bubbles"
    frames = load(subj)
    var0, read2, gph = VP.fit_variance(frames[0][:, :, 1])
    if gph < 0:
        print("REFUSED: fitted photon gain is negative")
        return 2
    print("%s: %d OK frames" % (subj, len(frames)))

    base = np.mean([f.astype(np.float64) for f in frames], axis=0)
    print("\ncommissioning the synthetic null (both directions):")
    ok, bad = commission(base, var0)
    for l in ok:
        print("  ok      " + l)
    for l in bad:
        print("  FAILED  " + l)
    if bad:
        print("REFUSED: the synthetic null is not commissioned")
        return 2

    fs = synth(frames, var0)
    n = len(fs)

    # Measure the RESIDUAL against the known base, not the image. Every arm
    # shares the same base, whose own mid-band content is large; measuring the
    # image lets that common term dominate and the statistic reads ~1.000x for
    # every arm regardless of what the merge did. The first version of this
    # script did exactly that, and its sqrt(n) control caught it: the plain
    # mean read 1.006x where 19 averaged noise fields must read 0.229x.
    srcb = min(res_band(f - base) for f in fs)
    srcs = max(res_fine(f - base) for f in fs)
    print("\n  best synthetic source residual: band %.5f  fine %.5f"
          % (srcb, srcs))
    print("\n  %-18s %12s %12s %14s %10s"
          % ("arm", "band", "fine", "band vs best", "fine"))
    rows = []
    arms = (("a_shipping", dict(SHIP)),
            ("c_flat_exponent", dict(SHIP, exponent=1.0, sharpen=1.0)),
            ("b_plain_mean", dict(SHIP, mode="mean")))
    for name, cfg in arms:
        rec, _ = VP.merge(fs, cfg, BETA, var0)
        r = rec - base
        b, s = res_band(r), res_fine(r)
        rows.append(dict(arm=name, band=b, fine=s,
                         band_vs_best_source=b / srcb,
                         fine_vs_best_source=s / srcs))
        print("  %-18s %12.5f %12.5f %13.3fx %9.3fx"
              % (name, b, s, b / srcb, s / srcs))

    # The fix as described collapses selectivity toward p=1. p=1 is still
    # WEIGHTING by noise-driven band energy, not averaging. These two arms
    # separate "gentler weighting" from "actual averaging" on data where the
    # right answer is known.
    for name, p_lo in (("d_conf_to_p1", 1.0), ("e_conf_to_mean", 0.0)):
        rec, _ = merge_confident(fs, SHIP, BETA, var0, kappa=0.01, p_lo=p_lo)
        r = rec - base
        b, s = res_band(r), res_fine(r)
        rows.append(dict(arm=name, band=b, fine=s, p_lo=p_lo, kappa=0.01,
                         band_vs_best_source=b / srcb,
                         fine_vs_best_source=s / srcs))
        print("  %-18s %12.5f %12.5f %13.3fx %9.3fx"
              % (name, b, s, b / srcb, s / srcs))

    # DECOMPOSITION. Two noise-driven decisions are stacked in this merge:
    # WHICH frames are admitted (excess = max(sq - floor, 0) is a hard,
    # per-pixel, noise-driven threshold) and HOW they are weighted once
    # admitted (the exponent ladder). These arms turn each off separately, so
    # the manufacture can be attributed rather than guessed at.
    for name, cfg, kw in (
            ("f_admit_only", dict(SHIP), dict(kappa=0.0, p_lo=0.0)),
            ("g_exponent_only", dict(SHIP, gate=0.0), None)):
        if kw is None:
            rec, _ = VP.merge(fs, cfg, BETA, var0)
        else:
            rec, _ = merge_confident(fs, cfg, BETA, var0, **kw)
        r = rec - base
        b, s = res_band(r), res_fine(r)
        rows.append(dict(arm=name, band=b, fine=s,
                         band_vs_best_source=b / srcb,
                         fine_vs_best_source=s / srcs))
        print("  %-18s %12.5f %12.5f %13.3fx %9.3fx"
              % (name, b, s, b / srcb, s / srcs))

    expect = 1.0 / np.sqrt(n)
    mean = rows[2]["band_vs_best_source"]
    ship = rows[0]["band_vs_best_source"]
    print("\n  POSITIVE CONTROL: averaging %d independent noise fields must "
          "cut the band energy to %.3fx" % (n, expect))
    print("  the plain mean reads %.3fx" % mean)
    if abs(mean - expect) > 0.25 * expect:
        print("  REFUSED: the statistic does not respond to noise averaging "
              "as it must, so it cannot be trusted to see manufacture either")
        return 2
    print("  ok      the statistic responds to noise averaging correctly")
    print("\n  shipping selection reads %.3fx against the plain mean's %.3fx"
          % (ship, mean))
    print("  MANUFACTURE FACTOR, selection over mean: %.2fx"
          % (ship / max(mean, 1e-12)))
    by = {r["arm"]: r["band_vs_best_source"] for r in rows}
    span = ship - mean
    print("\n  attribution of the manufactured mid-scale band energy:")
    for nm, lab in (("f_admit_only", "hard admission threshold alone"),
                    ("g_exponent_only", "exponent ladder alone, no gate")):
        if nm in by:
            print("    %-32s %6.3fx  = %5.1f%% of the excess over a mean"
                  % (lab, by[nm], 100.0 * (by[nm] - mean) / max(span, 1e-12)))
    print("    %-32s %6.3fx  = %5.1f%% removed by the exponent fix's best "
          "case" % ("flat exponent (fix ceiling)", by["c_flat_exponent"],
                    100.0 * (ship - by["c_flat_exponent"]) / max(span, 1e-12)))
    if ship > 1.0:
        print("  -> the merge is blotchier at mid scale than its own best "
              "frame on a stack with NOTHING to resolve. That excess cannot "
              "be resolved detail; it is manufactured.")
    else:
        print("  -> the merge stays below its best frame even so; mid-scale "
              "manufacture from pure noise is NOT demonstrated here.")

    res = dict(subject=subj, frames=n, rows=rows,
               source=dict(band_min=srcb, fine_max=srcs),
               sqrt_n_expectation=float(expect),
               plain_mean_band_ratio=float(mean),
               shipping_band_ratio=float(ship),
               manufacture_factor=float(ship / max(mean, 1e-12)),
               noise_fit=dict(read2=read2, gain=gph))
    p = os.path.join(OUT, "%s.json" % subj)
    json.dump(res, io.open(p, "w", encoding="utf-8"), indent=1)
    print("\nwrote %s" % p)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except SystemExit:
        raise
    except Exception:
        import traceback
        traceback.print_exc()
        print("\nREFUSED: crashed; no claim about manufacture is measured")
        sys.exit(2)
