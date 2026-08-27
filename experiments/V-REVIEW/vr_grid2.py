r"""PERIODIC TILE GRID in the master, spectral version.

vr_grid.py's first-difference comb FAILED ITS OWN POSITIVE CONTROL: planting a
p=32 seam grid of 0.008*mean (113 DN) into 112MSDCF's window moved the score
from 1.1480 to 1.1480 (x) -- not at all.  Mechanism: mean|dL| is dominated by
per-pixel noise (sigma ~ hundreds of DN), and adding a small coherent step b to
a zero-mean noise a raises E|a+b| only by b^2/2sigma^2, second order.  That
instrument is dead and is not used for any verdict here.

This one integrates coherently instead.  S(u) = sum_v |F(u,v)|^2 over the 2-D
FFT of the window after removing the low-frequency subject (blk - boxblur 8) and
a Hann taper.  Summing power over v is Parseval on each row: it accumulates the
per-row energy at spatial frequency u whatever the SIGN of each tile's seam, so
a grid whose steps flip sign tile-to-tile still adds.  Noise is flat in u, the
subject falls off smoothly, so a tile grid is a spike at u0 = W/p and harmonics.

  score(p) = S(W/p) / (local median of S), max over the harmonics present.
  DETECT   requires score > the 99.5th percentile of S/localmedian over ALL u in
           the scanned band -- i.e. the peak must beat the rest of its own
           spectrum, which prices in the fact that we scanned many pitches.
  POSITIVE CONTROL --plant a,b,c injects a real p=32 seam grid (a fraction of
           the window mean) and prints the ladder.  The detection floor it
           establishes is quoted in the report; an acquittal from an instrument
           that cannot see a planted grid is worthless.

  python vr_grid2.py SUBJECT [--plant=0.0005,0.002,0.008] [--frame=K] [--nosrc]
"""
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import vr_lib as V                                            # noqa: E402
from orch_blotch import boxblur                               # noqa: E402

UMIN, UMAX = 4, 120          # window/pitch, i.e. pitch 7.5 .. 225 px


def spec(L):
    f = L.astype(np.float64)
    f = f - boxblur(f.astype(np.float32), 8).astype(np.float64)
    h = np.hanning(f.shape[0])[:, None] * np.hanning(f.shape[1])[None, :]
    F = np.fft.rfft2(f * h)
    P = (F.real ** 2 + F.imag ** 2)
    Su = P.sum(axis=0)                # energy at each horizontal frequency
    Sv = P.sum(axis=1)                # (rfft2: axis0 is v, full; axis1 is u, half)
    return Su, Sv


def norm(S):
    """Divide out the smooth subject falloff: median in a +-9 bin neighbourhood."""
    n = len(S)
    out = np.ones(n)
    for i in range(n):
        a, b = max(0, i - 9), min(n, i + 10)
        nb = np.concatenate([S[a:i], S[i + 1:b]])
        out[i] = S[i] / max(float(np.median(nb)), 1e-30)
    return out


def scan(L, W):
    res = {}
    for nm, S in zip("xy", spec(L)):
        R = norm(S)
        band = R[UMIN:UMAX + 1]
        thr = float(np.percentile(band, 99.5))
        best = []
        for p in range(8, 226):
            us = [int(round(W / p * h)) for h in (1, 2, 3)]
            us = [u for u in us if UMIN <= u <= UMAX]
            if not us:
                continue
            best.append((max(R[u] for u in us), p, [round(R[u], 2) for u in us]))
        best.sort(reverse=True)
        res[nm] = (best, thr, R)
    return res


def report(tag, L, W):
    r = scan(L, W)
    for nm in "xy":
        best, thr, R = r[nm]
        s, p, harm = best[0]
        p32 = [b for b in best if b[1] == 32][0]
        print("%-30s %s: best p=%3d score=%.2f harm=%s | p=32 score=%.2f | "
              "99.5%%=%.2f  %s" % (tag, nm, p, s, harm, p32[0], thr,
                                   "DETECT" if s > thr else "none"))
    return r


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    opts = dict(a[2:].split("=", 1) if "=" in a else (a[2:], "1")
                for a in sys.argv[1:] if a.startswith("--"))
    subj = args[0]
    with open(os.path.join(V.OUT, "source_%s.json" % subj)) as fh:
        S = json.load(fh)
    wy, wx = S["master"]["blotch"]["y"], S["master"]["blotch"]["x"]
    W = V.BWIN
    m = V.lum_of(V.read_rgb(V.master_path(subj)))[wy:wy + W, wx:wx + W]
    print("SUBJECT %s  window (%d,%d) %dx%d  mean %.1f DN  sd(noise) %.1f DN"
          % (subj, wy, wx, W, W, m.mean(), np.std(m - boxblur(m, 3))))
    report("MASTER", m, W)

    if "plant" in opts:
        for a in [float(x) for x in opts["plant"].split(",")]:
            mm = float(np.mean(m))
            g = m.astype(np.float32).copy()
            st = np.zeros(W, np.float32)
            st[::32] = 1.0
            g = g + (a * mm) * st[None, :] + (a * mm) * st[:, None]
            report("  PLANT p=32 %.4f (%.0f DN)" % (a, a * mm), g, W)
        return

    if "nosrc" in opts:
        return
    ok = [r for r in S["rows"] if r["state"] == "OK"]
    k = int(opts["frame"]) if "frame" in opts else sorted(ok, key=lambda r: -r["blotch"])[0]["frame"]
    tif = os.path.join(V.OUT, "%s--grid-f%04d.tiff" % (subj, k))
    if not os.path.exists(tif):
        V.render_frame(subj, k, tif)
    import vr_reg2 as R2
    src = V.lum_of(V.read_rgb(tif))
    A, d = R2.register_best(V.lum_of(V.read_rgb(V.master_path(subj))), src,
                            R2.master_cover(subj) / 1.0, wy, wx, W)
    pt = A @ np.array([wx + W / 2.0, wy + W / 2.0, 1.0])
    sx = max(0, min(src.shape[1] - W, int(round(pt[0] - W / 2))))
    sy = max(0, min(src.shape[0] - W, int(round(pt[1] - W / 2))))
    print("  single-frame render f%d, same scene, ITS OWN pixel grid at (%d,%d), ncc %.3f"
          % (k, sy, sx, d["ncc_context"]))
    report("SINGLE-FRAME f%d" % k, src[sy:sy + W, sx:sx + W], W)
    os.remove(tif)


if __name__ == "__main__":
    main()
