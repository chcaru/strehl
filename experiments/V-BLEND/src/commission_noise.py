"""Commission noisefloor.py. Every case checks MAGNITUDE, not just sign: a null
cannot catch an amplitude error (ORCH's own positive control failed exactly
that way, by predicting a luma figure for a per-channel injection).
"""
import numpy as np, tifffile, tempfile, os, sys
sys.path.insert(0, r"C:\dev\strehl-out\V-BLEND")
from noisefloor import immerkaer, mad_diag, structure_index, tiles, load_green, sigma_std
from scipy.signal import fftconvolve

rng = np.random.default_rng(20260825)
H = W = 512
fails = []

def report(name, got, want, tol, note=""):
    ok = abs(got-want) <= tol*max(abs(want), 1e-9)
    print(f"  {'PASS' if ok else 'FAIL'}  {name:<44} got {got:9.4f} want {want:9.4f} (+/-{tol*100:.0f}%) {note}")
    if not ok: fails.append(name)

def sig(field):
    t = tiles(np.asarray(field, dtype=np.float32))
    s = float(np.median(sigma_std(t))); h = float(np.median(immerkaer(t)))
    return s, h, s/h

print("=== EVIDENCE (printed above every verdict) ===")
print("  case                                        sigma_std   sigma_hf   std/hf")

# 1. amplitude recovery, white noise: both estimators exact, ratio 1
for s_ in (7.8, 50.0, 400.0):
    s, h, r = sig(20000.0 + rng.normal(0, s_, (H, W)))
    print(f"  white noise sigma={s_:7.2f}                    {s:9.3f}  {h:9.3f}  {r:6.3f}")
    report(f"white sigma_std s={s_}", s, s_, 0.05)
    report(f"white sigma_hf  s={s_}", h, s_, 0.05)
    report(f"white ratio     s={s_}", r, 1.0, 0.06)

# 2. gradient insensitivity: a strong ramp must not inflate either estimator
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
s, h, r = sig(8000.0 + 20.0*xx + 12.0*yy + rng.normal(0, 50.0, (H, W)))
print(f"  ramp 20/12 DN/px + noise 50                {s:9.3f}  {h:9.3f}  {r:6.3f}")
report("ramp: sigma_std unbiased", s, 50.0, 0.05)
report("ramp: sigma_hf  unbiased", h, 50.0, 0.05)

# 3. PLANTED SMOOTHING. 3x3 box average of white noise: true per-pixel sigma is
#    90/3 = 30, and the noise is now CORRELATED. sigma_std must recover 30;
#    sigma_hf must under-report; the ratio must rise well above 1.
n = rng.normal(0, 90.0, (H+2, W+2))
box = sum(n[a:a+H, b:b+W] for a in range(3) for b in range(3))/9.0
s, h, r = sig(10000.0 + box)
print(f"  3x3-box smoothed (true sigma 30)           {s:9.3f}  {h:9.3f}  {r:6.3f}")
report("smoothing: sigma_std recovers true size", s, 30.0, 0.10, "<- correlation-independent")
print(f"  {'PASS' if r > 2.5 else 'FAIL'}  smoothing: ratio flags correlation           got {r:.3f} want > 2.5")
if r <= 2.5: fails.append("smoothing ratio")

# 3b. a WIDER smooth must give a LARGER ratio (monotone response, not a one-off)
k = np.exp(-((np.mgrid[-12:13, -12:13]**2).sum(0))/(2*2.5**2)); k /= k.sum()
s2, h2, r2 = sig(10000.0 + fftconvolve(rng.normal(0, 300.0, (H, W)), k, mode="same"))
print(f"  gaussian sigma_s=2.5 px smoothed           {s2:9.3f}  {h2:9.3f}  {r2:6.3f}")
print(f"  {'PASS' if r2 > r else 'FAIL'}  wider smooth gives larger ratio              got {r2:.3f} > {r:.3f}")
if not r2 > r: fails.append("ratio monotone in smoothing width")

# 4. PLANTED N-FRAME AVERAGE. Averaging independent frames leaves the noise
#    WHITE, so sigma falls as 1/sqrt(N) and the ratio must STAY at 1. This is
#    what separates "quiet because averaged" from "quiet because smoothed".
for N in (4, 25, 139):
    acc = np.zeros((H, W))
    for _ in range(N): acc += rng.normal(0, 120.0, (H, W))
    s, h, r = sig(9000.0 + acc/N)
    want = 120.0/np.sqrt(N)
    print(f"  average of N={N:3d} (true sigma {want:6.3f})        {s:9.3f}  {h:9.3f}  {r:6.3f}")
    report(f"n_eff={N}: 1/sqrt(N) recovered", s, want, 0.08)
    report(f"n_eff={N}: ratio stays white", r, 1.0, 0.08, "<- averaging does NOT correlate")

# 5. THE LUMA TRAP. I read GREEN directly, never luma, so a common field across
#    R,G,B must return at FULL amplitude with no 0.750 attenuation.
common = rng.normal(0, 65.0, (H, W))
p = os.path.join(tempfile.gettempdir(), "vblend_commission_rgb.tif")
tifffile.imwrite(p, np.clip(np.stack([12000.0+common, 9000.0+common, 6000.0+common], 2), 0, 65535).astype(np.uint16))
s, h, r = sig(load_green(p))
print(f"  common field across R,G,B via green        {s:9.3f}  {h:9.3f}  {r:6.3f}")
report("luma trap: full amplitude on green", s, 65.0, 0.05, "<- not 0.750x")
os.remove(p)

# 6. structure index separates noise from band-limited structure
pure = np.asarray(rng.normal(0, 60.0, (H, W)), dtype=np.float32)
si_p = float(np.median(structure_index(tiles(pure), sigma_std(tiles(pure)))))
kk = np.exp(-((np.mgrid[-8:9, -8:9]**2).sum(0))/(2*3.0**2)); kk /= kk.sum()
sf = np.asarray(fftconvolve(rng.normal(0, 900.0, (H, W)), kk, mode="same") + rng.normal(0, 60.0, (H, W)), dtype=np.float32)
si_s = float(np.median(structure_index(tiles(sf), sigma_std(tiles(sf)))))
print(f"  structure index: pure noise {si_p:.3f}   structure {si_s:.3f}")
report("structure index ~1 on pure noise", si_p, 1.0, 0.20)
print(f"  {'PASS' if si_s > 3.0 else 'FAIL'}  structure index flags structure              got {si_s:.3f} want > 3.0")
if si_s <= 3.0: fails.append("structure index discrimination")

print()
print("=== VERDICT ===")
print(("COMMISSION FAILED: " + ", ".join(fails)) if fails else "COMMISSION PASSED: all cases")
sys.exit(1 if fails else 0)
