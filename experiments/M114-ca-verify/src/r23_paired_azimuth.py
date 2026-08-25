"""M114 r23: remove the constant channel offset EXACTLY by azimuthal pairing.

r22 could not adjudicate H1 vs H2 because the native-CA measurement is
contaminated by a constant cross-channel offset that differs per stack (0.206,
0.350 and ~0.83 px). That offset is not lateral CA -- it is the profile's
recorded-but-unapplied `translation` term, of the order CFA co-siting predicts.
It does not cancel in any ratio, and fitting with or without an intercept flips
the direction of the tweezers-vs-bee difference, so the fit form was deciding
the answer.

THE EXACT REMOVAL. A window at position p with outward radial unit u reads
    c(r) + t.u
Its point-mirror through the optical centre, at -p, has outward radial unit -u
and reads
    c(r) - t.u
so the MEAN of the pair is c(r) with the translation gone by construction, and
the HALF-DIFFERENCE is t.u, which recovers the translation as a free by-product.
No fit form, no intercept, no assumption about the offset's size.

CONTROLS
  Y1  NULL. G vs G reads 0.000 px.
  Y2  SIGN+SCALE. Integer roll recovered exactly, correct sign.
  Y3  TRANSLATION RECOVERY. The half-difference must yield a CONSISTENT vector
      across azimuths within a stack -- that is what makes it a translation
      rather than noise. Reported as the spread of the recovered |t|.
  Y4  THE ANSWER. Paired native slope through the origin, now legitimate.
"""
import json
import numpy as np
import tifffile
from scipy import ndimage
from pathlib import Path

