import numpy as np, tifffile, sys
b, a, n = sys.argv[1], sys.argv[2], int(sys.argv[3])
B = tifffile.imread(b); A = tifffile.imread(a)
assert B.dtype == np.uint16 and A.dtype == np.uint16
d = np.abs(A.astype(np.int32) - B.astype(np.int32)).mean(axis=2)
H, W = d.shape; bs, h = 100, 160
ys, xs = H//bs, W//bs
blk = d[:ys*bs, :xs*bs].reshape(ys, bs, xs, bs).mean(axis=(1,3))
seen = []
for f in np.argsort(blk.ravel())[::-1]:
    by, bx = divmod(int(f), xs)
    y, x = by*bs + bs//2, bx*bs + bs//2
    if y < h or x < h or y > H-h or x > W-h: continue
    if any(abs(y-p[0]) < 300 and abs(x-p[1]) < 300 for p in seen): continue
    seen.append((y, x))
    if len(seen) == n: break
print(" ".join(f"{y},{x}" for y, x in seen))
