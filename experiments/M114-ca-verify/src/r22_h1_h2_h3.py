"""M114 r22: H1 vs H2 vs H3 on both FITTING stacks plus the held-out control.

gain = (applied / declared) x (declared_slope / native_slope)
         \___ application ___/   \______ fit quality ______/

The two factors are separately measurable, and they discriminate the three
hypotheses without ambiguity:

  H1 coefficient error   -> fit-quality factor ~1.44 on the FITTING stacks
  H2 applicability error -> fit-quality factor ~1.0 on the FITTING stacks and
                            far from 1 elsewhere
  H3 application bug     -> application factor != 1 and SCENE-INDEPENDENT, with
                            the fit-quality factor ~1 on every stack

CONTROLS
  X1  NULL. G vs G must read 0.000 px.
  X2  SIGN+SCALE. Integer roll recovered with correct sign, exactly.
  X3  APPLICATION FACTOR SCENE-INDEPENDENCE. Measured same-channel, so
      correlated content, the X2-exact regime. Physics requires it be equal on
      all three stacks. RED IF the spread exceeds 10%.
"""
import json
import numpy as np
import tifffile
from scipy import ndimage
from pathlib import Path

R17 = Path(r"C:\dev\strehl-out\M114-ca-verify\r17")
R21 = Path(r"C:\dev\strehl-out\M114-ca-verify\r21")
NOMINAL, WIN = 704.5e-6, 96
RINGS = [(0.10, 0.25), (0.25, 0.38), (0.38, 0.50), (0.50, 0.62),
         (0.62, 0.74), (0.74, 0.86), (0.86, 0.98)]
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
    rng = np.random.default_rng(2222)
    samp = [float(np.mean(gmag(G[y:y+WIN, x:x+WIN])))
            for y, x in zip(rng.integers(0, H-WIN, 400), rng.integers(0, W-WIN, 400))]
    thresh = float(np.percentile(samp, 75))
    sl0 = (slice(H//2, H//2+WIN), slice(W//2, W//2+WIN))
    x1 = disp(std(gmag(G[sl0])), std(gmag(G[sl0])), 1.0, 0.0)
    rec = [disp(std(gmag(np.roll(G, k, axis=1)[sl0])), std(gmag(G[sl0])), 1.0, 0.0) for k in (-2, 2)]
    x2 = max(abs(r-k) for r, k in zip(rec, (-2, 2)))
    print("\n=== %-13s (%s)   X1 null %+.4f %s   X2 roll err %.4f %s ==="
          % (scene, role, x1, "PASS" if abs(x1) < 0.02 else "FAIL",
             x2, "PASS" if x2 < 0.10 else "FAIL"), flush=True)
    aps, ros, rms, ns = [], [], [], []
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
        ap = float(np.median([disp(std(gmag(on[sl][:, :, 0])), std(gmag(off[sl][:, :, 0])), ux, uy) for sl, ux, uy, _ in got]))
        ro = float(np.median([disp(std(gmag(off[sl][:, :, 0])), std(gmag(off[sl][:, :, 1])), ux, uy) for sl, ux, uy, _ in got]))
        rm = float(np.median([g[3] for g in got]))
        aps.append(ap); ros.append(ro); rms.append(rm); ns.append(len(got))
        print("  r=%.3f n=%2d  applied %+.3f  declared %+.3f  R_off %+.3f" % (rm, len(got), ap, NOMINAL*rm*RC, ro), flush=True)
    rms_a, aps_a, ros_a, ns_a = map(np.array, (rms, aps, ros, ns))
    declared_slope = NOMINAL * RC
    app_slope = float(np.sum(rms_a*aps_a)/np.sum(rms_a*rms_a))
    native_slope = float(np.sum(rms_a*ros_a)/np.sum(rms_a*rms_a))
    appf = app_slope / declared_slope
    fitf = declared_slope / abs(native_slope)
    print("  application factor %.3f   fit-quality factor %.3f   GAIN %.3f   native slope %+.3f"
          % (appf, fitf, appf*fitf, native_slope))
    OUT[scene] = dict(role=role, app_factor=appf, fit_factor=fitf, gain=appf*fitf,
                      native_slope=native_slope, X1=x1, X2=x2, n_rings=len(rms))

print("\n=================== VERDICT TABLE ===================")
print("%-13s %-9s  applic.  fitqual.   GAIN" % ("stack", "role"))
for s in OUT:
    o = OUT[s]
    print("%-13s %-9s   %.3f     %.3f     %.3f" % (s, o["role"], o["app_factor"], o["fit_factor"], o["gain"]))
af = [OUT[s]["app_factor"] for s in OUT]
ff = [OUT[s]["fit_factor"] for s in OUT]
fitstacks = [s for s in OUT if OUT[s]["role"] == "FITTING"]
x3 = (max(af)/min(af) - 1) <= 0.10
print("\nX3 application factor scene-independent: %.3f-%.3f spread %.1f%% -> %s"
      % (min(af), max(af), 100*(max(af)/min(af)-1), "PASS" if x3 else "FAIL"))
print("fit-quality factor on FITTING stacks: %s"
      % ", ".join("%s %.3f" % (s, OUT[s]["fit_factor"]) for s in fitstacks))
h1 = all(1.35 <= OUT[s]["fit_factor"] <= 1.55 for s in fitstacks)
h2 = all(abs(OUT[s]["fit_factor"] - 1) < 0.10 for s in fitstacks) and any(abs(OUT[s]["fit_factor"]-1) > 0.25 for s in OUT if OUT[s]["role"] != "FITTING")
h3 = x3 and abs(np.mean(af) - 1) > 0.05 and all(abs(f - 1) < 0.15 for f in ff)
print("\nH1 coefficient error   : %s" % ("CONFIRMED" if h1 else "REFUTED"))
print("H2 applicability error : %s" % ("CONFIRMED" if h2 else "REFUTED"))
print("H3 application bug     : %s" % ("CONFIRMED" if h3 else "REFUTED"))
(R21 / "r22.json").write_text(json.dumps(OUT, indent=1, default=float), encoding="utf-8")
