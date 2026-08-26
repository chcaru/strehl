"""THE DISCRIMINATOR: is run 2 blurrier, or is it less noisy?

Blur attenuates high-frequency energy EVERYWHERE, including at edges.
Denoising attenuates it in FLAT regions and leaves edges intact.

So bin pixels by LOCAL VARIANCE measured on run 1 (the same bins for both
arms, so the partition cannot move under the treatment) and compute the
gradient-energy ratio run2/run1 inside each bin.

  loss flat AND detailed  -> blur       -> the regression is real
  loss only in flat bins  -> denoise    -> the "regression" is a noise read
"""
import json, sys
import numpy as np
from pathlib import Path
from scipy.ndimage import uniform_filter
sys.path.insert(0, str(Path(__file__).parent))
from vlib import luma

R1 = Path(r"C:\dev\strehl-out\gallery-history\2026-08-25-tone-fix")
R2 = Path(r"C:\dev\strehl-out\gallery-history\2026-08-25-1327")
NB = 5

def gradmag2(y):
    gx = np.zeros_like(y); gy = np.zeros_like(y)
    gx[:, :-1] = np.diff(y, axis=1)
    gy[:-1, :] = np.diff(y, axis=0)
    return gx*gx + gy*gy

def run(name):
    y1, y2 = luma(R1/f"{name}.jpg"), luma(R2/f"{name}.jpg")
    # partition defined on run 1 ONLY, so treatment cannot move the bins
    m = uniform_filter(y1, 7)
    lv = uniform_filter(y1*y1, 7) - m*m
    qs = np.quantile(lv, np.linspace(0, 1, NB+1))
    qs[0] -= 1; qs[-1] += 1
    g1, g2 = gradmag2(y1), gradmag2(y2)
    out = []
    for i in range(NB):
        sel = (lv >= qs[i]) & (lv < qs[i+1])
        e1 = g1[sel].mean(); e2 = g2[sel].mean()
        out.append(dict(bin=i, lo=float(qs[i]), n=int(sel.sum()),
                        e1=float(e1), e2=float(e2),
                        ratio=float(np.sqrt(e2/e1)) if e1 > 0 else float("nan")))
    return out

SUBJ = ["bee-1-cpl","bee-2-cpl","bee-3-cpl","couch-fibers-cpl",
        "highly-angled-ruler-mm-cpl","dry-erase-marker-head-cpl",
        "flowers-cpl","lavendar-cpl","coffee-bean","wrapped-text-1","foam"]

print("gradient-RMS ratio run2/run1, by LOCAL-VARIANCE bin of run 1")
print("bin 0 = flattest 20% (noise lives here)   bin 4 = most detailed 20%\n")
print(f"{'subject':32s} {'flat0':>8s} {'1':>8s} {'2':>8s} {'3':>8s} {'detail4':>8s}   {'d4-f0':>7s}")
print("-"*88)
allrows = {}
for s in SUBJ:
    r = run(s); allrows[s] = r
    v = [x["ratio"] for x in r]
    print(f"{s[:32]:32s} " + " ".join(f"{x:8.4f}" for x in v) + f"   {v[4]-v[0]:+7.4f}")
    sys.stdout.flush()

f0 = [allrows[s][0]["ratio"] for s in SUBJ]
d4 = [allrows[s][4]["ratio"] for s in SUBJ]
print()
print(f"median flattest-bin ratio : {np.median(f0):.4f}")
print(f"median detailed-bin ratio : {np.median(d4):.4f}")
print()
print("If detailed-bin ratio ~= 1.0 the loss is NOISE, not sharpness.")
print("If detailed-bin ratio tracks the flat bin, it is BLUR.")
Path("experiments/V-softness/out/bins.json").write_text(json.dumps(allrows, indent=1))
