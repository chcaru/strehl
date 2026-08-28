r"""DIRECT signal/noise decomposition at flat sites -- the measurement that
decides the orchestrator's failure mode #2 without a variance budget.

Two renders of the same scene from DISJOINT frame subsets (EVEN / ODD) share
their scene content and NOT their noise. So for band-0 fields x (EVEN) and
y (ODD), per tile, after removing the tile mean:

    cov(x, y)              = sigma_s^2   REAL signal variance surviving the arm
    (var x + var y)/2 - cov = sigma_n^2  noise variance surviving the arm

Render both halves under each ARM and the decomposition is per-arm. Then:
    SIGNAL ratio = sigma_s^2(arm) / sigma_s^2(A-unset)
    NOISE  ratio = sigma_n^2(arm) / sigma_n^2(A-unset)

A pure denoiser  -> SIGNAL ~ 1.00, NOISE < 1.
A blur           -> BOTH fall.
This is the discrimination the orchestrator's detail-site guard cannot make,
because the content at issue is low-contrast fine texture AT THE FLAT SITES,
which the most-textured-tile column never looks at.

FOOLING DIRECTIONS.
 (a) Any residual misregistration between the two halves decorrelates real
     texture and DEPRESSES the signal column. A blurred arm tolerates
     misregistration better, so misregistration biases this test IN FAVOUR of
     blurring arms. A finding that an arm LOSES signal is therefore
     conservative under this bias.
 (b) Anything reproducible for a non-scene reason (fixed-pattern sensor noise,
     hot pixels) lands in the signal column. This measures REPRODUCIBILITY.
 (c) Tile class is frozen on the clean A-unset pair so an arm cannot move the
     goalposts by changing which tiles look flat.
"""
import argparse
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bandmetrics as bm                                           # noqa: E402
import nscale as ns                                                # noqa: E402
import splithalf as sh                                             # noqa: E402

OUT = r"C:\dev\strehl-out\V-BANDFLOOR\nscale"


def decomp(ge, go, sel, y0, x0, ty, tx):
    """Per-tile (signal, noise) band-0 variance over the selected tiles."""
    X = sh.tiles_of(sh.band0(ge), y0, x0, ty, tx)[sel]
    Y = sh.tiles_of(sh.band0(go), y0, x0, ty, tx)[sel]
    X = X - X.mean(1, keepdims=True)
    Y = Y - Y.mean(1, keepdims=True)
    cov = (X * Y).mean(1)
    var = 0.5 * ((X * X).mean(1) + (Y * Y).mean(1))
    return cov, var - cov


def ratio(num, den, seed=7, nboot=4000):
    rng = np.random.default_rng(seed)
    idx = rng.integers(0, len(num), size=(nboot, len(num)))
    r = np.median(num[idx], axis=1) / np.maximum(np.median(den[idx], axis=1), 1e-30)
    m = float(np.median(num) / max(np.median(den), 1e-30))
    return m, float(np.percentile(r, 2.5)), float(np.percentile(r, 97.5))


def report(tag, s, n, s0, n0):
    rs, ns_ = ratio(s, s0), ratio(n, n0)
    print("  %-30s SIGNAL x%.4f [%.4f,%.4f]   NOISE x%.4f [%.4f,%.4f]"
          % (tag, rs[0], rs[1], rs[2], ns_[0], ns_[1], ns_[2]))
    return rs, ns_


