"""M120b step 14 -- what is in the cached field, and where is the background?

Two things before the real test:
  (a) Is `bee3-leg-field.npy` the focus field BEFORE the 17x17 regulariser, or after?
      Decided by which argmax reproduces the cached `bee3-leg-argbest.npy`.
      If it is pre-regulariser, then "regulariser OFF, window ON" -- the decisive
      arm of M1 -- is available directly with no recomputation.
  (b) Locate a large background region and a subject region for P4.
"""
import numpy as np
from scipy import ndimage as ndi
from pathlib import Path

C = Path(r"C:\dev\blog\death-of-software\projects\strehl\experiments\M87-occlusion\cache")
REG_R = 8
REG_W = 2 * REG_R + 1


def box_mean(a, r):
    return ndi.uniform_filter(a, size=2 * r + 1, mode="nearest")


field = np.load(C / "bee3-leg-field.npy", mmap_mode="r")
argbest = np.load(C / "bee3-leg-argbest.npy")
luma = np.load(C / "bee3-leg-luma.npy", mmap_mode="r")
K, H, W = field.shape
print(f"field {field.shape} {field.dtype} | argbest {argbest.shape} {argbest.dtype}")

# --- (a) pre- or post-regulariser? Decide on a strip to keep it cheap. -------
ys, ye, xs, xe = 300, 460, 400, 700
pad = REG_R + 2
sub = np.array(field[:, ys - pad:ye + pad, xs - pad:xe + pad], dtype=np.float32)
raw_arg = np.argmax(sub, axis=0)[pad:-pad, pad:-pad]
reg = np.empty_like(sub)
for k in range(K):
    reg[k] = box_mean(sub[k], REG_R)
reg_arg = np.argmax(reg, axis=0)[pad:-pad, pad:-pad]
truth = argbest[ys:ye, xs:xe]
print(f"\nagreement with cached argbest over {truth.size} px:")
print(f"  argmax(field)              = {100*np.mean(raw_arg == truth):6.2f}%   <- field is POST-reg if ~100")
print(f"  argmax(box_mean(field,8))  = {100*np.mean(reg_arg == truth):6.2f}%   <- field is PRE-reg if ~100")

# --- (b) where is the background? -------------------------------------------
# Background = smooth in every frame. Use a coarse local-sd map of a mid frame,
# and require the whole stack's max local sd to be low.
step = 8
mid = np.array(luma[K // 2], dtype=np.float32)
lo = ndi.uniform_filter(mid, 33)
hi = np.sqrt(np.maximum(ndi.uniform_filter(mid * mid, 33) - lo * lo, 0))
print(f"\nmid-frame local sd: p10 {np.percentile(hi,10):.1f}  p50 {np.percentile(hi,50):.1f}  "
      f"p90 {np.percentile(hi,90):.1f}  level p50 {np.median(mid):.0f}")

# tile the plane and score each 192x192 tile by max-over-frames local sd (cheap: 12 frames)
T = 192
probe = np.linspace(0, K - 1, 12).astype(int)
best = []
for ty in range(REG_R + 16, H - T - REG_R - 16, T // 2):
    for tx in range(REG_R + 16, W - T - REG_R - 16, T // 2):
        m = 0.0
        for k in probe:
            t = np.array(luma[k, ty:ty + T, tx:tx + T], dtype=np.float32)
            l = ndi.uniform_filter(t, 33)
            s = np.sqrt(np.maximum(ndi.uniform_filter(t * t, 33) - l * l, 0))
            m = max(m, float(np.percentile(s, 95)))
        best.append((m, ty, tx))
best.sort()
print("\nquietest tiles (max-over-12-frames p95 local sd) -- background candidates:")
for m, ty, tx in best[:5]:
    print(f"   sd {m:8.2f}  at y {ty:4d} x {tx:4d}")
print("busiest tiles -- subject candidates for P4:")
for m, ty, tx in best[-5:]:
    print(f"   sd {m:8.2f}  at y {ty:4d} x {tx:4d}")
