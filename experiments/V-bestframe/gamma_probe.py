"""ORCH asked me to state the gamma I got from rawpy rather than assert a default.

Decode the same ARW twice, once with the postprocess parameters this instrument
actually uses and once with gamma=(1,1) (linear), then fit log(nonlinear) against
log(linear) over the mid-tones. The slope is the effective encoding exponent.
"""
import numpy as np, rawpy
from pathlib import Path

f = sorted(Path(r"D:\personal\macro\flowers-cpl").glob("*.ARW"))[0]
kw = dict(output_bps=16, no_auto_bright=True, use_camera_wb=True)  # exactly bestframe.decode
with rawpy.imread(str(f)) as r:
    a = r.postprocess(**kw)
assert a.dtype == np.uint16, a.dtype
with rawpy.imread(str(f)) as r:
    b = r.postprocess(gamma=(1, 1), **kw)
assert b.dtype == np.uint16, b.dtype
print(f"file {f.name}  shape {a.shape}  dtype {a.dtype}")
x = b[::7, ::7].astype(np.float64).ravel() / 65535.0
y = a[::7, ::7].astype(np.float64).ravel() / 65535.0
m = (x > 0.02) & (x < 0.5) & (y > 0.02) & (y < 0.9)
sl, ic = np.polyfit(np.log(x[m]), np.log(y[m]), 1)
print(f"  n={m.sum()} midtone samples; log-log slope = {sl:.4f}  -> effective gamma "
      f"exponent 1/{1/sl:.4f}")
print(f"  i.e. output ~ linear**{sl:.4f}   (BT.709 encode is ~1/2.222 = 0.4500 "
      f"with a linear toe; pure sRGB is ~0.4167 with a toe)")
for q in (0.05, 0.1, 0.2, 0.4, 0.6, 0.8):
    i = np.argmin(np.abs(x - q))
    print(f"    linear {x[i]:.4f} -> encoded {y[i]:.4f}")
print(f"  max DN: nonlinear {a.max()}  linear {b.max()}")
print("  NOTE: this instrument does not rely on the value. Each frame is mapped to")
print("  the merge by an EMPIRICAL monotone transfer fitted from registered blurred")
print("  sample pairs, so any fixed encoding curve is absorbed. The number is")
print("  reported because it was asked for, not because a result depends on it.")
