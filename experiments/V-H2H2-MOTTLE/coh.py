"""Is 'incoherent detail' incoherent selection, or unregistered halves?

ORCH's item 2 predicts that a merge over-selecting on noise picks different frames
per pixel in half A than in half B, so detail correlated ACROSS two half-stacks
falls short of total detail, and the shortfall rises with N.

That prediction shares its instrument with a confound this lane has already
measured: two strehl renders differing only in frame set do not land on the same
pixel grid (3-21 px rms, 0.16-1.37% magnification, section 12.4). Two independent
half-stacks ARE two different frame sets. A cross-correlation between two images
displaced by d suppresses a wavelength lambda by roughly exp(-2 pi^2 d^2 / lambda^2),
so at lambda = 4-5 px -- which is 0.20-0.25 cyc/px, the band the 2.017 is quoted in
-- a displacement of a few px destroys coherence completely with no selection
defect required.

ORCH wrote that alignment drift 'would produce coherent error in both halves
rather than incoherent choice'. That is true of a drift shared by both halves. It
is not true of a drift BETWEEN the halves, which is what was measured.

THE TWO HYPOTHESES DISAGREE ON DATA THAT ALREADY EXISTS.

    selection  : the coherence deficit rises with N.
    registration: the coherence deficit tracks the measured displacement field,
                  which is NOT monotone in N -- 6.54, 20.68, 9.90, 10.00 px at
                  n18, n37, n74, n149. n37 is the worst pair and the second
                  shallowest rung.

and they disagree on a second axis:

    selection  : registering the two halves changes nothing, because the frame
                 choice is still incoherent per pixel.
    registration: registering the two halves recovers most of the deficit.

Both are measured here. Neither is fitted.

TOTAL DETAIL IS ALSO REPORTED, ON ONE ARM, because ORCH asked for at least one
statistic that cannot be moved by coherence alone: band energy in a single render
counts detail whether or not the other half agrees about it.
"""
import json
import os
import sys

import numpy as np
import tifffile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bandlib  # noqa: E402
import decomplib  # noqa: E402
import nscene  # noqa: E402

OUT = r"C:\dev\strehl-out\V-H2H2\ladder2\out"
RUNGS = [18, 37, 74, 149]
BANDS = [("5-15", 5, 15), ("20-60", 20, 60), ("40-120", 40, 120)]
SITE, PAD, MARGIN = 384, 64, 600
GRID_Y, GRID_X = 4, 6


def gamma(ca, cb, lo, hi):
    """Correlation of the two arms' band coefficients: the coherent fraction.

    Bounded [-1, 1] by construction, so it cannot be inflated by a gain, and it
    is 1 only if the two arms agree pixel for pixel about where the detail is.
    """
    fa = decomplib.bandpass(ca, lo, hi)
    fb = decomplib.bandpass(cb, lo, hi)
    fa = fa - fa.mean()
    fb = fb - fb.mean()
    den = np.sqrt(float(np.mean(fa * fa)) * float(np.mean(fb * fb)))
    if den <= 0:
        return None
    return float(np.mean(fa * fb)) / den


def total(ca, lo, hi):
    """Band energy in ONE arm. Immune to coherence: no second image is consulted."""
    f = decomplib.bandpass(ca, lo, hi)
    return float(np.sqrt(np.mean((f - f.mean()) ** 2)))


def sites(h, w):
    ys = np.linspace(MARGIN, h - MARGIN - SITE, GRID_Y).astype(int)
    xs = np.linspace(MARGIN, w - MARGIN - SITE, GRID_X).astype(int)
    return [(int(y), int(x)) for y in ys for x in xs]


