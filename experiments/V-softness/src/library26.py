"""Run the commissioned tone-invariant instrument on all 26 subjects.

Also calibrates the observed loss into an EQUIVALENT GAUSSIAN SIGMA, by
blurring each subject's OWN run-1 image until its HF fraction falls by the
observed amount. That converts a unitless ratio into pixels of blur.
"""
import json, sys
import numpy as np
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))
from vlib import luma, grad_rms, grad_rms_norm, hf_fraction

try:
    from scipy.ndimage import gaussian_filter as gf
    def blur(y, s): return y if s <= 0 else gf(y, s, mode="nearest")
    BACKEND = "scipy"
except Exception:
    from vlib import gauss as blur
    BACKEND = "numpy"

R1 = Path(r"C:\dev\strehl-out\gallery-history\2026-08-25-tone-fix")
R2 = Path(r"C:\dev\strehl-out\gallery-history\2026-08-25-1327")
SIGMAS = [0.0, 0.15, 0.25, 0.35, 0.5, 0.7, 1.0]

def equiv_sigma(y1, target):
    """sigma whose HF-fraction ratio on run1 equals the observed ratio."""
    base = hf_fraction(y1)
    xs, ys = [], []
    for s in SIGMAS:
        xs.append(s); ys.append(hf_fraction(blur(y1, s)) / base)
    if target >= ys[0]: return 0.0
    if target <= ys[-1]: return float("nan")
    for i in range(len(xs)-1):
        if ys[i] >= target >= ys[i+1]:
            f = (ys[i]-target) / max(ys[i]-ys[i+1], 1e-12)
            return xs[i] + f*(xs[i+1]-xs[i])
    return float("nan")

print(f"blur backend: {BACKEND}")
print(f"new (run2) = {R2.name}   old (run1) = {R1.name}\n")
print(f"{'subject':38s} {'raw':>8s} {'norm':>8s} {'HFfrac':>8s} {'eqSigma':>8s}")
print("-"*76)
rows = []
for p2 in sorted(R2.glob("*.jpg")):
    p1 = R1 / p2.name
    if not p1.exists(): continue
    y2, y1 = luma(p2), luma(p1)
    if y1.shape != y2.shape:
        print(f"{p2.stem:38s}  SHAPE MISMATCH"); continue
    raw = grad_rms(y2)/grad_rms(y1)
    nrm = grad_rms_norm(y2)/grad_rms_norm(y1)
    hf  = hf_fraction(y2)/hf_fraction(y1)
    es  = equiv_sigma(y1, hf)
    rows.append(dict(subject=p2.stem, raw=raw, norm=nrm, hf=hf, eq_sigma=es))
    print(f"{p2.stem[:38]:38s} {raw:8.4f} {nrm:8.4f} {hf:8.4f} {es:8.3f}")
    sys.stdout.flush()

hfs = [r["hf"] for r in rows]
print()
print(f"{len(rows)} subjects. HF-fraction ratio: median {np.median(hfs):.4f}, "
      f"min {min(hfs):.4f}, max {max(hfs):.4f}")
print(f"  HF below 1: {sum(1 for h in hfs if h < 1)}   above 1: {sum(1 for h in hfs if h > 1)}")
print(f"  softer at 2% on HF: {sum(1 for h in hfs if h < 0.98)}")
Path("experiments/V-softness/out").mkdir(parents=True, exist_ok=True)
Path("experiments/V-softness/out/library26.json").write_text(json.dumps(rows, indent=1))
print("wrote experiments/V-softness/out/library26.json")
