import sys, numpy as np, tifffile
src, dst = sys.argv[1], sys.argv[2]
a = tifffile.imread(src)
assert a.dtype == np.uint16, a.dtype
x = a.astype(np.float64) / 65535.0
lin = np.where(x <= 0.04045, x / 12.92, ((x + 0.055) / 1.055) ** 2.4)
out = np.clip(np.rint(lin * 65535.0), 0, 65535).astype(np.uint16)
tifffile.imwrite(dst, out)
print("decoded", src.split(chr(92))[-1], "->", dst.split(chr(92))[-1], out.shape, out.dtype)