def measure(ga, gb):
    """Coherence per band, raw and after per-site integer registration."""
    h, w = ga.shape
    raw = {b[0]: [] for b in BANDS}
    reg = {b[0]: [] for b in BANDS}
    tot = {b[0]: [] for b in BANDS}
    offs = []
    for y, x in sites(h, w):
        ca = ga[y:y + SITE, x:x + SITE]
        pad = gb[y - PAD:y + SITE + PAD, x - PAD:x + SITE + PAD]
        cb_raw = pad[PAD:PAD + SITE, PAD:PAD + SITE]
        (dy, dx), _e, edge = nscene.integer_align(ca, pad, PAD)
        if edge:
            continue
        cb_reg = pad[PAD + dy:PAD + dy + SITE, PAD + dx:PAD + dx + SITE]
        offs.append((dy, dx))
        for name, lo, hi in BANDS:
            r = gamma(ca, cb_raw, lo, hi)
            g = gamma(ca, cb_reg, lo, hi)
            if r is not None and g is not None:
                raw[name].append(r)
                reg[name].append(g)
                tot[name].append(total(ca, lo, hi))
    o = np.array(offs, dtype=np.float64)
    field = float(np.sqrt(np.mean((o - o.mean(axis=0)) ** 2))) if len(o) else float("nan")
    return raw, reg, tot, field, len(offs)


def load(name, expo):
    return bandlib.display(tifffile.imread(os.path.join(OUT, name + ".tiff"))[..., 1]
                           .astype(np.float64), expo)


def spearman(x, y):
    """Rank correlation. Four points, so this is a sign-and-order statement,
    not a p-value, and it is reported as one."""
    def rank(v):
        o = sorted(range(len(v)), key=lambda i: v[i])
        r = [0] * len(v)
        for j, i in enumerate(o):
            r[i] = j + 1
        return r
    rx, ry = rank(x), rank(y)
    n = len(x)
    d2 = sum((a - b) ** 2 for a, b in zip(rx, ry))
    return 1.0 - 6.0 * d2 / (n * (n * n - 1))


def main():
    r16 = tifffile.imread(os.path.join(OUT, "n149a.tiff"))
    expo = 0.90 / max(float(np.percentile(r16.astype(np.float64) / 65535.0, 99.9)), 1e-9)
    del r16
    print("display gain %.4f, one reference for every arm\n" % expo)
    print("%-6s %6s  %-8s %8s %8s %8s %10s"
          % ("rung", "field", "band", "gam_raw", "gam_reg", "recover", "total_a"))
    rows = {}
    for n in RUNGS:
        ga, gb = load("n%da" % n, expo), load("n%db" % n, expo)
        raw, reg, tot, field, k = measure(ga, gb)
        del ga, gb
        rows[n] = {"field": field, "sites": k}
        for name, _lo, _hi in BANDS:
            gr = float(np.median(raw[name]))
            gg = float(np.median(reg[name]))
            ta = float(np.median(tot[name]))
            rec = (gg - gr) / max(1.0 - gr, 1e-12)
            rows[n][name] = {"raw": gr, "reg": gg, "recover": rec, "total_a": ta}
            print("%-6d %6.2f  %-8s %8.4f %8.4f %7.1f%% %10.4f"
                  % (n, field, name, gr, gg, 100 * rec, ta))
        print()

    # The two hypotheses disagree here and nowhere else.
    ns = [float(n) for n in RUNGS]
    fields = [rows[n]["field"] for n in RUNGS]
    out = {"rows": {str(n): rows[n] for n in RUNGS}, "expo": expo, "rho": {}}
    print("%-10s %22s %22s" % ("band", "rho(gam_raw, field)", "rho(gam_raw, N)"))
    for name, _lo, _hi in BANDS:
        g = [rows[n][name]["raw"] for n in RUNGS]
        rf, rn = spearman(g, fields), spearman(g, ns)
        out["rho"][name] = {"field": rf, "N": rn}
        print("%-10s %22.3f %22.3f" % (name, rf, rn))
    print("\nregistration-immune statistic (one arm, counts detail whether or not")
    print("the other half agrees about it):")
    for name, _lo, _hi in BANDS:
        t = [rows[n][name]["total_a"] for n in RUNGS]
        out["rho"].setdefault(name, {})["total_N"] = spearman(t, ns)
        print("  total_a %-8s %s   rho vs N %+.3f"
              % (name, " ".join("%.4f" % v for v in t), spearman(t, ns)))
    p = os.path.join(OUT, "coh.json")
    with open(p, "w") as f:
        json.dump(out, f, indent=1)
    print("\nwrote %s" % p)
    return rows


if __name__ == "__main__":
    main()
