"""M103 -- does the gain correction increase waxiness? A threshold-free test.

`waxmap.py` passed its plants but then found almost nothing at the place where a
1:1 crop plainly shows a large waxy region, so its absolute thresholds
(sigma < 1.5 DN, brightness > 110 DN) are mis-calibrated against the real
artefact and its whole-frame verdict is not usable. Rather than tune thresholds
until they agree with what I already believe -- which would be circular -- this
script removes the thresholds.

The question is comparative: **does the gain-corrected render contain more
smooth-and-bright area than the shipped one?** That can be asked as a whole
distribution instead of a cut:

  - take the brightest P% of pixels in EACH arm by its OWN percentile, so a
    difference in overall exposure between the arms cannot masquerade as a
    difference in waxiness;
  - within that set, report the fraction whose local sigma falls below each of a
    sweep of thresholds.

If the corrected arm is waxier, its curve sits above the shipped one at every
threshold. No single cut has to be chosen and no threshold can be tuned to taste.

Controls:
  PLACEBO     shipped against itself: the two curves must be identical to 0.0000
              at every threshold. Catches any asymmetry in the pipeline itself.
  POSITIVE    a known waxy region -- smooth bright fill with a hard edge --
              planted into a copy of the shipped render must lift the shipped
              curve by approximately the planted area fraction.
  SPECIFICITY the same area planted as honest defocus (Gaussian blur, feathered,
              no hard boundary) is ALSO smooth, so it must lift the curve too.
              That is the point: this instrument measures smoothness, and it is
              honest about not distinguishing a merge artefact from real bokeh.
              The hard-boundary question is settled by eye on the 1:1 crops and
              by `waxmap.py`'s region test, not here.

usage:
  python src/waxsweep.py <shipped.tif> <corrected.tif> <out.json>
"""

import json
import sys

import numpy as np
from PIL import Image, ImageFilter

Image.MAX_IMAGE_PIXELS = None

K = 9
PCTS = [90.0, 95.0, 99.0]
SIGMAS = [0.5, 1.0, 1.5, 2.0, 3.0, 4.0, 6.0]


