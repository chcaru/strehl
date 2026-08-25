"""M114 r20: the decisive number -- does the GAIN transfer between scenes?

r19 established the two ingredients cleanly:
  * SAME-CHANNEL applied/declared agrees between scenes to 1.4% (1.183 vs
    1.166), so the delivered correction is scene-independent, as physics demands.
  * Native CA through-origin slope differs 1.293x between scenes (-2.780 vs
    -3.595 px/unit-r) on the SAME lens at the SAME aperture with the SAME
    teleconverter.

gain = applied / needed. The numerator is scene-independent and the denominator
is not, so the gain CANNOT be scene-independent. This quantifies it with
bootstrap CIs and a direct between-scene test.

Two forms of `needed` are reported because they differ in what they assume:
  RAW        needed = -R_off measured in that ring. Inherits the constant
             channel offset r19 part C measured (0.206 and 0.350 px), which does
             NOT cancel in a ratio and inflates low-radius rings.
  CORRECTED  needed = slope0 * r from the through-origin fit, which is the
             physical model of a radial scale and removes the constant offset.

CONTROLS
  W1  NULL. G vs G must read 0.000 px.
  W2  SIGN+SCALE. Integer roll must be recovered with correct sign, exactly.
  W3  SCENE-CONSISTENCY OF THE INSTRUMENT. applied/declared must agree between
      scenes. This is the bar that proves a between-scene DIFFERENCE in gain is
      about the scenes and not about the estimator. RED IF they disagree >10%.
"""
import json
import numpy as np
import tifffile
from scipy import ndimage
from pathlib import Path

R17 = Path(r"C:\dev\strehl-out\M114-ca-verify\r17")
NOMINAL, WIN = 704.5e-6, 96
RINGS = [(0.10, 0.25), (0.25, 0.38), (0.38, 0.50), (0.50, 0.62),
         (0.62, 0.74), (0.74, 0.86), (0.86, 0.98)]

def gmag(a):
    return ndimage.gaussian_gradient_magnitude(a, 1.0)

def std(a):
    s = a.std()
    return (a - a.mean()) / s if s > 1e-9 else a * 0.0

def _ssd(a, b, ux, uy, ds, order):
    yy, xx = np.mgrid[0:a.shape[0], 0:a.shape[1]].astype(np.float64)
    best, bd = None, 0.0
    for d in ds:
        w = ndimage.map_coordinates(b, [yy + d * uy, xx + d * ux], order=order, mode="nearest")
        s = float(np.mean((a - w) ** 2))
        if best is None or s < best:
            best, bd = s, float(d)
    return bd

def disp(a, b, ux, uy):
    c = _ssd(a, b, ux, uy, np.arange(-6.0, 6.01, 0.5), 1)
    return -_ssd(a, b, ux, uy, np.arange(c - 0.5, c + 0.501, 0.05), 3)

