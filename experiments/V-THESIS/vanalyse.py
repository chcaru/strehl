"""Follow-ups: CIs, band sensitivity, a REALISTIC impulse plant, sigma cross-check."""
import json, pathlib, sys
import numpy as np, tifffile
from scipy.ndimage import median_filter

V = pathlib.Path("experiments/V-THESIS").resolve(); sys.path.insert(0, str(V))
B = pathlib.Path("experiments/BUILD-THESIS").resolve(); sys.path.insert(0, str(B))
from vstat import va_blur_px, sigma_immerkaer      # noqa: E402
from stats import noise_sigma as donoho            # noqa: E402  THEIR estimator

R = pathlib.Path(r"C:\dev\strehl-out\BUILD-THESIS\renders")
OUT = pathlib.Path(r"C:\dev\strehl-out\V-THESIS")
data = json.loads((OUT/"vmeasure.json").read_text(encoding="utf8"))
RNG = np.random.default_rng(31415)

print("="*84)
print("A. PER-SUBJECT MEDIAN WITH A BOOTSTRAP 95% CI (tiles are non-overlapping)")
print("="*84)
print(f"{'subject':<20}{'n':>4}{'median':>9}{'95% CI':>20}{'sign test p':>13}{'null':>8}")
from math import comb
pooled = []
for rec in data:
    v = np.array([t["va_shipped"] for t in rec["tiles"] if t["kept"]])
    pooled.append(v)
    bs = [np.median(RNG.choice(v, v.size, replace=True)) for _ in range(20000)]
    lo, hi = np.percentile(bs, [2.5, 97.5])
    k = int((v > 0).sum()); n = len(v)
    p = sum(comb(n,i) for i in range(0, min(k, n-k)+1))*2/2**n
    print(f"{rec['subject']:<20}{n:>4}{np.median(v):>+9.3f}   [{lo:+.3f},{hi:+.3f}]"
          f"{min(p,1.0):>13.4f}{rec['va_null_median']:>+8.3f}")
allv = np.concatenate(pooled)
bs = [np.median(RNG.choice(allv, allv.size, replace=True)) for _ in range(20000)]
print(f"{'POOLED (109 tiles)':<20}{len(allv):>4}{np.median(allv):>+9.3f}"
      f"   [{np.percentile(bs,2.5):+.3f},{np.percentile(bs,97.5):+.3f}]")

print("\n"+"="*84)
print("B. BAND SENSITIVITY -- does a merge advantage hide at the finest scales?")
print("="*84)
def green(p): return tifffile.imread(str(p))[:,:,1].astype(np.float64)
bands = [(32.0,6.0),(24.0,4.0),(16.0,3.0),(12.0,2.6)]
print(f"{'subject':<20}" + "".join(f"{f'{a:.0f}-{b:.1f}px':>13}" for a,b in bands))
for rec in data:
    gm, ga = green(R/rec["subject"]/"merge.tif"), green(R/rec["subject"]/"argmax.tif")
    T, Ta = rec["Tm"], rec["Ta"]
    ks = [t for t in rec["tiles"] if t["kept"]]
    row = []
    for bp in bands:
        vs = [va_blur_px(gm[t["y"]:t["y"]+T, t["x"]:t["x"]+T],
                         ga[t["ay"]:t["ay"]+Ta, t["ax"]:t["ax"]+Ta], band_periods=bp)
              for t in ks]
        row.append(np.median(vs))
    print(f"{rec['subject']:<20}" + "".join(f"{r:>+13.3f}" for r in row))

print("\n"+"="*84)
print("C. REALISTIC IMPULSE CONTENT, MEASURED, AND THE BIAS IT ACTUALLY CAUSES")
print("="*84)
print(f"{'subject':<20}{'merge %>6sig':>14}{'argmax %>6sig':>15}{'excess':>9}{'VA bias':>10}")
for rec in data:
    gm, ga = green(R/rec["subject"]/"merge.tif"), green(R/rec["subject"]/"argmax.tif")
    T, Ta = rec["Tm"], rec["Ta"]
    t0 = [t for t in rec["tiles"] if t["kept"]][0]
    tm = gm[t0["y"]:t0["y"]+T, t0["x"]:t0["x"]+T]
    ta = ga[t0["ay"]:t0["ay"]+Ta, t0["ax"]:t0["ax"]+Ta]
    def rate(t):
        s = sigma_immerkaer(t); m = median_filter(t, 3, mode="nearest")
        return float((np.abs(t-m) > 6*s).mean()), float(np.abs(t-m)[np.abs(t-m)>6*s].mean() if (np.abs(t-m)>6*s).any() else 0.0), s
    rm, am_m, sm = rate(tm); ra, am_a, sa = rate(ta)
    exc = max(ra-rm, 0.0)
    # plant that excess, at the measured amplitude, on the merge tile
    tn = tm.copy(); fl = tn.ravel()
    n = int(exc*tm.size)
    if n > 0:
        idx = RNG.choice(tm.size, n, replace=False)
        fl[idx] += np.where(RNG.random(n) < 0.5, -am_a, am_a)
    bias = va_blur_px(tm, tn) if n > 0 else 0.0
    print(f"{rec['subject']:<20}{rm*100:>14.4f}{ra*100:>15.4f}{exc*100:>9.4f}{bias:>+10.3f}")

print("\n"+"="*84)
print("D. NOISE SIGMA: my estimator vs BUILD-THESIS's, on the SAME tiles")
print("="*84)
print(f"{'subject':<20}{'Immerkaer a/m':>15}{'Donoho a/m':>13}{'BT reported':>13}")
bt = {r['subject']: r['sigma_ratio_argmax_over_merge']
      for r in json.loads(pathlib.Path(r'C:\dev\strehl-out\BUILD-THESIS\measure-subjects.json').read_text(encoding='utf8'))}
for rec in data:
    gm, ga = green(R/rec["subject"]/"merge.tif"), green(R/rec["subject"]/"argmax.tif")
    T, Ta = rec["Tm"], rec["Ta"]
    im, do = [], []
    for t in [x for x in rec["tiles"] if x["kept"]]:
        tm = gm[t["y"]:t["y"]+T, t["x"]:t["x"]+T]; ta = ga[t["ay"]:t["ay"]+Ta, t["ax"]:t["ax"]+Ta]
        im.append(sigma_immerkaer(ta)/sigma_immerkaer(tm)); do.append(donoho(ta)/donoho(tm))
    print(f"{rec['subject']:<20}{np.median(im):>15.3f}{np.median(do):>13.3f}{bt[rec['subject']]:>13.3f}")
