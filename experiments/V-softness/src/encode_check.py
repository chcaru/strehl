import numpy as np, tifffile
B = r"C:\dev\strehl-out\BUILD-BLEND"
c = tifffile.imread(B + r"\ca-ctrl-flower-bud-with-background-fern-cpl.tiff")
b = tifffile.imread(B + r"\ca-blend-flower-bud-with-background-fern-cpl.tiff")
assert c.dtype == np.uint16 and b.dtype == np.uint16, (c.dtype, b.dtype)
print("ctrl", c.shape, c.dtype, " blend", b.shape, b.dtype)
cl = c.astype(np.float64).mean(2); bl = b.astype(np.float64).mean(2)
qs = [1, 5, 25, 50, 75, 95, 99, 99.9]
print("pct      ctrl      blend")
for q in qs:
    print("%5.1f  %8.0f  %8.0f" % (q, np.percentile(cl, q), np.percentile(bl, q)))

def srgb_dec(x):
    x = np.clip(x, 0, 1)
    return np.where(x <= 0.04045, x / 12.92, ((x + 0.055) / 1.055) ** 2.4)

# Bin blend (candidate linear) and look at the median ctrl in each bin.
# If ctrl is sRGB-ENCODED of the same scene, ctrl/65535 ~ srgb_encode(k*blend/65535):
# equivalently srgb_decode(ctrl) should be PROPORTIONAL to blend, while raw ctrl is not.
step = 8
cs = cl[::step, ::step].ravel(); bs = bl[::step, ::step].ravel()
lo, hi = np.percentile(bs, [2, 99.5])
edges = np.linspace(lo, hi, 21)
print()
print("blend bin (DN)      med ctrl     ctrl/blend    dec(ctrl)/blend_norm")
rows = []
for i in range(len(edges) - 1):
    m = (bs >= edges[i]) & (bs < edges[i + 1])
    if m.sum() < 200: continue
    mb = float(np.median(bs[m])); mc = float(np.median(cs[m]))
    r_raw = mc / mb
    r_dec = float(srgb_dec(np.array([mc / 65535.0]))[0]) / (mb / 65535.0)
    rows.append((mb, mc, r_raw, r_dec))
    print("%8.0f-%-8.0f %9.0f  %11.4f  %11.4f" % (edges[i], edges[i+1], mc, r_raw, r_dec))
import statistics
raw = [r[2] for r in rows]; dec = [r[3] for r in rows]
def cv(v): return statistics.pstdev(v) / statistics.fmean(v)
print()
print("spread of ratio across the tone range (lower = more nearly a pure gain):")
print("  raw  ctrl/blend        : mean %.4f  CV %.4f  min %.4f  max %.4f" % (statistics.fmean(raw), cv(raw), min(raw), max(raw)))
print("  sRGB-decoded / blend   : mean %.4f  CV %.4f  min %.4f  max %.4f" % (statistics.fmean(dec), cv(dec), min(dec), max(dec)))
