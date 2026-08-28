r"""TONE-NEUTRALISED re-measurement.

WHY. The two arms do not share a tone curve. strehl places black and white from
the MERGED image, so changing the merge changes the placement:

    leaf-2-cpl      A black 0.01497 white 0.10723   B black 0.01513 white 0.10718
    wrapped-text-1  A black 0.00444 white 0.20632   B black 0.00457 white 0.20630
    coffee-bubbles  A black 0.01181 white 1.18635   B black 0.01191 white 1.18634
    119MSDCF        A black 0.00851 white 0.34611   B black 0.00843 white 0.34597

A black-point shift is an OFFSET followed by a gamma, and an offset does NOT
cancel in `band RMS / tile mean`. It lifts or drops every band by roughly the
same fraction, on flat and textured tiles alike -- which is exactly the shape of
the leaf-2-cpl and wrapped-text-1 tables. Any band number read without this
control is partly a measurement of the tone stage.

METHOD. Estimate the POINTWISE transfer B <- A as the conditional median of B
given A's value, over 8 million sampled pixels, in 512 level bins; smooth it;
invert it; apply to B. Structure is zero-mean conditional on level, tone is not,
so the curve captures tone and leaves structure. Then re-run the SAME
commissioned measure_pair.

COMMISSIONED HERE, BOTH DIRECTIONS:
  * identical pair            -> correction must be ~0 and the columns must not move
  * pure planted tone shift   -> correction must remove it (columns return to ~0)
  * planted STRUCTURE change  -> correction must NOT remove it
The third arm is the one that matters: a corrector that removes everything is
useless, and this is the arm that can catch it.
"""
import argparse
import os
import sys

import numpy as np
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bandmetrics as bm                                           # noqa: E402

NBIN = 512


def transfer(gA, gB, nsample=8_000_000, seed=13):
    """Conditional median of B given A, on a common level grid."""
    rng = np.random.default_rng(seed)
    n = gA.size
    idx = rng.choice(n, size=min(nsample, n), replace=False)
    a = gA.ravel()[idx]
    b = gB.ravel()[idx]
    lo, hi = float(np.percentile(a, 0.05)), float(np.percentile(a, 99.95))
    edges = np.linspace(lo, hi, NBIN + 1)
    which = np.clip(np.digitize(a, edges) - 1, 0, NBIN - 1)
    order = np.argsort(which, kind="stable")
    which_s, b_s = which[order], b[order]
    bounds = np.searchsorted(which_s, np.arange(NBIN + 1))
    ctr = 0.5 * (edges[:-1] + edges[1:])
    med = np.full(NBIN, np.nan)
    for k in range(NBIN):
        s, e = bounds[k], bounds[k + 1]
        if e - s >= 200:
            med[k] = np.median(b_s[s:e])
    ok = np.isfinite(med)
    if ok.sum() < 16:
        raise SystemExit("transfer: too few populated bins")
    x, y = ctr[ok], med[ok]
    y = ndimage.uniform_filter1d(y, 9, mode="nearest")
    return x, y


def apply_inverse(gB, x, y):
    """Map B's values back through the fitted curve: B' = y^-1(B)."""
    o = np.argsort(y)
    return np.interp(gB, y[o], x[o]).astype(np.float32)


def describe(x, y):
    d = y - x
    return (float(np.median(np.abs(d))), float(np.max(np.abs(d))),
            float(np.median(np.abs(d)) / max(np.median(x), 1e-9)))


def run(gA, gB, cm, tag, quiet=False):
    x, y = transfer(gA, gB)
    med, mx, rel = describe(x, y)
    if not quiet:
        print("  tone transfer B<-A: median |B-A| at fixed level %.1f DN, max "
              "%.1f DN (%.4f%% of the median level)" % (med, mx, 100 * rel))
    gBc = apply_inverse(gB, x, y)
    return bm.measure_pair(gA, gBc, cm, tag=tag, quiet=quiet), (med, mx, rel)


def commission(path):
    print("COMMISSIONING the tone-neutraliser on real pixels: %s" % path)
    g, cm, clipf = bm.load(path)
    print("  whole-image clip fraction %.4f%%" % (100 * clipf))
    rows = []

    def arm(name, gb, need):
        r, (med, mx, rel) = run(g, gb, cm, name)
        cols = " ".join("%s %+7.3f%%" % (k, r[k]["pct"])
                        for k in ("BLOTCH", "LFC", "SHARP", "GRAIN"))
        ok = need(r)
        print("  %-52s %s\n      %s" % (name, "PASS" if ok else "FAIL", cols))
        rows.append((name, ok))

    arm("NULL      identical image -> all columns ~0",
        g.copy(), lambda r: all(abs(r[k]["pct"]) < 0.05
                                for k in ("BLOTCH", "LFC", "SHARP", "GRAIN")))
    # A pure tone move: black point raised by 0.15% of the level range, then
    # the same gamma-ish compression the pipeline applies.
    rng = float(np.percentile(g, 99.9)) - float(np.percentile(g, 0.1))
    tone = np.clip((g - 0.0015 * rng), 0, None)
    tone = (tone * (float(np.mean(g)) / max(float(np.mean(tone)), 1e-9))).astype(np.float32)
    arm("TONE      black+0.15%% of range, re-gained -> must be REMOVED",
        tone, lambda r: all(abs(r[k]["pct"]) < 0.10
                            for k in ("BLOTCH", "LFC", "SHARP", "GRAIN")))
    arm("STRUCTURE coarse bands cut 30%% -> must SURVIVE the corrector",
        bm.attenuate(g, bm.COARSE, 0.3),
        lambda r: r["LFC"]["pct"] < -10.0 and r["LFC"]["hi"] < -10.0)
    arm("STRUCTURE blur sigma 0.8 -> must SURVIVE the corrector",
        ndimage.gaussian_filter(g, 0.8),
        lambda r: r["SHARP"]["pct"] < -5.0 and r["SHARP"]["hi"] < -5.0)
    bad = [r for r in rows if not r[1]]
    print("\n  COMMISSIONED %d/%d arms" % (len(rows) - len(bad), len(rows)))
    for n, _ in bad:
        print("    NOT COMMISSIONED: %s" % n)
    return 1 if bad else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--commission", metavar="TIFF")
    ap.add_argument("--a")
    ap.add_argument("--b")
    ap.add_argument("--tag", default="")
    args = ap.parse_args()
    if args.commission:
        return commission(args.commission)
    gA, cmA, clipA = bm.load(args.a)
    gB, cmB, clipB = bm.load(args.b)
    print("%s  TONE-NEUTRALISED\n  A clip %.4f%%   B clip %.4f%%"
          % (args.tag, 100 * clipA, 100 * clipB))
    r, _ = run(gA, gB, cmA | cmB, args.tag)
    return 0


if __name__ == "__main__":
    sys.exit(main())
