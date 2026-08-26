"""Measure the geometric relation between the two arms by tile-wise phase
correlation. NOTHING is resampled; this only MEASURES so later steps are honest.
Tiles that are flat or clipped in either arm are dropped (they carry no phase)."""
import numpy as np, tifffile

PRIOR = r"C:\dev\macro\out\coffee-bean\stack.tif"
STREHL = r"C:\dev\strehl-out\SHIP-V2\coffee-bean--SHIP-V2.tiff"

def green(path):
    a = tifffile.memmap(path, mode="r")
    g = np.ascontiguousarray(a[:, :, 1]).astype(np.float32)
    del a
    return g

def prep(t):
    t = np.asarray(t, np.float32)
    m = np.median(t)
    t = np.log1p(np.maximum(t - t.min(), 0) / (abs(m) + 1e-6))
    t = t - t.mean()
    s = t.std()
    if s < 1e-6:
        return None
    win = np.hanning(t.shape[0])[:, None] * np.hanning(t.shape[1])[None, :]
    return (t / s) * win

def pc(a, b):
    A = np.fft.rfft2(a); B = np.fft.rfft2(b)
    R = A * np.conj(B); R /= np.abs(R) + 1e-12
    c = np.fft.irfft2(R, s=a.shape)
    i = int(np.argmax(c)); dy, dx = np.unravel_index(i, c.shape)
    pk = float(c.flat[i]); sd = float(c.std())
    if dy > a.shape[0] // 2: dy -= a.shape[0]
    if dx > a.shape[1] // 2: dx -= a.shape[1]
    return dy, dx, (pk / sd if sd > 0 else 0.0)

P = green(PRIOR); S = green(STREHL).astype(np.float32)
Pclip = None
print("prior G", P.shape, "strehl G", S.shape)

def box(x, f=8):
    h = (x.shape[0] // f) * f; w = (x.shape[1] // f) * f
    return x[:h, :w].reshape(h // f, f, w // f, f).mean(axis=(1, 3))

n = min(P.shape[0] // 8, S.shape[0] // 8); m = min(P.shape[1] // 8, S.shape[1] // 8)
dy, dx, snr = pc(prep(box(S)[:n, :m]), prep(box(P)[:n, :m]))
print(f"gross (8x): dy={dy*8} dx={dx*8} snr={snr:.1f}")

T = 512
ys = np.linspace(300, P.shape[0] - 300 - T, 8).astype(int)
xs = np.linspace(300, P.shape[1] - 300 - T, 11).astype(int)
rows = []
for y in ys:
    for x in xs:
        sy = y + dy * 8; sx = x + dx * 8
        if sy < 0 or sx < 0 or sy + T > S.shape[0] or sx + T > S.shape[1]:
            continue
        tp = P[y:y + T, x:x + T]
        if (tp >= 1.0).mean() > 0.02:      # clipped in prior -> no usable phase
            continue
        a = prep(S[sy:sy + T, sx:sx + T]); b = prep(tp)
        if a is None or b is None:
            continue
        ddy, ddx, sn = pc(a, b)
        rows.append((y + T / 2, x + T / 2, ddy, ddx, sn))
rows = np.array(rows)
good = rows[rows[:, 4] > 10]
print(f"tiles evaluated {len(rows)}  kept(snr>10) {len(good)}  median snr {np.median(rows[:,4]):.1f}")

cy = P.shape[0] / 2; cx = P.shape[1] / 2
Y = good[:, 0] - cy; X = good[:, 1] - cx
DY = good[:, 2].astype(float); DX = good[:, 3].astype(float)
A = np.zeros((2 * len(good), 4)); rhs = np.zeros(2 * len(good))
A[0::2, 0] = X; A[0::2, 1] = -Y; A[0::2, 2] = 1.0
A[1::2, 0] = Y; A[1::2, 1] = X;  A[1::2, 3] = 1.0
rhs[0::2] = DX; rhs[1::2] = DY
sol, *_ = np.linalg.lstsq(A, rhs, rcond=None)
a_, b_, tx, ty = sol
res = A @ sol - rhs
print("\nSIMILARITY FIT  (strehl pixel = s*R(prior pixel - c) + c + t)")
print(f"  scale s   = {1+a_:.6f}   ({a_*100:+.4f} %)")
print(f"  rotation  = {np.degrees(b_):+.5f} deg")
print(f"  transl    = tx {tx+dx*8:+.2f}  ty {ty+dy*8:+.2f} px")
print(f"  residual  rms {np.sqrt((res**2).mean()):.3f} px  max {np.abs(res).max():.2f} px")
sh = np.concatenate([DX - np.median(DX), DY - np.median(DY)])
print(f"  PURE-SHIFT model residual: rms {np.sqrt((sh**2).mean()):.3f} px  max {np.abs(sh).max():.1f} px")
print("\nper-tile (y,x,dy,dx,snr):")
for r in good[np.argsort(-good[:, 4])][:12]:
    print(f"   {r[0]:7.0f} {r[1]:7.0f}  dy {r[2]:+5.0f} dx {r[3]:+5.0f}  snr {r[4]:6.1f}")
np.save("tiles.npy", rows)
