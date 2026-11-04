"""Channel displacement against green on one raw frame, unbiased by CFA siting.
Each site set (R, G1, G2, B) is interpolated on its own to full resolution with a
bilinear kernel (normalised convolution of the masked mosaic), so samples stay where
they were taken. Null: G1 alone vs G2 alone -- same sparsity as R or B, must read 0.
Reported: displacement of the channel relative to green, sensor px (y down)."""
import sys, numpy as np, rawpy
from scipy.ndimage import sobel, convolve
from skimage.registration import phase_cross_correlation as pcc
with rawpy.imread(sys.argv[1]) as r:
    raw = r.raw_image_visible.astype(np.float32).copy(); pat = r.raw_pattern.copy()
    black = float(np.mean(r.black_level_per_channel))
raw -= black
H, W = raw.shape
k = np.array([[1, 2, 1], [2, 4, 2], [1, 2, 1]], np.float32) / 4
def interp(mask):
    num = convolve(raw * mask, k, mode='mirror'); den = convolve(mask.astype(np.float32), k, mode='mirror')
    return num / den
masks = {}
for i in range(2):
    for j in range(2):
        m = np.zeros((H, W), np.float32); m[i::2, j::2] = 1
        masks[int(pat[i, j])] = m
ch = {n: interp(masks[c]) for n, c in [('R', 0), ('G1', 1), ('B', 2), ('G2', 3)]}
ch['G'] = interp(masks[1] + masks[3])
gm = {n: np.hypot(sobel(v, 0), sobel(v, 1)) for n, v in ch.items()}
T = 256; cy, cx = H / 2, W / 2
thr = np.percentile(gm['G'], 80) * 0.5
def field(ref, mov):
    out = []
    for y in range(0, H - T, T):
        for x in range(0, W - T, T):
            a = gm[ref][y:y+T, x:x+T]
            if a.mean() < thr: continue
            s, _, _ = pcc(a, gm[mov][y:y+T, x:x+T], upsample_factor=20, normalization=None)
            out.append((x + T/2 - cx, y + T/2 - cy, -s[1], -s[0]))
    return np.array(out)
for name, ref, mov in [('null G2 vs G1', 'G1', 'G2'), ('R vs G', 'G', 'R'), ('B vs G', 'G', 'B')]:
    f = field(ref, mov); px, py = f[:, 0], f[:, 1]; rad = np.hypot(px, py) + 1e-9
    radial = (f[:, 2]*px + f[:, 3]*py) / rad; tang = (-f[:, 2]*py + f[:, 3]*px) / rad
    sl = np.polyfit(rad, radial, 1)
    print(f"{name:14s} n {len(f)} mean (x,y) ({f[:,2].mean():+.3f},{f[:,3].mean():+.3f}) sd ({f[:,2].std():.3f},{f[:,3].std():.3f}) | radial = {sl[0]*1e6:+.1f} ppm * r {sl[1]:+.3f}; tangential mean {tang.mean():+.3f}")
def robust(f):
    px, py = f[:, 0], f[:, 1]
    keep = np.hypot(f[:, 2], f[:, 3]) < 3.0
    for _ in range(5):
        A = np.zeros((2*keep.sum(), 3)); A[0::2, 0] = 1; A[1::2, 1] = 1; A[0::2, 2] = px[keep]; A[1::2, 2] = py[keep]
        b = np.empty(2*keep.sum()); b[0::2] = f[keep, 2]; b[1::2] = f[keep, 3]
        sol, *_ = np.linalg.lstsq(A, b, rcond=None)
        rx = f[:, 2] - (sol[0] + sol[2]*px); ry = f[:, 3] - (sol[1] + sol[2]*py); rr = np.hypot(rx, ry)
        mad = np.median(rr[keep]) * 1.4826 + 1e-6
        keep = rr < max(3 * mad, 0.15)
    return sol, rr[keep].std(), keep.sum(), len(f)
print("--- robust fit d = t + s*p")
for name in ['R', 'B', 'G2']:
    ref = 'G1' if name == 'G2' else 'G'
    sol, rms, k, n = robust(field(ref, name))
    print(f"{name}: t = ({sol[0]:+.3f},{sol[1]:+.3f}) px, scale {sol[2]*1e6:+.1f} ppm, rms {rms:.3f}, tiles {k}/{n}")