def commission(pe, po, pct):
    print("COMMISSIONING: direct signal/noise decomposition, on real pixels")
    ge, cme, cfe = ns.load64(pe)
    go, cmo, cfo = ns.load64(po)
    print("  clip: EVEN %.4f%%  ODD %.4f%%" % (100 * cfe, 100 * cfo))
    flat, tex = sh.masks(ge, go, cme | cmo, pct)
    y0, x0, ty, tx = sh.geom(ge.shape)
    print("  tile class frozen on the clean pair (%d flat / %d detail tiles)"
          % (int(flat.sum()), int(tex.sum())))
    s0, n0 = decomp(ge, go, flat, y0, x0, ty, tx)
    print("  baseline flat-site band-0: signal var %.4f  noise var %.4f  (signal frac %.3f)"
          % (np.median(s0), np.median(n0), np.median(s0) / (np.median(s0) + np.median(n0))))
    rng = np.random.default_rng(23)
    loc = float(np.sqrt(np.median(s0 + n0)))
    print("  plants sized in the FLAT SITES' own band-0 units (rms %.3f DN)\n" % loc)

    rows = []
    s, n = decomp(ge, go, flat, y0, x0, ty, tx)
    rs, rn = report("NULL arm := baseline", s, n, s0, n0)
    rows.append(("null", abs(rs[0] - 1) < 1e-9 and abs(rn[0] - 1) < 1e-9))

    s, n = decomp(ge + rng.normal(0, loc, ge.shape),
                  go + rng.normal(0, loc, go.shape), flat, y0, x0, ty, tx)
    rs, rn = report("DEFECT indep noise +1x", s, n, s0, n0)
    rows.append(("indep noise: NOISE up, SIGNAL flat", rn[1] > 1.0 and 0.9 < rs[0] < 1.1))

    k = bm.smooth
    s, n = decomp(k(ge, 1.0), k(go, 1.0), flat, y0, x0, ty, tx)
    rs, rn = report("DEFECT shared blur r=1.0", s, n, s0, n0)
    rows.append(("blur: SIGNAL down", rs[2] < 1.0))

    gne, gno = ge + rng.normal(0, loc, ge.shape), go + rng.normal(0, loc, go.shape)
    sN, nN = decomp(gne, gno, flat, y0, x0, ty, tx)
    rs, rn = report("IMPROVE ref=noisy, arm=clean", s0, n0, sN, nN)
    rows.append(("denoise: NOISE down, SIGNAL flat", rn[2] < 1.0 and 0.9 < rs[0] < 1.1))

    sh_ = rng.normal(0, loc, ge.shape)
    s, n = decomp(ge + sh_, go + sh_, flat, y0, x0, ty, tx)
    rs, rn = report("CONTROL shared texture +1x", s, n, s0, n0)
    rows.append(("shared texture: SIGNAL up", rs[1] > 1.0))

    ok = sum(1 for _, v in rows if v)
    print("\n  COMMISSIONED %d/%d arms" % (ok, len(rows)))
    for nm, v in rows:
        if not v:
            print("    NOT COMMISSIONED: %s" % nm)
    return 0 if ok == len(rows) else 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--commission", nargs=2)
    ap.add_argument("--subject")
    ap.add_argument("--arms", default="A-unset")
    ap.add_argument("--tile", type=int, default=128)
    ap.add_argument("--pct", type=float, default=25.0)
    a = ap.parse_args()
    bm.TILE = a.tile
    if a.commission:
        return commission(a.commission[0], a.commission[1], a.pct)

    arms = a.arms.split(",")
    pe = os.path.join(OUT, "%s__EVEN__%s.tiff" % (a.subject, arms[0]))
    po = os.path.join(OUT, "%s__ODD__%s.tiff" % (a.subject, arms[0]))
    ge, cme, cfe = ns.load64(pe)
    go, cmo, cfo = ns.load64(po)
    flat, tex = sh.masks(ge, go, cme | cmo, a.pct)
    y0, x0, ty, tx = sh.geom(ge.shape)
    s0, n0 = decomp(ge, go, flat, y0, x0, ty, tx)
    ds0, dn0 = decomp(ge, go, tex, y0, x0, ty, tx)
    print("%s split-half signal/noise, band 0, flattest %g%% (%d tiles), tile=%d"
          % (a.subject, a.pct, int(flat.sum()), a.tile))
    print("  reference arm %s   clip EVEN %.4f%%  ODD %.4f%%" % (arms[0], 100 * cfe, 100 * cfo))
    print("  FLAT   baseline signal var %.4f  noise var %.4f   signal fraction %.3f"
          % (np.median(s0), np.median(n0), np.median(s0) / (np.median(s0) + np.median(n0))))
    print("  DETAIL baseline signal var %.4f  noise var %.4f   signal fraction %.3f\n"
          % (np.median(ds0), np.median(dn0), np.median(ds0) / (np.median(ds0) + np.median(dn0))))
    print("  --- FLAT SITES (what the arm is supposed to clean) ---")
    for arm in arms:
        e = os.path.join(OUT, "%s__EVEN__%s.tiff" % (a.subject, arm))
        o = os.path.join(OUT, "%s__ODD__%s.tiff" % (a.subject, arm))
        if not (os.path.exists(e) and os.path.exists(o)):
            print("  %-30s MISSING" % arm)
            continue
        gx, cx, fx = ns.load64(e)
        gy, cy, fy = ns.load64(o)
        s, n = decomp(gx, gy, flat, y0, x0, ty, tx)
        report("%s (clip %.4f%%)" % (arm, 100 * max(fx, fy)), s, n, s0, n0)
    print("\n  --- DETAIL SITES (the guard) ---")
    for arm in arms:
        e = os.path.join(OUT, "%s__EVEN__%s.tiff" % (a.subject, arm))
        o = os.path.join(OUT, "%s__ODD__%s.tiff" % (a.subject, arm))
        if not (os.path.exists(e) and os.path.exists(o)):
            continue
        gx, _, _ = ns.load64(e)
        gy, _, _ = ns.load64(o)
        s, n = decomp(gx, gy, tex, y0, x0, ty, tx)
        report(arm, s, n, ds0, dn0)
    return 0


if __name__ == "__main__":
    sys.exit(main())
