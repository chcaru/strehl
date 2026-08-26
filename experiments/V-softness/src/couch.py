import sys
sys.path.insert(0, r"C:\dev\blog\death-of-software\projects\strehl\experiments\V-softness\src")
from vlib import luma, grad_rms, grad_rms_norm, hf_fraction
G = r"C:\dev\strehl-out\gallery-history"
runs = {"run1 tone-fix (5d7a7ba)": "2026-08-25-tone-fix",
        "run2 1327 (859edac)":     "2026-08-25-1327",
        "run3 1554 (vtone-after)": "2026-08-25-1554"}
vals = {}
for k, d in runs.items():
    y = luma(f"{G}\\{d}\\couch-fibers-cpl.jpg")
    vals[k] = (grad_rms(y), grad_rms_norm(y), hf_fraction(y), y.mean(), y.std())
    print(f"{k:<28} gradRMS {vals[k][0]:8.2f}  norm {vals[k][1]:7.4f}  "
          f"hf {vals[k][2]:.5f}  mean {vals[k][3]:6.1f}  sd {vals[k][4]:6.2f}")
print()
a = vals["run1 tone-fix (5d7a7ba)"]; b = vals["run2 1327 (859edac)"]
print("SS12.1 pair, run2 / run1 (couch-fibers-cpl):")
print(f"  raw gradient RMS ratio   {b[0]/a[0]:.4f}   <- BUILD-RENDER SS12.1 reports 0.9604")
print(f"  contrast-normalised      {b[1]/a[1]:.4f}")
print(f"  HF power fraction        {b[2]/a[2]:.4f}")
print(f"  global contrast (sd) x   {b[4]/a[4]:.4f}   mean {b[3]-a[3]:+.1f} DN")
print()
print("  SS12.2 reports 0.9376 for 859edac(gamut on) / 5d7a7ba on PINNED LINEAR builds.")
print(f"  gap SS12.1 - SS12.2 = {b[0]/a[0] - 0.9376:+.4f} on raw;"
      f" {b[2]/a[2] - 0.9376:+.4f} on HF")
