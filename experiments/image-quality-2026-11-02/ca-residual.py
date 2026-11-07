"""Per-tile sub-pixel shift of R and B against G (phase correlation on gradient
magnitude), on a linear master. Splits each shift into radial and tangential parts
about the image centre, and reports the mean vector: a uniform vector is a channel
translation, a radial pattern is lateral CA. Control: G against itself shifted by a
known integer roll."""
import sys, numpy as np, tifffile
from scipy.ndimage import sobel
from skimage.registration import phase_cross_correlation as pcc
a = tifffile.imread(sys.argv[1]).astype(np.float32)[..., :3]
H, W, _ = a.shape; cy, cx = H / 2, W / 2
gm = lambda c: np.hypot(sobel(c, 0), sobel(c, 1))
G = gm(a[..., 1]); R = gm(a[..., 0]); B = gm(a[..., 2])
T = 256; rows = []
for y in range(0, H - T, T):
    for x in range(0, W - T, T):
        g = G[y:y+T, x:x+T]
        if g.mean() < np.percentile(G, 80) * 0.5 or g.std() == 0:
            continue
        sr, er, _ = pcc(g, R[y:y+T, x:x+T], upsample_factor=20, normalization=None)
        sb, eb, _ = pcc(g, B[y:y+T, x:x+T], upsample_factor=20, normalization=None)
        rows.append((x + T/2 - cx, y + T/2 - cy, sr[1], sr[0], sb[1], sb[0]))
r = np.array(rows); print("tiles", len(r))
if len(r):
    px, py = r[:, 0], r[:, 1]; rad = np.hypot(px, py) + 1e-9; ux, uy = px / rad, py / rad
    for name, sx, sy in [("R", r[:, 2], r[:, 3]), ("B", r[:, 4], r[:, 5])]:
        radial = sx * ux + sy * uy; tang = -sx * uy + sy * ux
        print(f"{name}: mean shift (x,y) = ({sx.mean():+.3f}, {sy.mean():+.3f}) px  sd ({sx.std():.3f},{sy.std():.3f});"
              f" radial mean {radial.mean():+.3f}  tangential mean {tang.mean():+.3f}; corr(radial, r) {np.corrcoef(radial, rad)[0,1]:+.2f}")
# control: planted integer roll of G
g = G[int(cy)-T:int(cy)+T, int(cx)-T:int(cx)+T]
s, _, _ = pcc(g, np.roll(g, (1, -2), (0, 1)), upsample_factor=20, normalization=None)
print("control (planted roll y+1, x-2):", s)
print("--- fit d = t + s*p on the master (displacement of channel vs G, px)")
for name, sx, sy in [("R", -r[:, 2], -r[:, 3]), ("B", -r[:, 4], -r[:, 5])]:
    A = np.zeros((2*len(r), 3)); A[0::2, 0] = 1; A[1::2, 1] = 1; A[0::2, 2] = r[:, 0]; A[1::2, 2] = r[:, 1]
    b = np.empty(2*len(r)); b[0::2] = sx; b[1::2] = sy
    sol, *_ = np.linalg.lstsq(A, b, rcond=None); res = b - A @ sol
    print(f"{name}: t = ({sol[0]:+.3f},{sol[1]:+.3f}) px, scale {sol[2]*1e6:+.1f} ppm, residual rms {res.std():.3f}")
