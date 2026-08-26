"""BUILD-RESAMP -- does ISO 12233 share BUILD-SHARP's sensitivity confound?

BUILD-SHARP's ringing detector was commissioned on synthetic ideal steps and
recovered 1.00x of a planted overshoot there, but only 0.38x on the fork's
render and 0.08x on ours -- 4.75x more sensitive on one arm than the other,
with no ringing present anywhere.  Their plant was calibrated against an ideal
step while real edges are blurred, so the instrument's sensitivity became a
function of how step-like the render is, which is the quantity in dispute.

The question here is whether a slanted-edge MTF has the same disease.  The
theoretical answer is that it should not: the MTF ratio between two arms is

    MTF_blurred(f) / MTF_base(f)
        = [ O(f) . P(f) . G(f) ] / [ O(f) . P(f) ]
        = G(f)

so the object's own transfer O and the pipeline's own transfer P cancel
identically, and what survives is the planted Gaussian G alone.  Nothing is
compared against an externally calibrated amplitude.  But "should not" is an
argument, and this project does not accept arguments, so this file MEASURES it:
plant the SAME Gaussian in each render separately and report how much of it
each render gives back.

    recovery = (1 - measured ratio) / (1 - predicted ratio)

which is BUILD-SHARP's statistic exactly.  1.00 means the instrument recovered
all of the planted effect from that render.  If the two renders return
materially different recoveries, ISO 12233 shares the confound and no number
may cross the image boundary without being divided by it first.

Also reports, per render and per edge, the ESF fit residual -- the RMS of the
raw ROI samples about the binned ESF, over the edge contrast -- so that a noisy
or non-monotonic edge reads as a bad edge rather than as a resolution
difference.

Both inputs must be LINEAR.  A global scalar is applied to put the two renders
on a common amplitude scale so the site-finding thresholds behave identically;
it is a pure scalar and cancels in every ratio reported here.

Usage:  python commission_per_render.py <a.tif> <b.tif> [...]
"""

import os
import sys

import numpy as np
import tifffile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import slanted_edge as se  # noqa: E402

FGRID = np.round(np.arange(0.01, 0.201, 0.005), 4)
REPORT = (0.05, 0.10, 0.15, 0.20)
MAXSITES = 400
# A recovery fraction divides by (1 - predicted).  At f=0.05 a sigma=0.5 px
# Gaussian attenuates by only 1.2%, so that denominator is 0.0123 and a 1%
# measurement error becomes an 80% error in the recovery -- the first run of
# this file duly printed recoveries of 0.238x and -0.967x there, a NEGATIVE
# sensitivity, which is arithmetic and not evidence.  Only frequencies where
# the plant actually bites are admissible.
MIN_ATTEN = 0.04


def load_linear(path):
    """Green channel, linear, scaled to a common 0..60000 range."""
    a = tifffile.imread(path)
    if a.ndim == 3:
        a = a[:, :, 1]
    a = a.astype(np.float64)
    hi = float(np.percentile(a, 99.9))
    lo = float(np.percentile(a, 0.1))
    if hi <= lo:
        raise SystemExit(f"{path}: degenerate green channel")
    return (a - lo) * (60000.0 / (hi - lo)), (lo, hi)


def blur(img, sigma):
    """Exact frequency-domain Gaussian: the plant, with a closed form."""
    fy = np.fft.fftfreq(img.shape[0])[:, None]
    fx = np.fft.rfftfreq(img.shape[1])[None, :]
    h = np.exp(-2.0 * np.pi**2 * sigma**2 * (fy**2 + fx**2))
    return np.fft.irfft2(np.fft.rfft2(img) * h, s=img.shape)


def measure(img, sites):
    v, curves, resid = [], [], []
    for s in sites:
        r = se.measure_roi(se.cut(img, s), line=s["line"])
        v.append(r["mtf50"] if r else np.nan)
        curves.append((r["f"], r["m"]) if r else None)
        resid.append(r["esf_resid"] if r else np.nan)
    return np.array(v), curves, np.array(resid)