OUT = {}
for scene in ("bee-3-cpl", "119MSDCF"):
    off = tifffile.imread(str(R17 / (scene + "-off.tif"))).astype(np.float64)
    on = tifffile.imread(str(R17 / (scene + "-on.tif"))).astype(np.float64)
    H, W, _ = off.shape
    cx, cy, RC = W / 2.0, H / 2.0, np.hypot(W / 2.0, H / 2.0)
    G = off[:, :, 1]
    rng = np.random.default_rng(2020)
    samp = [float(np.mean(gmag(G[y:y+WIN, x:x+WIN])))
            for y, x in zip(rng.integers(0, H-WIN, 400), rng.integers(0, W-WIN, 400))]
    thresh = float(np.percentile(samp, 75))
    sl0 = (slice(H//2, H//2+WIN), slice(W//2, W//2+WIN))
    w1 = disp(std(gmag(G[sl0])), std(gmag(G[sl0])), 1.0, 0.0)
    rec = [disp(std(gmag(np.roll(G, k, axis=1)[sl0])), std(gmag(G[sl0])), 1.0, 0.0) for k in (-2, 2)]
    w2 = max(abs(r-k) for r, k in zip(rec, (-2, 2)))
    print("\n=== %s ===  W1 null %+.4f (%s)   W2 roll err %.4f (%s)"
          % (scene, w1, "PASS" if abs(w1) < 0.02 else "FAIL", w2, "PASS" if w2 < 0.10 else "FAIL"), flush=True)

    rows = []
    for rlo, rhi in RINGS:
        got, tries = [], 0
        while len(got) < 40 and tries < 40000:
            tries += 1
            y = int(rng.integers(8, H-WIN-8)); x = int(rng.integers(8, W-WIN-8))
            my, mx = y+WIN/2-cy, x+WIN/2-cx
            rr = np.hypot(mx, my)
            if not (rlo <= rr/RC < rhi) or rr < 1e-6:
                continue
            sl = (slice(y, y+WIN), slice(x, x+WIN))
            if float(np.mean(gmag(G[sl]))) < thresh:
                continue
            got.append((sl, mx/rr, my/rr, rr/RC))
        if len(got) < 8:
            continue
        ap = np.array([disp(std(gmag(on[sl][:, :, 0])), std(gmag(off[sl][:, :, 0])), ux, uy) for sl, ux, uy, _ in got])
        ro = np.array([disp(std(gmag(off[sl][:, :, 0])), std(gmag(off[sl][:, :, 1])), ux, uy) for sl, ux, uy, _ in got])
        rm = float(np.median([g[3] for g in got]))
        rows.append(dict(r=rm, n=len(got), ap=ap.tolist(), ro=ro.tolist(),
                         decl=NOMINAL*rm*RC))
    rmv = np.array([r["r"] for r in rows]); rov = np.array([np.median(r["ro"]) for r in rows])
    slope0 = float(np.sum(rmv*rov)/np.sum(rmv*rmv))
    print(" r      n   applied  needed_raw  gain_raw          needed_fit  gain_fit")
    for r in rows:
        a_, o_ = np.median(r["ap"]), np.median(r["ro"])
        nf = -slope0*r["r"]
        gr, gf = a_/(-o_), a_/nf
        boot = [np.median(rng.choice(r["ap"], len(r["ap"])))/nf for _ in range(600)]
        lo, hi = np.percentile(boot, [2.5, 97.5])
        r.update(gain_raw=float(gr), gain_fit=float(gf), ci=[float(lo), float(hi)])
        print(" %.3f  %2d   %+.3f    %+.3f     %6.3f            %+.3f    %6.3f [%.2f,%.2f]"
              % (r["r"], r["n"], a_, -o_, gr, nf, gf, lo, hi))
    wn = np.array([r["n"] for r in rows], float)
    gf = np.array([r["gain_fit"] for r in rows])
    gfm = float(np.sum(gf*wn)/wn.sum())
    slope_g = float(np.polyfit(rmv, gf, 1, w=wn)[0])
    ratio = float(np.mean([np.median(r["ap"])/r["decl"] for r in rows]))
    print("  WEIGHTED gain_fit %.3f   radial slope %+.4f   applied/declared %.3f   native slope %+.3f"
          % (gfm, slope_g, ratio, slope0))
    OUT[scene] = dict(gain=gfm, slope_g=slope_g, applied_declared=ratio, native_slope=slope0,
                      rows=[{k: v for k, v in r.items() if k not in ("ap", "ro")} for r in rows],
                      W1=w1, W2=w2)

a, b = OUT["bee-3-cpl"], OUT["119MSDCF"]
w3 = abs(b["applied_declared"]/a["applied_declared"] - 1) <= 0.10
print("\n=== W3 INSTRUMENT CONSISTENCY ===")
print("applied/declared  bee %.3f   119 %.3f   diff %+.1f%%  -> %s"
      % (a["applied_declared"], b["applied_declared"],
         100*(b["applied_declared"]/a["applied_declared"]-1), "PASS" if w3 else "FAIL"))
print("\n=== DOES THE GAIN TRANSFER? ===")
print("native CA slope   bee %+.3f   119 %+.3f   ratio %.3f" % (a["native_slope"], b["native_slope"], b["native_slope"]/a["native_slope"]))
print("GAIN              bee %.3f    119 %.3f    difference %+.1f%%"
      % (a["gain"], b["gain"], 100*(b["gain"]/a["gain"]-1)))
print("radial slope of gain   bee %+.4f   119 %+.4f" % (a["slope_g"], b["slope_g"]))
print("\nORCH predicted scene 2 in [1.40,1.50] and flat -> %s"
      % ("CONFIRMED" if 1.40 <= b["gain"] <= 1.50 else "REFUTED (gain %.3f)" % b["gain"]))
(R17 / "r20.json").write_text(json.dumps(OUT, indent=1, default=float), encoding="utf-8")
