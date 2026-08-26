import numpy as np, tifffile
o = r"C:\dev\strehl-out\BUILD-ELECT\accept"
ref = tifffile.imread(o + r"\fb-mean.tiff").astype(np.float32)
for a in ("fb-max", "fb-hp"):
    x = tifffile.imread(o + rf"\{a}.tiff").astype(np.float32)
    d = np.abs(x - ref)
    frac = float((d > 0).mean() * 100)
    print(f"{a:>8} vs fb-mean: {frac:6.2f}% of samples differ, "
          f"max |delta| {d.max():8.0f} DN, mean |delta| {d.mean():7.1f} DN, "
          f"p99.9 {np.percentile(d, 99.9):7.0f} DN")
