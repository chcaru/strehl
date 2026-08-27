"""Direction check in ABSOLUTE sigma, plus per-merge noise-reduction factor from identical inputs."""
import numpy as np, tifffile
from scipy.ndimage import uniform_filter
rng = np.random.default_rng(77)
CEN = np.load(r"C:\dev\strehl-out\V-NOISE\census.npz", allow_pickle=True)
CELLS, FLAT, T = CEN["cells"], CEN["flat"], int(CEN["T"])
TILES = [tuple(CELLS[i]) for i in FLAT]
R, CH = 3, ("Y", "R-Y", "B-Y")

def raw_pad(p):
    a = tifffile.imread(p)
    if a.ndim == 3 and a.shape[2] >= 4: a = a[:, :, :3]
    o = np.empty((len(TILES), T + 2*R, T + 2*R, 3), a.dtype)
    for i, (y, x) in enumerate(TILES): o[i] = a[y-R:y+T+R, x-R:x+T+R, :3]
    del a; return o

def opp(u):
    f = u.astype(np.float64) / (255.0 if u.dtype == np.uint8 else 65535.0)
    Y = 0.2126*f[...,0] + 0.7152*f[...,1] + 0.0722*f[...,2]
    return np.stack([Y, f[...,0]-Y, f[...,2]-Y], -1)

def q8(u):
    return u if u.dtype == np.uint8 else np.round(u.astype(np.float64)*255.0/65535.0).astype(np.uint8)

def halfdiff(A, B):
    c = slice(R, R+T); m = A[:, c, c, 0].mean(axis=(1,2)); n = A.shape[0]
    best = np.full(n, np.inf); bd = np.zeros((n,2), int)
    for dy in range(-R, R+1):
        for dx in range(-R, R+1):
            d = A[:, c, c, 0] - B[:, R+dy:R+dy+T, R+dx:R+dx+T, 0]
            v = (d**2).mean(axis=(1,2)) - d.mean(axis=(1,2))**2
            w = v < best; best[w] = v[w]; bd[w] = (dy, dx)
    out = np.empty((n,3))
    for i in range(n):
        dy, dx = bd[i]
        d = A[i, c, c, :] - B[i, R+dy:R+dy+T, R+dx:R+dx+T, :]
        v = (d**2).mean(axis=(0,1)) - d.mean(axis=(0,1))**2
        out[i] = np.sqrt(0.5*v)/m[i]
    return out

def hp_sigma(X):
    """Single-image flat-ROI estimator: same estimator applied to inputs AND outputs."""
    c = slice(R, R+T); m = X[:, c, c, 0].mean(axis=(1,2)); n = X.shape[0]
    out = np.empty((n,3))
    for i in range(n):
        for ch in range(3):
            t = X[i, c, c, ch]; out[i, ch] = (t - uniform_filter(t, 9, mode="reflect")).std()
        out[i] /= m[i]
    return out

print("="*96); print("PART 1  ABSOLUTE sigma per arm  (published gauge: container-matched, shift-corrected)")
print("="*96)
sA, sB = raw_pad(r"C:\dev\strehl-out\V-H2H2\lin\113-A-g1.tiff"), raw_pad(r"C:\dev\strehl-out\V-H2H2\lin\113-B-g1.tiff")
P = {"strehl": halfdiff(opp(sA), opp(sB)), "strehl(8bit)": halfdiff(opp(q8(sA)), opp(q8(sB)))}
del sA, sB
for lab, a, b in (("enfuse", "coh-enfuse-A.tif", "coh-enfuse-B.tif"), ("focus-stack", "coh-fs15-A.tif", "coh-fs15-B.tif")):
    A, B = raw_pad(r"C:\dev\strehl-out\V-LINEAR2\out\%s" % a), raw_pad(r"C:\dev\strehl-out\V-LINEAR2\out\%s" % b)
    P[lab] = halfdiff(opp(A), opp(B)); del A, B
print("\n  sigma x1000, normalised by tile mean luma. LOWER = CLEANER.\n")
print("  %-16s %10s %10s %10s" % ("arm", "Y", "R-Y", "B-Y"))
for k in ("strehl", "strehl(8bit)", "enfuse", "focus-stack"):
    print("  %-16s %10.4f %10.4f %10.4f" % tuple([k] + [1000*np.median(P[k][:,i]) for i in range(3)]))
print("\n  Which arm is noisier, per channel:")
for i, c in enumerate(CH):
    v = {k: np.median(P[k][:,i]) for k in ("strehl","enfuse","focus-stack")}
    o = sorted(v, key=v.get)
    print("    %-4s cleanest -> noisiest:  %s" % (c, "  <  ".join("%s(%.4f)" % (k, 1000*v[k]) for k in o)))

print(); print("="*96); print("PART 2  NOISE REDUCTION EACH MERGE ACHIEVED FROM THE SAME INPUTS")
print("="*96)
inp = hp_sigma(opp(raw_pad(r"C:\dev\strehl-out\V-LINEAR2\aligned\al_0000.tif")))
outs = {"strehl": hp_sigma(opp(raw_pad(r"C:\dev\strehl-out\V-H2H2\lin\113-A-g1.tiff"))),
        "enfuse": hp_sigma(opp(raw_pad(r"C:\dev\strehl-out\V-LINEAR2\out\coh-enfuse-A.tif"))),
        "focus-stack": hp_sigma(opp(raw_pad(r"C:\dev\strehl-out\V-LINEAR2\out\coh-fs15-A.tif")))}
print("\n  Same estimator (9px high-pass) on one INPUT frame and on each half-stack MERGE.")
print("  Half stack is ~31 frames, so the shot-noise ideal is sqrt(31.5) = %.2fx\n" % np.sqrt(31.5))
print("  %-14s %26s %26s %26s" % ("arm", "Y reduction", "R-Y reduction", "B-Y reduction"))
n = len(TILES)
for k in ("strehl", "enfuse", "focus-stack"):
    cells = []
    for i in range(3):
        pt = np.median(inp[:,i]) / np.median(outs[k][:,i])
        bs = [np.median(inp[j,i])/np.median(outs[k][j,i]) for j in (rng.integers(0,n,n) for _ in range(2000))]
        lo, hi = np.percentile(bs, [2.5, 97.5])
        cells.append("%5.2fx [%4.2f,%5.2f]" % (pt, lo, hi))
    print("  %-14s %26s %26s %26s" % (k, cells[0], cells[1], cells[2]))
print("\n  input frame sigma x1000: " + "  ".join("%s=%.4f" % (CH[i], 1000*np.median(inp[:,i])) for i in range(3)))