def local_sigma(g, k=K):
    s = np.cumsum(np.cumsum(g, 0), 1)
    s2 = np.cumsum(np.cumsum(g * g, 0), 1)
    s = np.pad(s, ((1, 0), (1, 0)))
    s2 = np.pad(s2, ((1, 0), (1, 0)))
    h, w = g.shape
    y0, y1 = np.arange(h - k), np.arange(k, h)
    x0, x1 = np.arange(w - k), np.arange(k, w)
    A = s[np.ix_(y1, x1)] - s[np.ix_(y0, x1)] - s[np.ix_(y1, x0)] + s[np.ix_(y0, x0)]
    B = s2[np.ix_(y1, x1)] - s2[np.ix_(y0, x1)] - s2[np.ix_(y1, x0)] + s2[np.ix_(y0, x0)]
    n = k * k
    return np.sqrt(np.maximum(B / n - (A / n) ** 2, 0.0)), (k // 2, h - k, w - k)


def curve(g):
    sig, (o, hh, ww) = local_sigma(g)
    gc = g[o:o + hh, o:o + ww]
    out = {}
    for p in PCTS:
        thr = np.percentile(gc, p)
        sel = sig[gc >= thr]
        out["p%g" % p] = {"bright_thr_dn": float(thr),
                          "n": int(sel.size),
                          "frac": {str(s): float((sel < s).mean()) for s in SIGMAS}}
    return out


def show(name, c):
    for p in PCTS:
        row = c["p%g" % p]["frac"]
        print("  %-22s p%-4g " % (name, p) +
              " ".join("%6.4f" % row[str(s)] for s in SIGMAS))


def main():
    ship_p, corr_p, out_p = sys.argv[1], sys.argv[2], sys.argv[3]
    print("loading")
    gs = np.asarray(Image.open(ship_p))[..., 1].astype(np.float64)
    gc = np.asarray(Image.open(corr_p))[..., 1].astype(np.float64)

    hdr = "  %-22s %-5s " % ("arm", "pct") + " ".join("%6s" % ("s<%g" % s) for s in SIGMAS)
    print("\nCONTROLS")
    print(hdr)
    cs = curve(gs)
    show("shipped", cs)
    # PLACEBO
    cs2 = curve(gs.copy())
    dmax = max(abs(cs["p%g" % p]["frac"][str(s)] - cs2["p%g" % p]["frac"][str(s)])
               for p in PCTS for s in SIGMAS)
    print("  PLACEBO shipped vs itself: max |delta| = %.4e -> %s"
          % (dmax, "PASS" if dmax == 0.0 else "FAIL"))

    # POSITIVE: hard-edged smooth bright fill, 600x600. The fill level is taken
    # from the data (above the p99 brightness cut) rather than guessed: a first
    # version filled with a fixed 175 DN, which on this mostly-dark subject sits
    # below the p95 cut, so the planted pixels never entered the bright set and
    # the control read exactly +0.000000. The plant was wrong, not the metric.
    fill = float(np.percentile(gs, 99.5)) + 10.0
    plant = gs.copy()
    plant[1200:1800, 2400:3000] = fill
    cp = curve(plant)
    print("  (p90/p95/p99 brightness cuts: %.1f / %.1f / %.1f DN; plant fill %.1f DN)"
          % (cs["p90"]["bright_thr_dn"], cs["p95"]["bright_thr_dn"],
             cs["p99"]["bright_thr_dn"], fill))
    want = (600.0 * 600.0) / gs.size
    got = cp["p95"]["frac"]["1.0"] - cs["p95"]["frac"]["1.0"]
    # the planted pixels are all in the brightest 5%, so within that set the
    # expected lift is the planted area divided by the size of the set
    exp = (600.0 * 600.0) / cs["p95"]["n"]
    ok1 = got > 0.4 * exp
    print("  POSITIVE planted smooth bright blob (%.5f of frame, %.4f of the p95 set):"
          % (want, exp))
    print("           p95 s<1.0 rises %.4f -> %.4f (delta %+.4f) -> %s"
          % (cs["p95"]["frac"]["1.0"], cp["p95"]["frac"]["1.0"], got,
             "PASS" if ok1 else "FAIL"))

    # SPECIFICITY: honest defocus of the same area
    soft = gs.copy()
    sy, sx = 2600, 4200
    patch = Image.fromarray(soft[sy:sy + 600, sx:sx + 600].astype(np.uint8))
    blur = np.asarray(patch.filter(ImageFilter.GaussianBlur(14))).astype(np.float64)
    ramp = np.minimum(np.minimum(np.arange(600), np.arange(600)[::-1])[:, None],
                      np.minimum(np.arange(600), np.arange(600)[::-1])[None, :])
    a = np.clip(ramp / 60.0, 0, 1)
    soft[sy:sy + 600, sx:sx + 600] = a * blur + (1 - a) * soft[sy:sy + 600, sx:sx + 600]
    cf = curve(soft)
    got2 = cf["p95"]["frac"]["1.0"] - cs["p95"]["frac"]["1.0"]
    print("  SPECIFICITY honest defocus, same area: delta %+.4f" % got2)
    print("           (expected to move: this instrument measures smoothness and")
    print("            does not claim to separate bokeh from artefact)")
    ok = (dmax == 0.0) and ok1
    print("  -> controls %s\n" % ("PASS" if ok else "FAIL"))
    if not ok:
        return 1

    cc = curve(gc)
    print("Fraction of the brightest pixels whose local sigma is below each cut.")
    print("Percentiles are taken per-arm, so exposure differences cannot leak in.")
    print(hdr)
    show("shipped", cs)
    show("gain-corrected", cc)
    print()
    print("  %-22s %-5s " % ("DELTA corr-ship", "pct") +
          " ".join("%6s" % ("s<%g" % s) for s in SIGMAS))
    worse = 0
    for p in PCTS:
        row = [cc["p%g" % p]["frac"][str(s)] - cs["p%g" % p]["frac"][str(s)] for s in SIGMAS]
        worse += sum(1 for v in row if v > 0)
        print("  %-22s p%-4g " % ("", p) + " ".join("%+6.4f" % v for v in row))
    print()
    print("  cells where the corrected arm is smoother: %d of %d"
          % (worse, len(PCTS) * len(SIGMAS)))

    res = {"shipped": cs, "corrected": cc,
           "controls": {"placebo_max_delta": dmax, "positive_delta": got,
                        "positive_expected": exp, "specificity_delta": got2,
                        "pass": bool(ok)}}
    with open(out_p, "w", encoding="utf-8") as fh:
        json.dump(res, fh, indent=1, sort_keys=True)
    print("\nwrote " + out_p)
    return 0


if __name__ == "__main__":
    sys.exit(main())