def curve_ratio(ca, cb):
    acc = []
    for a, b in zip(ca, cb):
        if a is None or b is None:
            continue
        ma = np.interp(FGRID, a[0], a[1])
        mb = np.interp(FGRID, b[0], b[1])
        r = np.full(len(FGRID), np.nan)
        ok = mb > 0.08
        r[ok] = ma[ok] / mb[ok]
        acc.append(r)
    return np.nanmedian(np.array(acc), axis=0)


def one(path):
    g, (lo, hi) = load_linear(path)
    print(f"\n=== {os.path.basename(path)} ===")
    print(f"  raster {g.shape[1]} x {g.shape[0]}, green, linear "
          f"(0.1-99.9 pct {lo:.4g}..{hi:.4g} -> 0..60000)")
    sites = se.dedup(se.find_edges(g))[:MAXSITES]
    base, c0, r0 = measure(g, sites)
    ok = np.isfinite(base)
    print(f"  sites {len(sites)}, usable {int(ok.sum())}")
    print(f"  ESF fit residual / contrast: median {np.nanmedian(r0):.4f}, "
          f"IQR {np.nanpercentile(r0,25):.4f}-{np.nanpercentile(r0,75):.4f}, "
          f"p95 {np.nanpercentile(r0,95):.4f}")
    print(f"  MTF50 median {np.nanmedian(base[ok]):.5f} cyc/px "
          "  (NOT cross-render comparable -- object-limited)")

    rc = curve_ratio(c0, c0)
    nullworst = float(np.nanmax(np.abs(rc - 1.0)))
    print(f"  NULL   same render twice, worst |ratio-1| = {nullworst:.3e}   "
          f"{'PASS' if nullworst < 1e-12 else 'FAIL'}")

    out = {}
    for sigma in (0.5, 1.0):
        gb = blur(g, sigma)
        _, cb, rb = measure(gb, sites)
        rc = curve_ratio(cb, c0)
        pred = np.exp(-2.0 * np.pi**2 * sigma**2 * FGRID**2)
        print(f"  PLANT  Gaussian sigma={sigma} px  "
              f"(residual median {np.nanmedian(rb):.4f})")
        recs = []
        for f0 in REPORT:
            i = int(np.argmin(np.abs(FGRID - f0)))
            if 1.0 - pred[i] < MIN_ATTEN:
                recs.append(np.nan)
                print(f"      f={FGRID[i]:.3f}  measured {rc[i]:.4f}  "
                      f"predicted {pred[i]:.4f}  recovery  ---  "
                      f"(plant attenuates only "
                      f"{100*(1-pred[i]):.1f}%, ill-conditioned)")
                continue
            rec = (1.0 - rc[i]) / (1.0 - pred[i])
            recs.append(rec)
            print(f"      f={FGRID[i]:.3f}  measured {rc[i]:.4f}  "
                  f"predicted {pred[i]:.4f}  recovery {rec:6.3f}x")
        out[sigma] = np.array(recs)
    return out


def main():
    paths = sys.argv[1:]
    res = {p: one(p) for p in paths}
    if len(paths) < 2:
        return
    print("\n\n=== CROSS-RENDER SENSITIVITY (the BUILD-SHARP test) ===")
    print("  recovery of the SAME planted Gaussian, per render.")
    print("  If these differ, the instrument's sensitivity depends on the")
    print("  render and no magnitude may cross the image boundary.\n")
    for sigma in (0.5, 1.0):
        print(f"  sigma={sigma} px")
        hdr = "      " + "".join(f"{f'f={f:.3f}':>12}" for f in REPORT)
        print(hdr)
        for p in paths:
            row = "".join(f"{v:>12.3f}" for v in res[p][sigma])
            print(f"      {row}   {os.path.basename(p)}")
        a = res[paths[0]][sigma]
        b = res[paths[1]][sigma]
        ratio = a / b
        print("      " + "".join(
            f"{v:>12.3f}" if np.isfinite(v) else f"{'---':>12}" for v in ratio) +
              "   RATIO of recoveries")
        worst = float(np.nanmax(np.abs(ratio - 1.0)))
        print(f"      worst |recovery ratio - 1| = {worst:.3f}   "
              f"{'IMMUNE' if worst < 0.10 else 'SHARES THE CONFOUND'}\n")


if __name__ == "__main__":
    main()