R17 = Path(r"C:\dev\strehl-out\M114-ca-verify\r17")
R21 = Path(r"C:\dev\strehl-out\M114-ca-verify\r21")
NOMINAL, WIN = 704.5e-6, 96
RINGS = [(0.15, 0.30), (0.30, 0.45), (0.45, 0.60), (0.60, 0.75), (0.75, 0.90)]
STACKS = [("tweezers-cpl", R21, "FITTING"), ("bee-3-cpl", R17, "FITTING"),
          ("119MSDCF", R17, "held out")]

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
for scene, base, role in STACKS:
    off = tifffile.imread(str(base / (scene + "-off.tif"))).astype(np.float64)
    on = tifffile.imread(str(base / (scene + "-on.tif"))).astype(np.float64)
    H, W, _ = off.shape
    cx, cy, RC = W / 2.0, H / 2.0, np.hypot(W / 2.0, H / 2.0)
    G = off[:, :, 1]
    rng = np.random.default_rng(2323)
    samp = [float(np.mean(gmag(G[y:y+WIN, x:x+WIN])))
            for y, x in zip(rng.integers(0, H-WIN, 500), rng.integers(0, W-WIN, 500))]
    thresh = float(np.percentile(samp, 60))
    sl0 = (slice(H//2, H//2+WIN), slice(W//2, W//2+WIN))
    y1 = disp(std(gmag(G[sl0])), std(gmag(G[sl0])), 1.0, 0.0)
    rec = [disp(std(gmag(np.roll(G, k, axis=1)[sl0])), std(gmag(G[sl0])), 1.0, 0.0) for k in (-2, 2)]
    y2 = max(abs(r-k) for r, k in zip(rec, (-2, 2)))
    print("\n=== %-13s (%-8s)  Y1 %+.4f %s   Y2 %.4f %s ==="
          % (scene, role, y1, "PASS" if abs(y1) < 0.02 else "FAIL",
             y2, "PASS" if y2 < 0.10 else "FAIL"), flush=True)

    rms, cas, apps, tproj, ns = [], [], [], [], []
    for rlo, rhi in RINGS:
        pairs, tries = [], 0
        while len(pairs) < 26 and tries < 60000:
            tries += 1
            y = int(rng.integers(8, H-WIN-8)); x = int(rng.integers(8, W-WIN-8))
            my, mx = y+WIN/2-cy, x+WIN/2-cx
            rr = np.hypot(mx, my)
            if not (rlo <= rr/RC < rhi) or rr < 1e-6:
                continue
            x2_ = int(round(2*cx - x - WIN)); y2_ = int(round(2*cy - y - WIN))
            if not (8 <= x2_ < W-WIN-8 and 8 <= y2_ < H-WIN-8):
                continue
            sa = (slice(y, y+WIN), slice(x, x+WIN))
            sb = (slice(y2_, y2_+WIN), slice(x2_, x2_+WIN))
            if float(np.mean(gmag(G[sa]))) < thresh or float(np.mean(gmag(G[sb]))) < thresh:
                continue
            pairs.append((sa, sb, mx/rr, my/rr, rr/RC))
        if len(pairs) < 8:
            print("  r %.2f-%.2f  only %d pairs, skipped" % (rlo, rhi, len(pairs)))
            continue
        ca, tp, ap = [], [], []
        for sa, sb, ux, uy, _ in pairs:
            da = disp(std(gmag(off[sa][:, :, 0])), std(gmag(off[sa][:, :, 1])), ux, uy)
            db = disp(std(gmag(off[sb][:, :, 0])), std(gmag(off[sb][:, :, 1])), -ux, -uy)
            ca.append(0.5*(da+db)); tp.append(0.5*(da-db))
            ap.append(disp(std(gmag(on[sa][:, :, 0])), std(gmag(off[sa][:, :, 0])), ux, uy))
            ap.append(disp(std(gmag(on[sb][:, :, 0])), std(gmag(off[sb][:, :, 0])), -ux, -uy))
        rm = float(np.median([p[4] for p in pairs]))
        rms.append(rm); cas.append(float(np.median(ca))); apps.append(float(np.median(ap)))
        tproj.append(float(np.median(np.abs(tp)))); ns.append(len(pairs))
        print("  r=%.3f pairs=%2d  CA(paired) %+.3f  applied %+.3f  |t.u| %.3f"
              % (rm, len(pairs), cas[-1], apps[-1], tproj[-1]), flush=True)

    rv, cv, av = map(np.array, (rms, cas, apps))
    decl_slope = NOMINAL * RC
    native = float(np.sum(rv*cv)/np.sum(rv*rv))
    appsl = float(np.sum(rv*av)/np.sum(rv*rv))
    pred = native*rv
    r2 = 1 - np.sum((cv-pred)**2)/np.sum((cv-cv.mean())**2)
    appf, fitf = appsl/decl_slope, decl_slope/abs(native)
    print("  native(paired) %+.3f px/unit-r  R2(through origin) %.4f   |t.u| median %.3f"
          % (native, r2, float(np.median(tproj))))
    print("  application %.3f   fit-quality %.3f   GAIN %.3f" % (appf, fitf, appf*fitf))
    OUT[scene] = dict(role=role, native=native, r2=r2, app_factor=appf, fit_factor=fitf,
                      gain=appf*fitf, t_proj=float(np.median(tproj)), Y1=y1, Y2=y2)

print("\n============== PAIRED VERDICT TABLE ==============")
print("%-13s %-9s  native   R2      applic.  fitqual.  GAIN" % ("stack", "role"))
for s in OUT:
    o = OUT[s]
    print("%-13s %-9s  %+.3f  %.4f   %.3f    %.3f    %.3f"
          % (s, o["role"], o["native"], o["r2"], o["app_factor"], o["fit_factor"], o["gain"]))
af = [OUT[s]["app_factor"] for s in OUT]
fitst = [s for s in OUT if OUT[s]["role"] == "FITTING"]
ffit = [OUT[s]["fit_factor"] for s in fitst]
print("\nY3 recovered |t.u| per stack: %s"
      % ", ".join("%s %.3f" % (s, OUT[s]["t_proj"]) for s in OUT))
print("application factor spread %.3f-%.3f (%.1f%%)" % (min(af), max(af), 100*(max(af)/min(af)-1)))
print("fit-quality on FITTING stacks: %s" % ", ".join("%s %.3f" % (s, OUT[s]["fit_factor"]) for s in fitst))
h1 = all(1.30 <= f <= 1.60 for f in ffit)
h2 = all(abs(f-1) < 0.15 for f in ffit)
print("\nH1 coefficient error (fit-quality ~1.44 on fitting stacks) : %s" % ("CONFIRMED" if h1 else "REFUTED"))
print("H2 applicability error (fit-quality ~1.0 on fitting stacks) : %s" % ("CONFIRMED" if h2 else "REFUTED"))
(R21 / "r23.json").write_text(json.dumps(OUT, indent=1, default=float), encoding="utf-8")
